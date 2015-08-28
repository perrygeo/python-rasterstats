import math
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

    new_win = ((r - 1, r + 1), (c - 1, c + 1))
    frc = ( 0.5 - (r - frow), 0.5 - (c - fcol))  # the fractional row, col of the point
    return new_win, frc


def _bilinear(arr, frow, fcol):
    """ Given an array, return the value for the fractional row/col
    using bilinear interpolation between the cells"
    """
    # for now, only 2x2 arrays
    assert arr.shape == (2, 2)

    # convert rows, cols to cartesian coords on unit square
    x = fcol
    y = 1 - frow
    # use variables for clarity, todo optimize by replacement
    x1 = 0
    x2 = 1
    y1 = 0
    y2 = 1

    ulv, urv, llv, lrv = arr[0:2, 0:2].flatten().tolist()

    fxy = ((llv * (x2 - x) * (y2 - y)) +
           (lrv * (x - x1) * (y2 - y)) +
           (ulv * (x2 - x) * (y - y1)) +
           (urv * (x - x1) * (y - y1)))

    return fxy


def point_query(vectors, raster, band_num=1, layer_num=1, interpolate='bilinear',
                nodata_value=None, affine=None, transform=None):
    features_iter = read_features(vectors, layer_num)

    rtype, rgt, rshape, global_src_extent, nodata_value = \
        raster_info(raster, False, nodata_value, affine, transform)

    for feat in features_iter:
        geom = shape(feat['geometry'])

        # TODO check if point, otherwise ???
        window, frc = _point_window_frc(geom.x, geom.y, rgt)

        with rasterio.drivers():
            with rasterio.open(raster, 'r') as src:
                src_array = src.read(band_num, window=window, masked=False)

        val = _bilinear(src_array, *frc)
        yield val

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
