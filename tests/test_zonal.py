# test zonal stats
import os
import pytest
from rasterstats import raster_stats, RasterStatsError

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
raster = os.path.join(DATA, 'slope.tif')

def test_main():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster)
    for key in ['std', 'count', 'min', 'max', 'sum', 'mean']:
        assert stats[0].has_key(key)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_zonal_global_extent():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, global_src_extent=True)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_global_non_ogr():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = (x.shape for x in reader.shapeRecords())
    with pytest.raises(RasterStatsError):
        raster_stats(geoms, raster, global_src_extent=True)

def test_zonal_nodata():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = raster_stats(polygons, raster, global_src_extent=True, nodata_value=0)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

# TODO test non-existent path
# def test_doesnt exist():
#     multipolygons = os.path.join(DATA, 'DOESNOTEXIST.shp')
#     stats = raster_stats(multipolygons, raster)
#     assert len(stats) == 2
#     assert stats[0]['count'] == 75
#     assert stats[1]['count'] == 50

### Different geometry types

# TODO points can be optimized to avoid the call to rasterizelayer
def test_points():
    points = os.path.join(DATA, 'points.shp')
    stats = raster_stats(points, raster)
    # three features
    assert len(stats) == 3
    # three pixels
    assert sum([x['count'] for x in stats]) == 3

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
    assert 'mean' in stats.keys  # not a list, a dict
    assert stats['count'] == 75

def test_single_geolike():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [x.shape.__geo_interface__ for x in reader.shapeRecords()]
    stats = raster_stats(geoms[0], raster)
    assert 'mean' in stats.keys  # not a list, a dict
    assert stats['count'] == 75

def test_iterable_geolike():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [x.shape.__geo_interface__ for x in reader.shapeRecords()]
    stats = raster_stats(geoms, raster)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

## Categorical
def test_categorical():
    polygons = os.path.join(DATA, 'polygons.shp')
    categorical_raster = os.path.join(DATA, 'slope_classes.tif') 
    stats = raster_stats(polygons, categorical_raster, categorical=True)
    assert len(stats) == 2
    assert stats[0][1.0] == 75
    assert stats[1].has_key(5.0)
