import json
import math
import warnings
from collections.abc import Iterable, Mapping
from json import JSONDecodeError

import fiona
import numpy as np
import rasterio
from affine import Affine
from fiona.errors import DriverError
from rasterio.enums import MaskFlags
from rasterio.transform import guard_transform
from shapely import wkb, wkt

try:
    from shapely.errors import ShapelyError
except ImportError:  # pragma: no cover
    from shapely.errors import ReadingError as ShapelyError


geom_types = [
    "Point",
    "LineString",
    "Polygon",
    "MultiPoint",
    "MultiLineString",
    "MultiPolygon",
]

try:
    # Fiona 1.9+
    import fiona.model

    def fiona_generator(obj, layer=0):
        with fiona.open(obj, "r", layer=layer) as src:
            for feat in src:
                yield fiona.model.to_dict(feat)

except ModuleNotFoundError:
    # Fiona <1.9
    def fiona_generator(obj, layer=0):
        with fiona.open(obj, "r", layer=layer) as src:
            yield from src


def wrap_geom(geom):
    """Wraps a geometry dict in an GeoJSON Feature"""
    return {"type": "Feature", "properties": {}, "geometry": geom}


def parse_feature(obj):
    """Given a python object
    attemp to a GeoJSON-like Feature from it
    """

    # object implementing geo_interface
    if hasattr(obj, "__geo_interface__"):
        gi = obj.__geo_interface__
        if gi["type"] in geom_types:
            return wrap_geom(gi)
        elif gi["type"] == "Feature":
            return gi

    # wkt
    try:
        shape = wkt.loads(obj)
        return wrap_geom(shape.__geo_interface__)
    except (ShapelyError, TypeError, AttributeError):
        pass

    # wkb
    try:
        shape = wkb.loads(obj)
        return wrap_geom(shape.__geo_interface__)
    except (ShapelyError, TypeError):
        pass

    # geojson-like python mapping
    try:
        if obj["type"] in geom_types:
            return wrap_geom(obj)
        elif obj["type"] == "Feature":
            return obj
    except (AssertionError, TypeError):
        pass

    raise ValueError("Can't parse %s as a geojson Feature object" % obj)


def read_features(obj, layer=0):
    features_iter = None
    if isinstance(obj, str):
        try:
            # test it as fiona data source
            with fiona.open(obj, "r", layer=layer) as src:
                assert len(src) > 0

            features_iter = fiona_generator(obj, layer)
        except (
            AssertionError,
            DriverError,
            OSError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
        ):
            try:
                mapping = json.loads(obj)
                if "type" in mapping and mapping["type"] == "FeatureCollection":
                    features_iter = mapping["features"]
                elif mapping["type"] in geom_types + ["Feature"]:
                    features_iter = [parse_feature(mapping)]
            except (ValueError, JSONDecodeError):
                # Single feature-like string
                features_iter = [parse_feature(obj)]
    elif isinstance(obj, Mapping):
        if "type" in obj and obj["type"] == "FeatureCollection":
            features_iter = obj["features"]
        else:
            features_iter = [parse_feature(obj)]
    elif isinstance(obj, bytes):
        # Single binary object, probably a wkb
        features_iter = [parse_feature(obj)]
    elif hasattr(obj, "__geo_interface__"):
        mapping = obj.__geo_interface__
        if mapping["type"] == "FeatureCollection":
            features_iter = mapping["features"]
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
    fc = {"type": "FeatureCollection", "features": []}
    fc["features"] = [f for f in features]
    return fc


def rowcol(x, y, affine, op=math.floor):
    """Get row/col for a x/y"""
    r = int(op((y - affine.f) / affine.e))
    c = int(op((x - affine.c) / affine.a))
    return r, c


def bounds_window(bounds, affine):
    """Create a full cover rasterio-style window"""
    w, s, e, n = bounds
    row_start, col_start = rowcol(w, n, affine)
    row_stop, col_stop = rowcol(e, s, affine, op=math.ceil)
    return (row_start, row_stop), (col_start, col_stop)


