from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
import rasterio
from shapely.geometry import shape
from .io import read_features, raster_info


def _point_window_frc(x, y, rgt):
    """ Given an x, y
    Returns
        - rasterio window representing 2x2 window around a given point with point in UL
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

    return ((llv * (1 - x) * (1 - y)) +
            (lrv * x * (1 - y)) +
            (ulv * (1 - x) * y) +
            (urv * x * y))


def point_query(vectors, raster, band_num=1, layer_num=1, interpolate='bilinear',
                nodata_value=None, affine=None, transform=None):
    features_iter = read_features(vectors, layer_num)

    rtype, rgt, _, global_src_extent, nodata_value = \
        raster_info(raster, False, nodata_value, affine, transform)

    with rasterio.drivers():
        with rasterio.open(raster, 'r') as src:
            for feat in features_iter:
                geom = shape(feat['geometry'])

                # TODO check if point, otherwise loop through verticies
                x, y = geom.x, geom.y

                if interpolate == 'bilinear':
                    window, frc = _point_window_frc(x, y, rgt)
                    src_array = src.read(band_num, window=window, masked=False)
                    val = _bilinear(src_array, *frc)
                    yield val
                elif interpolate == 'nearest':
                    r, c = src.index(x, y)
                    window = ((r, r+1), (c, c+1))
                    src_array = src.read(band_num, window=window, masked=False)
                    val = src_array[0, 0]
                    yield val
                else:
                    raise Exception("nearest or bilinear")

    # TODO nodata?
    # TODO do we support global_src_extent? not yet...
    # if not global_src_extent:
    #     # use feature's source extent and read directly from source
    #     window = pixel_offsets_to_window(src_offset)
    #     with rasterio.drivers():
    #         with rasterio.open(raster, 'r') as src:
    #             src_array = src.read(
    #                 band_num, window=window, masked=False)
    # else:
    #     # subset feature array from global source extent array
    #     xa = src_offset[0] - global_src_offset[0]
    #     ya = src_offset[1] - global_src_offset[1]
    #     xb = xa + src_offset[2]
    #     yb = ya + src_offset[3]
    #     src_array = global_src_array[ya:yb, xa:xb]
