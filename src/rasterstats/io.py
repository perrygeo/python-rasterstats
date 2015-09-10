# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import sys
import json
import math
import fiona
import rasterio
from affine import Affine
import numpy as np
from shapely.geos import ReadingError
from shapely import wkt, wkb
from collections import Iterable, Mapping


geom_types = ["Point", "LineString", "Polygon",
              "MultiPoint", "MultiLineString", "MultiPolygon"]

PY3 = sys.version_info[0] >= 3
if PY3:
    string_types = str,
else:
    string_types = basestring,

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


def geo_records(vectors):
    for vector in vectors:
        yield parse_feature(vector)


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
    elif isinstance(obj, Iterable):
        # Iterable of feature-like objects
        features_iter = (parse_feature(x) for x in obj)
    elif hasattr(obj, '__geo_interface__'):
        mapping = obj.__geo_interface__
        if mapping['type'] == 'FeatureCollection':
            features_iter = mapping['features']
        else:
            features_iter = [parse_feature(mapping)]
    else:
        # Single feature-like object
        features_iter = [parse_feature(obj)]

    if not features_iter:
        raise ValueError("Object is not a recognized source of Features")
    return features_iter


def read_featurecollection(obj, layer=0, lazy=False):
    features = read_features(obj, layer=layer)
    fc = {'type': 'FeatureCollection', 'features': []}
    if lazy:
        fc['features'] = (f for f in features)
    else:
        fc['features'] = [f for f in features]
    return fc


def raster_info(raster, global_src_extent, nodata_value, affine, transform):
    """ Accepts a rasterio-supported raster source or ndarray
    Handles intricacies of affine vs transform, nodata, raster vs array
    """
    if isinstance(raster, np.ndarray):
        rtype = 'ndarray'

        # must have transform info
        if affine:
            transform = affine
        if not transform:
            raise ValueError("Must provide the 'transform' kwarg "
                             "when using ndarrays as src raster")
        try:
            rgt = transform.to_gdal()  # an Affine object
        except AttributeError:
            rgt = transform  # a GDAL geotransform

        rshape = (raster.shape[1], raster.shape[0])

        # global_src_extent is implicitly turned on, array is already in memory
        global_src_extent = True

    else:
        rtype = 'gdal'

        with rasterio.drivers():
            with rasterio.open(raster, 'r') as src:
                affine = src.affine
                rgt = affine.to_gdal()
                rshape = (src.width, src.height)
                rnodata = src.nodata

        if nodata_value is not None:
            # override with specified nodata
            nodata_value = float(nodata_value)
        else:
            nodata_value = rnodata

    return rtype, rgt, rshape, global_src_extent, nodata_value


def rc(x, y, affine, op=math.floor):
    """ Get row/col for a x/y
    """
    r = int(op((y - affine.f) / affine.e))
    c = int(op((x - affine.c) / affine.a))
    return r, c


def get_window(bounds, affine):
    """Create a full cover rasterio-style window
    """
    w, s, e, n = bounds
    row_start, col_start = rc(w, n, affine)
    row_stop, col_stop = rc(e, s, affine, op=math.ceil)
    return (row_start, row_stop), (col_start, col_stop)


def get_bounds(window, affine):
    (row_start, row_stop), (col_start, col_stop) = window
    w, s = (col_start, row_stop) * affine
    e, n = (col_stop, row_start) * affine
    return w, s, e, n


class Raster(object):

    @property
    def transform(*args, **kwargs):
        raise Exception("Don't you mean 'affine'?")

    def read(self, bounds):

        # Calculate the window
        win = get_window(bounds, self.affine)
        (row_start, row_stop), (col_start, col_stop) = win

        c, _, _, f = get_bounds(win, self.affine)  # c ~ west, f ~ north
        a, b, _, d, e, _, _, _, _ = tuple(self.affine)
        new_affine = Affine(a, b, c, d, e, f)

        nodata = self.nodata

        if self.array:
            # It's an ndarray already
            new_array = self.array[row_start:row_stop, col_start:col_stop]
        elif self.src:
            # It's an open rasterio dataset
            new_array = self.src.read(self.band, window=win, boundless=True)
        else:
            raise Exception("Raster has neither a src nor an array, should never happen")

        return Raster(new_array, new_affine, nodata)

    def __init__(self, raster, affine=None, nodata=None, band=1):
        self.drivers = None
        self.array = None
        self.src = None

        if isinstance(raster, np.ndarray):
            if affine is None:
                raise Exception("Must specify affine for numpy arrays")
            # TODO try Affine.from_gdal(affine) and raise warning "Looks like you're using
            self.array = raster
            self.affine = affine
            self.shape = raster.shape
            self.nodata = nodata
        else:
            self.drivers = rasterio.drivers()
            self.src = rasterio.open(raster, 'r')
            self.affine = self.src.affine
            self.shape = (self.src.height, self.src.width)
            self.band = band

            if nodata is not None:
                # override with specified nodata
                self.nodata = float(nodata)
            else:
                self.nodata = self.src.nodata

    def __enter__(self):
        return self

    def __exit__(self, *args):
        #TODO close drivers and src
        pass
