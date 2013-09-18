# test zonal stats
import os
from rasterstats import raster_stats
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def test_zonal():
    polygons = os.path.join(DATA, 'polygons.shp')
    raster = os.path.join(DATA, 'slope.tif')
    stats = raster_stats(polygons, raster)
    assert sorted(stats[0].keys()) == sorted(
        ['std', 'count', 'min', 'max', 'sum', 'fid', 'mean'])
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_zonal_global_extent():
    polygons = os.path.join(DATA, 'polygons.shp')
    raster = os.path.join(DATA, 'slope.tif')
    stats = raster_stats(polygons, raster, global_src_extent=True)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_zonal_nodata():
    polygons = os.path.join(DATA, 'polygons.shp')
    raster = os.path.join(DATA, 'slope.tif')
    stats = raster_stats(polygons, raster, global_src_extent=True, nodata_value=0)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50
