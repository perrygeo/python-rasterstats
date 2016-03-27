import sys
import os
import fiona
import rasterio
import json
import pytest
from shapely.geometry import shape
from rasterstats.io import read_features, read_featurecollection, Raster  # todo parse_feature
from rasterstats.io import boundless_array, window_bounds, bounds_window, rowcol


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
polygons = os.path.join(DATA, 'polygons.shp')
raster = os.path.join(DATA, 'slope.tif')

import numpy as np
arr = np.array([[1, 1, 1],
                [1, 1, 1],
                [1, 1, 1]])

arr3d = np.array([[[1, 1, 1],
                   [1, 1, 1],
                   [1, 1, 1]]])

with fiona.open(polygons, 'r') as src:
    target_features = [f for f in src]

target_geoms = [shape(f['geometry']) for f in target_features]


def _compare_geomlists(aa, bb):
    for a, b in zip(aa, bb):
        assert a.almost_equals(b)


def _test_read_features(indata):
    features = list(read_features(indata))
    # multi
    geoms = [shape(f['geometry']) for f in features]
    _compare_geomlists(geoms, target_geoms)


def _test_read_features_single(indata):
    # single (first target geom)
    geom = shape(list(read_features(indata))[0]['geometry'])
    assert geom.almost_equals(target_geoms[0])


def test_fiona_path():
    assert list(read_features(polygons)) == target_features


def test_layer_index():
    layer = fiona.listlayers(DATA).index('polygons')
    assert list(read_features(DATA, layer=layer)) == target_features


def test_layer_name():
    assert list(read_features(DATA, layer='polygons')) == target_features


def test_path_unicode():
    try:
        upolygons = unicode(polygons)
    except NameError:
        # python3, it's already unicode
        upolygons = polygons
    assert list(read_features(upolygons)) == target_features


def test_featurecollection():
    assert read_featurecollection(polygons)['features'] == \
        list(read_features(polygons)) == \
        target_features


def test_shapely():
    with fiona.open(polygons, 'r') as src:
        indata = [shape(f['geometry']) for f in src]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_wkt():
    with fiona.open(polygons, 'r') as src:
        indata = [shape(f['geometry']).wkt for f in src]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_wkb():
    with fiona.open(polygons, 'r') as src:
        indata = [shape(f['geometry']).wkb for f in src]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_mapping_features():
    # list of Features
    with fiona.open(polygons, 'r') as src:
        indata = [f for f in src]
    _test_read_features(indata)


def test_mapping_feature():
    # list of Features
    with fiona.open(polygons, 'r') as src:
        indata = [f for f in src]
    _test_read_features(indata[0])


def test_mapping_geoms():
    with fiona.open(polygons, 'r') as src:
        indata = [f for f in src]
    _test_read_features(indata[0]['geometry'])


def test_mapping_collection():
    indata = {'type': "FeatureCollection"}
    with fiona.open(polygons, 'r') as src:
        indata['features'] = [f for f in src]
    _test_read_features(indata)


def test_jsonstr():
    # Feature str
    with fiona.open(polygons, 'r') as src:
        indata = [f for f in src]
    indata = json.dumps(indata[0])
    _test_read_features(indata)


def test_jsonstr_geom():
    # geojson geom str
    with fiona.open(polygons, 'r') as src:
        indata = [f for f in src]
    indata = json.dumps(indata[0]['geometry'])
    _test_read_features(indata)


def test_jsonstr_collection():
    indata = {'type': "FeatureCollection"}
    with fiona.open(polygons, 'r') as src:
        indata['features'] = [f for f in src]
    indata = json.dumps(indata)
    _test_read_features(indata)


class MockGeoInterface:
    def __init__(self, f):
        self.__geo_interface__ = f


def test_geo_interface():
    with fiona.open(polygons, 'r') as src:
        indata = [MockGeoInterface(f) for f in src]
    _test_read_features(indata)


def test_geo_interface_geom():
    with fiona.open(polygons, 'r') as src:
        indata = [MockGeoInterface(f['geometry']) for f in src]
    _test_read_features(indata)


def test_geo_interface_collection():
    # geointerface for featurecollection?
    indata = {'type': "FeatureCollection"}
    with fiona.open(polygons, 'r') as src:
        indata['features'] = [f for f in src]
    indata = MockGeoInterface(indata)
    _test_read_features(indata)


def test_notafeature():
    with pytest.raises(ValueError):
        list(read_features(['foo', 'POINT(-122 42)']))

    with pytest.raises(ValueError):
        list(read_features(Exception()))


