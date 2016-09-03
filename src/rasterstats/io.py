# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import sys
import json
import math
import fiona
import rasterio
import warnings
from rasterio.transform import guard_transform
from affine import Affine
import numpy as np
from shapely.geos import ReadingError
from shapely import wkt, wkb
from collections import Iterable, Mapping


geom_types = ["Point", "LineString", "Polygon",
              "MultiPoint", "MultiLineString", "MultiPolygon"]

PY3 = sys.version_info[0] >= 3
if PY3:
    string_types = str,  # pragma: no cover
else:
    string_types = basestring,  # pragma: no cover

def wrap_geom(geom):
    """ Wraps a geometry dict in an GeoJSON Feature
    """
    return {'type': 'Feature',
            'properties': {},
            'geometry': geom}


def parse_feature(obj):
    """ Given a python object
    attemp to a GeoJSON-like Feature from it
    """

    # object implementing geo_interface
    if hasattr(obj, '__geo_interface__'):
        gi = obj.__geo_interface__
        if gi['type'] in geom_types:
            return wrap_geom(gi)
        elif gi['type'] == 'Feature':
            return gi

    # wkt
    try:
        shape = wkt.loads(obj)
        return wrap_geom(shape.__geo_interface__)
    except (ReadingError, TypeError, AttributeError):
        pass

    # wkb
    try:
        shape = wkb.loads(obj)
        return wrap_geom(shape.__geo_interface__)
    except (ReadingError, TypeError):
        pass

    # geojson-like python mapping
    try:
        if obj['type'] in geom_types:
            return wrap_geom(obj)
        elif obj['type'] == 'Feature':
            return obj
    except (AssertionError, TypeError):
        pass

    raise ValueError("Can't parse %s as a geojson Feature object" % obj)


def read_features(obj, layer=0):
    features_iter = None
    if isinstance(obj, string_types):
        try:
            # test it as fiona data source
            with fiona.open(obj, 'r', layer=layer) as src:
                assert len(src) > 0

            def fiona_generator(obj):
                with fiona.open(obj, 'r', layer=layer) as src:
                    for feature in src:
                        yield feature

            features_iter = fiona_generator(obj)
        except (AssertionError, TypeError, IOError, OSError):
            try:
                mapping = json.loads(obj)
                if 'type' in mapping and mapping['type'] == 'FeatureCollection':
                    features_iter = mapping['features']
                elif mapping['type'] in geom_types + ['Feature']:
                    features_iter = [parse_feature(mapping)]
            except ValueError:
                # Single feature-like string
                features_iter = [parse_feature(obj)]
    elif isinstance(obj, Mapping):
        if 'type' in obj and obj['type'] == 'FeatureCollection':
            features_iter = obj['features']
        else:
            features_iter = [parse_feature(obj)]
    elif isinstance(obj, bytes):
        # Single binary object, probably a wkb
        features_iter = [parse_feature(obj)]
    elif hasattr(obj, '__geo_interface__'):
        mapping = obj.__geo_interface__
        if mapping['type'] == 'FeatureCollection':
            features_iter = mapping['features']
        else:
            features_iter = [parse_feature(mapping)]
    elif isinstance(obj, Iterable):
        # Iterable of feature-like objects
        features_iter = (parse_feature(x) for x in obj)

    if not features_iter:
        raise ValueError("Object is not a recognized source of Features")
    return features_iter


def read_featurecollection(obj, layer=0):
    features = read_features(obj, layer=layer)
    fc = {'type': 'FeatureCollection', 'features': []}
    fc['features'] = [f for f in features]
    return fc


def rowcol(x, y, affine, op=math.floor):
    """ Get row/col for a x/y
    """
    r = int(op((y - affine.f) / affine.e))
    c = int(op((x - affine.c) / affine.a))
    return r, c


def bounds_window(bounds, affine):
    """Create a full cover rasterio-style window
    """
    w, s, e, n = bounds
    row_start, col_start = rowcol(w, n, affine)
    row_stop, col_stop = rowcol(e, s, affine, op=math.ceil)
    return (row_start, row_stop), (col_start, col_stop)


def window_bounds(window, affine):
    (row_start, row_stop), (col_start, col_stop) = window
    w, s = (col_start, row_stop) * affine
    e, n = (col_stop, row_start) * affine
    return w, s, e, n


