from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
import math
import rasterio
from shapely.geometry import shape
from shapely import wkt
from numpy.ma import masked
from numpy import asscalar
from .io import read_features, raster_info


def _point_window_frc(x, y, rgt):
    """ Given an x, y
    Returns
        - rasterio window representing 2x2 window whose center points encompass point
        - the fractional row and col (frc) of the point in the new array

    ((row1, row2), (col1, col2)), (frow, fcol)
    """
    c, a, b, f, d, e = rgt  # gdal-style translated to Affine nomenclature

    frow, fcol = (y-f)/e, (x-c)/a
    r, c = int(round(frow)), int(round(fcol))

    # The new source window for our 2x2 array
    new_win = ((r - 1, r + 1), (c - 1, c + 1))
    # the fractional row, col of the point on the unit square
    frc = (0.5 - (r - frow), 0.5 - (c - fcol))

    return new_win, frc


def _bilinear(arr, frow, fcol):
    """ Given a 2x2 array, treat center points as a unit square
    return the value for the fractional row/col
    using bilinear interpolation between the cells
    """
    # for now, only 2x2 arrays
    assert arr.shape == (2, 2)

    # convert fractional rows, cols to cartesian coords on unit square
    x = fcol
    y = 1 - frow

    ulv, urv, llv, lrv = arr[0:2, 0:2].flatten().tolist()

    if hasattr(arr, 'count') and arr.count() != 4:
        # a masked array with at least one nodata
        # fall back to nearest neighbor
        val = arr[math.floor(x), math.floor(y)]
        if val is masked:
            return None
        else:
            return asscalar(val)

    return ((llv * (1 - x) * (1 - y)) +
            (lrv * x * (1 - y)) +
            (ulv * (1 - x) * y) +
            (urv * x * y))


def geom_xys(geom):
    """Given a shapely geometry,
    generate a flattened series of 2D points as x,y tuples
    """
    if geom.has_z:
        # hack to convert to 2D, https://gist.github.com/ThomasG77/cad711667942826edc70
        geom = wkt.loads(geom.to_wkt())
        assert not geom.has_z

    if hasattr(geom, "geoms"):
        geoms = geom.geoms
    else:
        geoms = [geom]

    for g in geoms:
        arr = g.array_interface_base['data']
        for pair in zip(arr[::2], arr[1::2]):
            yield pair


def point_query(vectors, raster, band_num=1, layer_num=1, interpolate='bilinear',
                nodata_value=None, affine=None, transform=None):
    """Given a set of n vector features and a raster,
    generates n lists of raster values at each vertex of the geometry

    Effectively creates a 2D list, even for a single point, such that

        value = list(point_query(point, raster))[0][0]

    The first index is the geometry, the second is the vertex within the geometry

    # TODO nodata?
    # TODO do we support global_src_extent and ndarrays? not yet...
    """
    features_iter = read_features(vectors, layer_num)

    rtype, rgt, _, _, nodata_value = \
        raster_info(raster, False, nodata_value, affine, transform)

    with rasterio.drivers():
        with rasterio.open(raster, 'r') as src:
            if interpolate == 'bilinear':
                for feat in features_iter:
                    geom = shape(feat['geometry'])
                    vals = []
                    for x, y in geom_xys(geom):
                        window, frc = _point_window_frc(x, y, rgt)
                        src_array = src.read(band_num, window=window, masked=True)
                        vals.append(_bilinear(src_array, *frc))
                    yield vals
            elif interpolate == 'nearest':
                for feat in features_iter:
                    geom = shape(feat['geometry'])
                    vals = []
                    for x, y in geom_xys(geom):
                        r, c = src.index(x, y)
                        window = ((r, r+1), (c, c+1))
                        src_array = src.read(band_num, window=window, masked=True)
                        val = src_array[0, 0]
                        if val is masked:
                            vals.append(None)
                        else:
                            vals.append(asscalar(val))
                    yield vals
            else:
                raise ValueError("interpolate must be nearest or bilinear")
