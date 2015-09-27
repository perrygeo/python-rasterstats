import os
import rasterio
from rasterstats.point import point_window_unitxy, bilinear, geom_xys
from rasterstats import point_query

raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
raster_nodata = os.path.join(os.path.dirname(__file__), 'data/slope_nodata.tif')

with rasterio.open(raster) as src:
    affine = src.affine

def test_unitxy_ul():
    win, unitxy = point_window_unitxy(245300, 1000073, affine)
    assert win == ((30, 32), (38, 40))
    x, y = unitxy
    # should be in LR of new unit square
    assert x > 0.5
    assert y < 0.5

def test_unitxy_ur():
    win, unitxy = point_window_unitxy(245318, 1000073, affine)
    assert win == ((30, 32), (39, 41))
    x, y = unitxy
    # should be in LL of new unit square
    assert x < 0.5
    assert y < 0.5

    win, unitxy = point_window_unitxy(245296, 1000073, affine)
    assert win == ((30, 32), (38, 40))
    x, y = unitxy
    # should be in LL of new unit square
    assert x < 0.5
    assert y < 0.5

def test_unitxy_lr():
    win, unitxy = point_window_unitxy(245318, 1000056, affine)
    assert win == ((31, 33), (39, 41))
    x, y = unitxy
    # should be in UL of new unit square
    assert x < 0.5
    assert y > 0.5

def test_unitxy_ll():
    win, unitxy = point_window_unitxy(245300, 1000056, affine)
    assert win == ((31, 33), (38, 40))
    x, y = unitxy
    # should be in UR of new unit square
    assert x > 0.5
    assert y > 0.5

def test_bilinear():
    import numpy as np
    arr = np.array([[1.0, 2.0],
                    [3.0, 4.0]])

    assert bilinear(arr, 0, 0) == 3.0
    assert bilinear(arr, 1, 0) == 4.0
    assert bilinear(arr, 1, 1) == 2.0
    assert bilinear(arr, 0, 1) == 1.0
    assert bilinear(arr, 0.5, 0.5) == arr.mean()
    assert bilinear(arr, 0.95, 0.95) < 4.0
    assert bilinear(arr, 0.05, 0.95) > 1.0


def test_xy_array_bilinear_window():
    """ integration test
    """
    x, y = (245309, 1000064)

    with rasterio.open(raster) as src:
        win, unitxy = point_window_unitxy(x, y, affine)
        arr = src.read(1, window=win)

    val = bilinear(arr, *unitxy)
    assert round(val) == 74


def test_point_query():
    point = "POINT(245309 1000064)"
    val = point_query(point, raster)[0]
    assert round(val) == 74


def test_point_query_geojson():
    point = "POINT(245309 1000064)"
    features = point_query(point, raster, property_name="TEST", geojson_out=True)
    for feature in features:
        assert 'TEST' in feature['properties']
        assert round(feature['properties']['TEST']) == 74


def test_point_query_nodata():
    # all nodata, on the grid
    point = "POINT(245309 1000308)"
    val = point_query(point, raster_nodata)[0]
    assert val is None

    # all nodata, off the grid
    point = "POINT(244000 1000308)"
    val = point_query(point, raster_nodata)[0]
    assert val is None
    point = "POINT(244000 1000308)"
    val = point_query(point, raster_nodata, interpolate="nearest")[0]
    assert val is None

    # some nodata, should fall back to nearest
    point = "POINT(245905 1000361)"
    val = point_query(point, raster_nodata, interpolate="nearest")[0]
    assert round(val) == 43
    val = point_query(point, raster_nodata)[0]
    assert round(val) == 43


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