def boundless_array(arr, window, nodata, masked=False):
    dim3 = False
    if len(arr.shape) == 3:
        dim3 = True
    elif len(arr.shape) != 2:
        raise ValueError("Must be a 2D or 3D array")

    # unpack for readability
    (wr_start, wr_stop), (wc_start, wc_stop) = window

    # Calculate overlap
    olr_start = max(min(window[0][0], arr.shape[-2:][0]), 0)
    olr_stop = max(min(window[0][1], arr.shape[-2:][0]), 0)
    olc_start = max(min(window[1][0], arr.shape[-2:][1]), 0)
    olc_stop = max(min(window[1][1], arr.shape[-2:][1]), 0)

    # Calc dimensions
    overlap_shape = (olr_stop - olr_start, olc_stop - olc_start)
    if dim3:
        window_shape = (arr.shape[0], wr_stop - wr_start, wc_stop - wc_start)
    else:
        window_shape = (wr_stop - wr_start, wc_stop - wc_start)

    # create an array of nodata values
    out = np.ones(shape=window_shape) * nodata

    # Fill with data where overlapping
    nr_start = olr_start - wr_start
    nr_stop = nr_start + overlap_shape[0]
    nc_start = olc_start - wc_start
    nc_stop = nc_start + overlap_shape[1]
    if dim3:
        out[:, nr_start:nr_stop, nc_start:nc_stop] = \
            arr[:, olr_start:olr_stop, olc_start:olc_stop]
    else:
        out[nr_start:nr_stop, nc_start:nc_stop] = \
            arr[olr_start:olr_stop, olc_start:olc_stop]

    if masked:
        out = np.ma.MaskedArray(out, mask=(out == nodata))

    return out


class Raster(object):
    """ Raster abstraction for data access to 2/3D array-like things

    Use as a context manager to ensure dataset gets closed properly::

        >>> with Raster(path) as rast:
        ...

    Parameters
    ----------
    raster: 2/3D array-like data source, required
        Currently supports paths to rasterio-supported rasters and
        numpy arrays with Affine transforms.

    affine: Affine object
        Maps row/col to coordinate reference system
        required if raster is ndarray

    nodata: nodata value, optional
        Overrides the datasource's internal nodata if specified

    band: integer
        raster band number, optional (default: 1)

    Methods
    -------
    index
    read
    """

    def __init__(self, raster, affine=None, nodata=None, band=1):
        self.array = None
        self.src = None

        if isinstance(raster, np.ndarray):
            if affine is None:
                raise ValueError("Specify affine transform for numpy arrays")
            self.array = raster
            self.affine = affine
            self.shape = raster.shape
            self.nodata = nodata
        else:
            self.src = rasterio.open(raster, 'r')
            self.affine = guard_transform(self.src.transform)
            self.shape = (self.src.height, self.src.width)
            self.band = band

            if nodata is not None:
                # override with specified nodata
                self.nodata = float(nodata)
            else:
                self.nodata = self.src.nodata

    def index(self, x, y):
        """ Given (x, y) in crs, return the (row, column) on the raster
        """
        col, row = [math.floor(a) for a in (~self.affine * (x, y))]
        return row, col

    def read(self, bounds=None, window=None, masked=False):
        """ Performs a boundless read against the underlying array source

        Parameters
        ----------
        bounds: bounding box
            in w, s, e, n order, iterable, optional
        window: rasterio-style window, optional
            bounds OR window are required,
            specifying both or neither will raise exception
        masked: boolean
            return a masked numpy array, default: False
            bounds OR window are required, specifying both or neither will raise exception

        Returns
        -------
        Raster object with update affine and array info
        """
        # Calculate the window
        if bounds and window:
            raise ValueError("Specify either bounds or window")

        if bounds:
            win = bounds_window(bounds, self.affine)
        elif window:
            win = window
        else:
            raise ValueError("Specify either bounds or window")

        c, _, _, f = window_bounds(win, self.affine)  # c ~ west, f ~ north
        a, b, _, d, e, _, _, _, _ = tuple(self.affine)
        new_affine = Affine(a, b, c, d, e, f)

        nodata = self.nodata
        if nodata is None:
            nodata = -999
            warnings.warn("Setting nodata to -999; specify nodata explicitly")

        if self.array is not None:
            # It's an ndarray already
            new_array = boundless_array(
                self.array, window=win, nodata=nodata, masked=masked)
        elif self.src:
            # It's an open rasterio dataset
            new_array = self.src.read(
                self.band, window=win, boundless=True, masked=masked)

        return Raster(new_array, new_affine, nodata)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.src is not None:
            # close the rasterio reader
            self.src.close()
