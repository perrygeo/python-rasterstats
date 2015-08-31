import sys
import os
import fiona
from shapely.geometry import shape
from rasterstats.io import read_features, read_featurecollection  # todo parse_feature
import json
import pytest


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
polygons = os.path.join(DATA, 'polygons.shp')

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
    assert list(read_features(DATA, layer=6)) == target_features


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


# Optional tests
def test_geodataframe():
    try:
        import geopandas as gpd
        df = gpd.GeoDataFrame.from_file(polygons)
        if not hasattr(df, '__geo_interface__'):
            pytest.skip("This version of geopandas doesn't support df.__geo_interface__")
    except ImportError:
        pytest.skip("Can't import geopands")
    assert read_features(df)
