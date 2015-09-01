import os
import rasterio
from rasterstats.point import _point_window_frc, point_query, _bilinear, geom_xys

raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')

with rasterio.open(raster) as src:
    rgt = src.affine.to_gdal()

def test_frc_ul():
    win, frc = _point_window_frc(245300, 1000073, rgt)
    assert win == ((30, 32), (38, 40))
    frow, fcol = frc
    assert frow > 0.5
    assert fcol > 0.5

def test_frc_ur():
    win, frc = _point_window_frc(245318, 1000073, rgt)
    assert win == ((30, 32), (39, 41))
    frow, fcol = frc
    assert frow > 0.5
    assert fcol < 0.5

    win, frc = _point_window_frc(245296, 1000073, rgt)
    assert win == ((30, 32), (38, 40))
    frow, fcol = frc
    assert frow > 0.5
    assert fcol < 0.5

def test_frc_lr():
    win, frc = _point_window_frc(245318, 1000056, rgt)
    assert win == ((31, 33), (39, 41))
    frow, fcol = frc
    assert frow < 0.5
    assert fcol < 0.5

def test_frc_ll():
    win, frc = _point_window_frc(245300, 1000056, rgt)
    assert win == ((31, 33), (38, 40))
    frow, fcol = frc
    assert frow < 0.5
    assert fcol > 0.5

def test_bilinear():
    import numpy as np
    arr = np.array([[1.0, 2.0],
                    [3.0, 4.0]])

    assert _bilinear(arr, 0, 0) == arr[0, 0]
    assert _bilinear(arr, 1, 0) == arr[1, 0]
    assert _bilinear(arr, 1, 1) == arr[1, 1]
    assert _bilinear(arr, 0, 1) == arr[0, 1]
    assert _bilinear(arr, 0.5, 0.5) == arr.mean()
    assert _bilinear(arr, 0.95, 0.95) < arr[1, 1]
    assert _bilinear(arr, 0.05, 0.05) > arr[0, 0]

def test_xy_array_bilinear_window():
    """ integration test
    """
    x, y = (245309, 1000064)

    with rasterio.open(raster) as src:
        rgt = src.affine.to_gdal()
        win, frc = _point_window_frc(x, y, rgt)
        arr = src.read(1, window=win)

    val = _bilinear(arr, *frc)
    assert round(val) == 74

def test_point_query():
    point = "POINT(245309 1000064)"
    val = list(point_query(point, raster))[0][0]
    assert round(val) == 74

def test_geom_xys():
    from shapely.geometry import (Point, MultiPoint,
                                  LineString, MultiLineString,
                                  Polygon, MultiPolygon)
    pt = Point(0, 0)
    assert list(geom_xys(pt)) == [(0, 0)]
    mpt = MultiPoint([(0, 0), (1, 1)])
    assert list(geom_xys(mpt)) == [(0, 0), (1, 1)]
    line = LineString([(0, 0), (1, 1)])
    assert list(geom_xys(line)) == [(0, 0), (1, 1)]
    mline = MultiLineString([((0, 0), (1, 1)), ((-1, 0), (1, 0))])
    assert list(geom_xys(mline)) == [(0, 0), (1, 1), (-1, 0), (1, 0)]
    poly = Polygon([(0, 0), (1, 1), (1, 0)])
    assert list(geom_xys(poly)) == [(0, 0), (1, 1), (1, 0), (0, 0)]
    ring = poly.exterior
    assert list(geom_xys(ring)) == [(0, 0), (1, 1), (1, 0), (0, 0)]
    mpoly = MultiPolygon([poly, Polygon([(2, 2), (3, 3), (3, 2)])])
    assert list(geom_xys(mpoly)) == [(0, 0), (1, 1), (1, 0), (0, 0),
                                     (2, 2), (3, 3), (3, 2), (2, 2)]
    mpt3d = MultiPoint([(0, 0, 1), (1, 1, 2)])
    assert list(geom_xys(mpt3d)) == [(0, 0), (1, 1)]
