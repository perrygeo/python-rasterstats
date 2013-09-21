# test zonal stats
import os
import pytest
from osgeo import ogr
from rasterstats import raster_stats, RasterStatsError
from rasterstats.main import VALID_STATS
from rasterstats.utils import shapely_to_ogr_type, parse_geo, get_ogr_ds, \
                              OGRError, feature_to_geojson
from shapely.geometry import shape, box
import json

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
raster = os.path.join(DATA, 'slope.tif')

def test_main():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster)
    for key in ['__fid__', 'count', 'min', 'max', 'mean']:
        assert stats[0].has_key(key)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_zonal_global_extent():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster)
    global_stats = raster_stats(polygons, raster, global_src_extent=True)
    assert stats == global_stats

def test_global_non_ogr():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = (x.shape for x in reader.shapeRecords())
    with pytest.raises(RasterStatsError):
        raster_stats(geoms, raster, global_src_extent=True)

def test_zonal_nodata():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, nodata_value=0)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_doesnt_exist():
    nonexistent = os.path.join(DATA, 'DOESNOTEXIST.shp')
    with pytest.raises(RasterStatsError):
        raster_stats(nonexistent, raster)

def test_nonsense():
    polygons = os.path.join(DATA, 'polygons.shp')
    with pytest.raises(RasterStatsError):
        raster_stats("blaghrlargh", raster)
    with pytest.raises(RasterStatsError):
        raster_stats(polygons, "blercherlerch")
    with pytest.raises(RasterStatsError):
        raster_stats(["blaghrlargh",], raster)

### Different geometry types

def test_points():
    points = os.path.join(DATA, 'points.shp')
    stats = raster_stats(points, raster)
    # three features
    assert len(stats) == 3
    # three pixels
    assert sum([x['count'] for x in stats]) == 3
    assert round(stats[0]['mean'], 3) == 11.386
    assert round(stats[1]['mean'], 3) == 35.547

def test_points_categorical():
    points = os.path.join(DATA, 'points.shp')
    categorical_raster = os.path.join(DATA, 'slope_classes.tif') 
    stats = raster_stats(points, categorical_raster, categorical=True)
    # three features
    assert len(stats) == 3
    assert not stats[0].has_key('mean')
    assert stats[0][1.0] == 1
    assert stats[1][2.0] == 1

def test_lines():
    lines = os.path.join(DATA, 'lines.shp')
    stats = raster_stats(lines, raster)
    assert len(stats) == 2
    assert stats[0]['count'] == 58
    assert stats[1]['count'] == 32

# Test multigeoms
def test_multipolygons():
    multipolygons = os.path.join(DATA, 'multipolygons.shp')
    stats = raster_stats(multipolygons, raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 125

def test_multilines():
    multilines = os.path.join(DATA, 'multilines.shp')
    stats = raster_stats(multilines, raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 90

def test_multipoints():
    multipoints = os.path.join(DATA, 'multipoints.shp')
    stats = raster_stats(multipoints, raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 3

## Geo interface
import shapefile

def test_iterable_geoms_geo():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = (x.shape for x in reader.shapeRecords())
    stats = raster_stats(geoms, raster)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_iterable_features_geo():  
    # Grr pyshp doesnt do feature-level geo_interface so we need to construct it 
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    features = []
    class FeatureThing(object):
        pass
    fields = reader.fields[1:]  
    field_names = [field[0] for field in fields]  
    for sr in reader.shapeRecords():
        geom = sr.shape.__geo_interface__  
        atr = dict(zip(field_names, sr.record))  
        obj = FeatureThing()
        obj.__geo_interface__ = dict(geometry=geom,properties=atr,type="Feature")
        features.append(obj)
    stats = raster_stats(features, raster)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_single_geo():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [x.shape for x in reader.shapeRecords()]
    stats = raster_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

def test_single_geolike():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [x.shape.__geo_interface__ for x in reader.shapeRecords()]
    stats = raster_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

def test_iterable_geolike():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [x.shape.__geo_interface__ for x in reader.shapeRecords()]
    stats = raster_stats(geoms, raster)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_single_wkt():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [shape(x.shape).wkt for x in reader.shapeRecords()]
    stats = raster_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

def test_single_wkb():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [shape(x.shape).wkb for x in reader.shapeRecords()]
    stats = raster_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

def test_single_jsonstr():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [json.dumps(x.shape.__geo_interface__) for x in reader.shapeRecords()]
    stats = raster_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

## Categorical
def test_categorical():
    polygons = os.path.join(DATA, 'polygons.shp')
    categorical_raster = os.path.join(DATA, 'slope_classes.tif') 
    stats = raster_stats(polygons, categorical_raster, categorical=True)
    assert len(stats) == 2
    assert stats[0][1.0] == 75
    assert stats[1].has_key(5.0)


## Utils

def test_nopoints():
    with pytest.raises(TypeError):
        shapely_to_ogr_type('Point')
    with pytest.raises(TypeError):
        shapely_to_ogr_type('MultiPoint')

        raster_stats(geoms, raster, global_src_extent=True)

def test_jsonstr():
    jsonstr = '{"type": "Polygon", "coordinates": [[[244697.45179524383, 1000369.2307574936], [244827.15493968062, 1000373.0455558595], [244933.9692939227, 1000353.9715640305], [244933.9692939227, 1000353.9715640305], [244930.15449555693, 1000147.9724522779], [244697.45179524383, 1000159.4168473752], [244697.45179524383, 1000369.2307574936]]]}'
    assert parse_geo(jsonstr)

def test_ogr_ds_nonstring():
    a = box(0,1,2,3)
    with pytest.raises(OGRError):
        get_ogr_ds(a)

def test_ogr_geojson():
    polygons = os.path.join(DATA, 'polygons.shp')
    ds = ogr.Open(polygons)
    lyr = ds.GetLayer(0)
    feat = lyr.GetNextFeature()
    res = feature_to_geojson(feat)
    assert res['type'] == 'Feature'

def test_ogr_geojson_nogeom():
    polygons = os.path.join(DATA, 'polygons.shp')
    ds = ogr.Open(polygons)
    lyr = ds.GetLayer(0)
    feat = lyr.GetNextFeature()
    feat.SetGeometryDirectly(None)
    res = feature_to_geojson(feat)
    assert res['type'] == 'Feature'
    assert res['geometry'] == None

def test_specify_stats_list():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, stats=['min', 'max'])
    assert sorted(stats[0].keys()) == sorted(['__fid__', 'min', 'max'])
    assert 'count' not in stats[0].keys()

def test_specify_all_stats():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, stats='ALL')
    assert sorted(stats[0].keys()) == sorted(VALID_STATS + ["__fid__"])
    stats = raster_stats(polygons, raster, stats='*')
    assert sorted(stats[0].keys()) == sorted(VALID_STATS + ["__fid__"])

def test_specify_stats_string():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, stats='min max')
    assert sorted(stats[0].keys()) == sorted(['__fid__', 'min', 'max'])
    assert 'count' not in stats[0].keys()

def test_specify_stats_invalid():
    polygons = os.path.join(DATA, 'polygons.shp')
    with pytest.raises(RasterStatsError):
        raster_stats(polygons, raster, stats='foo max')

def test_optional_stats():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, stats='min max sum majority median std')
    assert stats[0]['min'] <= stats[0]['median'] <= stats[0]['max']

def test_no_copy_properties():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, copy_properties=False)  # default
    assert not stats[0].has_key('id')  # attr from original shp

def test_copy_properties():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, copy_properties=True)
    assert stats[0].has_key('id')  # attr from original shp