def window_bounds(window, affine):
    (row_start, row_stop), (col_start, col_stop) = window
    w, s = affine * (col_start, row_stop)
    e, n = affine * (col_stop, row_start)
    return w, s, e, n


def beyond_extent(window, shape):
    """Checks if window references pixels beyond the raster extent"""
    (wr_start, wr_stop), (wc_start, wc_stop) = window
    return wr_start < 0 or wc_start < 0 or wr_stop > shape[0] or wc_stop > shape[1]


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
    out = np.empty(shape=window_shape, dtype=arr.dtype)
    out[:] = nodata

    # Fill with data where overlapping
    nr_start = olr_start - wr_start
    nr_stop = nr_start + overlap_shape[0]
    nc_start = olc_start - wc_start
    nc_stop = nc_start + overlap_shape[1]
    if dim3:
        out[:, nr_start:nr_stop, nc_start:nc_stop] = arr[
            :, olr_start:olr_stop, olc_start:olc_stop
        ]
    else:
        out[nr_start:nr_stop, nc_start:nc_stop] = arr[
            olr_start:olr_stop, olc_start:olc_stop
        ]

    if masked:
        out = np.ma.MaskedArray(out, mask=(out == nodata))

    return out


class NodataWarning(UserWarning):
    pass


# *should* limit NodataWarnings to once, but doesn't! Bug in CPython.
# warnings.filterwarnings("once", category=NodataWarning)
# instead we resort to a global bool
already_warned_nodata = False


class Raster:
    """Raster abstraction for data access to 2/3D array-like things

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
            self.src = rasterio.open(raster, "r")
            self.affine = guard_transform(self.src.transform)
            self.shape = (self.src.height, self.src.width)
            self.band = band

            if nodata is not None:
                # override with specified nodata
                self.nodata = float(nodata)
            else:
                self.nodata = self.src.nodata

    def index(self, x, y):
        """Given (x, y) in crs, return the (row, column) on the raster"""
        col, row = (math.floor(a) for a in (~self.affine * (x, y)))
        return row, col

    def read(self, bounds=None, window=None, masked=False, boundless=True):
        """Performs a read against the underlying array source

        Parameters
        ----------
        bounds: bounding box
            in w, s, e, n order, iterable, optional
        window: rasterio-style window, optional
            bounds OR window are required,
            specifying both or neither will raise exception
        masked: boolean
            return a masked numpy array, default: False
        boundless: boolean
            allow window/bounds that extend beyond the dataset’s extent, default: True
            partially or completely filled arrays will be returned as appropriate.

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

        if not boundless and beyond_extent(win, self.shape):
            raise ValueError(
                "Window/bounds is outside dataset extent, boundless reads are disabled"
            )

        c, _, _, f = window_bounds(win, self.affine)  # c ~ west, f ~ north
        a, b, _, d, e, _, _, _, _ = tuple(self.affine)
        new_affine = Affine(a, b, c, d, e, f)

        nodata = self.nodata
        if nodata is None:
            nodata = -999
            global already_warned_nodata
            if not already_warned_nodata:
                warnings.warn(
                    "Setting nodata to -999; specify nodata explicitly", NodataWarning
                )
                already_warned_nodata = True

        if self.array is not None:
            # It's an ndarray already
            new_array = boundless_array(
                self.array, window=win, nodata=nodata, masked=masked
            )
        elif self.src:
            # It's an open rasterio dataset
            if all(
                MaskFlags.per_dataset in flags for flags in self.src.mask_flag_enums
            ):
                if not masked:
                    masked = True
                    warnings.warn(
                        "Setting masked to True because dataset mask has been detected"
                    )

            new_array = self.src.read(
                self.band, window=win, boundless=boundless, masked=masked
            )

        return Raster(new_array, new_affine, nodata)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.src is not None:
            # close the rasterio reader
            self.src.close()