# Raster tests
def test_boundless():
    # Exact
    assert boundless_array(arr, window=((0, 3), (0, 3)), nodata=0).sum() == 9

    # Intersects
    assert boundless_array(arr, window=((-1, 2), (-1, 2)), nodata=0).sum() == 4
    assert boundless_array(arr, window=((1, 4), (-1, 2)), nodata=0).sum() == 4
    assert boundless_array(arr, window=((1, 4), (1, 4)), nodata=0).sum() == 4
    assert boundless_array(arr, window=((-1, 2), (1, 4)), nodata=0).sum() == 4

    # No overlap
    assert boundless_array(arr, window=((-4, -1), (-4, -1)), nodata=0).sum() == 0
    assert boundless_array(arr, window=((-4, -1), (4, 7)), nodata=0).sum() == 0
    assert boundless_array(arr, window=((4, 7), (4, 7)), nodata=0).sum() == 0
    assert boundless_array(arr, window=((4, 7), (-4, -1)), nodata=0).sum() == 0
    assert boundless_array(arr, window=((-3, 0), (-3, 0)), nodata=0).sum() == 0

    # Covers
    assert boundless_array(arr, window=((-1, 4), (-1, 4)), nodata=0).sum() == 9

    # 3D
    assert boundless_array(arr3d, window=((0, 3), (0, 3)), nodata=0).sum() == 9
    assert boundless_array(arr3d, window=((-1, 2), (-1, 2)), nodata=0).sum() == 4
    assert boundless_array(arr3d, window=((-3, 0), (-3, 0)), nodata=0).sum() == 0

    # 1D
    with pytest.raises(ValueError):
        boundless_array(np.array([1, 1, 1]), window=((0, 3),), nodata=0)


def test_boundless_masked():
    a = boundless_array(arr, window=((-4, -1), (-4, -1)), nodata=0, masked=True)
    assert a.mask.all()
    b = boundless_array(arr, window=((0, 3), (0, 3)), nodata=0, masked=True)
    assert not b.mask.any()
    c = boundless_array(arr, window=((-1, 2), (-1, 2)), nodata=0, masked=True)
    assert c.mask.any() and not c.mask.all()


def test_window_bounds():
    with rasterio.open(raster) as src:
        win = ((0, src.shape[0]), (0, src.shape[1]))
        assert src.bounds == window_bounds(win, src.affine)

        win = ((5, 10), (5, 10))
        assert src.window_bounds(win) == window_bounds(win, src.affine)


def test_bounds_window():
    with rasterio.open(raster) as src:
        assert bounds_window(src.bounds, src.affine) == \
            ((0, src.shape[0]), (0, src.shape[1]))


def test_rowcol():
    import math
    with rasterio.open(raster) as src:
        x, _, _, y = src.bounds
        x += 1.0
        y -= 1.0
        assert rowcol(x, y, src.affine, op=math.floor) == (0, 0)
        assert rowcol(x, y, src.affine, op=math.ceil) == (1, 1)

def test_Raster_index():
    x, y = 245114, 1000968
    with rasterio.open(raster) as src:
        c1, r1 = src.index(x, y)
    with Raster(raster) as rast:
        c2, r2 = rast.index(x, y)
    assert c1 == c2
    assert r1 == r2


def test_Raster():
    import numpy as np

    bounds = (244156, 1000258, 245114, 1000968)
    r1 = Raster(raster, band=1).read(bounds)

    with rasterio.open(raster) as src:
        arr = src.read(1)
        affine = src.affine
        nodata = src.nodata

    r2 = Raster(arr, affine, nodata, band=1).read(bounds)

    # If the abstraction is correct, the arrays are equal
    assert np.array_equal(r1.array, r2.array)

def test_Raster_context():
    # Assigned a regular name, stays open
    r1 = Raster(raster, band=1)
    assert not r1.src.closed
    r1.src.close()

    # Used as a context manager, closes itself
    with Raster(raster, band=1) as r2:
        pass
    assert r2.src.closed


def test_Raster_nan():
    with rasterio.open(raster) as src:
        win = ((0, src.height), (0, src.width))
        arr = src.read(1, window=win)
        affine = src.affine
        nodata = src.nodata

    assert (arr == nodata).sum() == 320

    # throw in a few nans and run it through Raster
    arr[20:25, 20:25] = float('nan')  # 25 nans
    r2 = Raster(arr, affine, nodata, band=1).read(window=win, nan_as_nodata=True)

    assert (r2.array == nodata).sum() == 345  # 25 more nodatas
    assert np.isnan(r2.array).sum() == 0  # nans were converted to nodata


def test_geointerface():
    class MockGeo(object):
        def __init__(self, features):
            self.__geo_interface__ = {
                'type': "FeatureCollection",
                'features': features}

        # Make it iterable just to ensure that geo interface
        # takes precendence over iterability
        def __iter__(self):
            pass

        def __next__(self):
            pass

        def next(self):
            pass

    features = [{
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Point",
            "coordinates": [0, 0]}
    }, {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-50, -10], [-40, 10], [-30, -10], [-50, -10]]]}}]

    geothing = MockGeo(features)
    assert list(read_features(geothing)) == features


# Optional tests
def test_geodataframe():
    try:
        import geopandas as gpd
        df = gpd.read_file(polygons)
        if not hasattr(df, '__geo_interface__'):
            pytest.skip("This version of geopandas doesn't support df.__geo_interface__")
    except ImportError:
        pytest.skip("Can't import geopands")
    assert list(read_features(df))
