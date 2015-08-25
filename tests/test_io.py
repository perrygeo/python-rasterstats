import sys
import os
from rasterstats.io import get_featurecollection, parse_geo
# TODO separate concerns, test zonal stats elsewhere
from rasterstats import zonal_stats


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
raster = os.path.join(DATA, 'slope.tif')

def test_featurecollection():
    polygons = os.path.join(DATA, 'polygons.shp')

    fc = get_featurecollection(polygons)
    assert fc['type'] == 'FeatureCollection'

    stats = zonal_stats(polygons, raster)
    stats2 = zonal_stats(fc, raster)

    assert stats == stats2


def test_jsonstr():
    jsonstr = '''
    {"type": "Polygon", "coordinates": [[
    [244697.45179524383, 1000369.2307574936],
    [244827.15493968062, 1000373.0455558595],
    [244933.9692939227, 1000353.9715640305],
    [244933.9692939227, 1000353.9715640305],
    [244930.15449555693, 1000147.9724522779],
    [244697.45179524383, 1000159.4168473752],
    [244697.45179524383, 1000369.2307574936]
    ]]}'''
    assert parse_geo(jsonstr)
