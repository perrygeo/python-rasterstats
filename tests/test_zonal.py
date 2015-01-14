# test zonal stats
import os
import pytest
from osgeo import ogr
from rasterstats import zonal_stats, stats_to_csv, RasterStatsError, raster_stats
from rasterstats.main import VALID_STATS
from rasterstats.utils import shapely_to_ogr_type, parse_geo, get_ogr_ds, \
                              OGRError, feature_to_geojson, bbox_to_pixel_offsets
from shapely.geometry import shape, box
import json
import sys
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
raster = os.path.join(DATA, 'slope.tif')

def test_main():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster)
    for key in ['__fid__', 'count', 'min', 'max', 'mean']:
        assert key in stats[0]
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_zonal_global_extent():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster)
    global_stats = zonal_stats(polygons, raster, global_src_extent=True)
    assert stats == global_stats

def test_global_non_ogr():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = (x.shape for x in reader.shapeRecords())
    with pytest.raises(RasterStatsError):
        zonal_stats(geoms, raster, global_src_extent=True)

def test_zonal_nodata():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, nodata_value=0)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_doesnt_exist():
    nonexistent = os.path.join(DATA, 'DOESNOTEXIST.shp')
    with pytest.raises(RasterStatsError):
        zonal_stats(nonexistent, raster)

def test_nonsense():
    polygons = os.path.join(DATA, 'polygons.shp')
    with pytest.raises(RasterStatsError):
        zonal_stats("blaghrlargh", raster)
    with pytest.raises(RasterStatsError):
        zonal_stats(polygons, "blercherlerch")
    with pytest.raises(RasterStatsError):
        zonal_stats(["blaghrlargh",], raster)

### Different geometry types

def test_points():
    points = os.path.join(DATA, 'points.shp')
    stats = zonal_stats(points, raster)
    # three features
    assert len(stats) == 3
    # three pixels
    assert sum([x['count'] for x in stats]) == 3
    assert round(stats[0]['mean'], 3) == 11.386
    assert round(stats[1]['mean'], 3) == 35.547

def test_points_categorical():
    points = os.path.join(DATA, 'points.shp')
    categorical_raster = os.path.join(DATA, 'slope_classes.tif') 
    stats = zonal_stats(points, categorical_raster, categorical=True)
    # three features
    assert len(stats) == 3
    assert 'mean' not in stats[0]
    assert stats[0][1.0] == 1
    assert stats[1][2.0] == 1

def test_lines():
    lines = os.path.join(DATA, 'lines.shp')
    stats = zonal_stats(lines, raster)
    assert len(stats) == 2
    assert stats[0]['count'] == 58
    assert stats[1]['count'] == 32

# Test multigeoms
def test_multipolygons():
    multipolygons = os.path.join(DATA, 'multipolygons.shp')
    stats = zonal_stats(multipolygons, raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 125

def test_multilines():
    multilines = os.path.join(DATA, 'multilines.shp')
    stats = zonal_stats(multilines, raster)
    assert len(stats) == 1
    # can differ slightly based on platform/gdal version
    assert stats[0]['count'] in [89, 90]

def test_multipoints():
    multipoints = os.path.join(DATA, 'multipoints.shp')
    stats = zonal_stats(multipoints, raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 3

## Geo interface
import shapefile

def test_iterable_geoms_geo():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = (x.shape for x in reader.shapeRecords())
    stats = zonal_stats(geoms, raster)
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
        atr = dict(list(zip(field_names, sr.record)))  
        obj = FeatureThing()
        obj.__geo_interface__ = dict(geometry=geom,properties=atr,type="Feature")
        features.append(obj)
    stats = zonal_stats(features, raster)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_single_geo():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [x.shape for x in reader.shapeRecords()]
    stats = zonal_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

def test_single_geolike():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [x.shape.__geo_interface__ for x in reader.shapeRecords()]
    stats = zonal_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

def test_iterable_geolike():  
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [x.shape.__geo_interface__ for x in reader.shapeRecords()]
    stats = zonal_stats(geoms, raster)
    assert len(stats) == 2
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

def test_single_wkt():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [shape(x.shape).wkt for x in reader.shapeRecords()]
    stats = zonal_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

def test_single_wkb():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [shape(x.shape).wkb for x in reader.shapeRecords()]
    stats = zonal_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

def test_single_jsonstr():
    reader = shapefile.Reader(os.path.join(DATA, 'polygons.shp'))  
    geoms = [json.dumps(x.shape.__geo_interface__) for x in reader.shapeRecords()]
    stats = zonal_stats(geoms[0], raster)
    assert len(stats) == 1
    assert stats[0]['count'] == 75

## Categorical
def test_categorical():
    polygons = os.path.join(DATA, 'polygons.shp')
    categorical_raster = os.path.join(DATA, 'slope_classes.tif') 
    stats = zonal_stats(polygons, categorical_raster, categorical=True)
    assert len(stats) == 2
    assert stats[0][1.0] == 75
    assert 5.0 in stats[1]


## Utils

def test_nopoints():
    with pytest.raises(TypeError):
        shapely_to_ogr_type('Point')
    with pytest.raises(TypeError):
        shapely_to_ogr_type('MultiPoint')

        zonal_stats(geoms, raster, global_src_extent=True)

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
    stats = zonal_stats(polygons, raster, stats=['min', 'max'])
    assert sorted(stats[0].keys()) == sorted(['__fid__', 'min', 'max'])
    assert 'count' not in list(stats[0].keys())

def test_specify_all_stats():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, stats='ALL')
    assert sorted(stats[0].keys()) == sorted(VALID_STATS + ["__fid__"])
    stats = zonal_stats(polygons, raster, stats='*')
    assert sorted(stats[0].keys()) == sorted(VALID_STATS + ["__fid__"])

def test_specify_stats_string():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, stats='min max')
    assert sorted(stats[0].keys()) == sorted(['__fid__', 'min', 'max'])
    assert 'count' not in list(stats[0].keys())

def test_specify_stats_invalid():
    polygons = os.path.join(DATA, 'polygons.shp')
    with pytest.raises(RasterStatsError):
        zonal_stats(polygons, raster, stats='foo max')

def test_optional_stats():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, stats='min max sum majority median std')
    assert stats[0]['min'] <= stats[0]['median'] <= stats[0]['max']

def test_no_copy_properties():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, copy_properties=False)  # default
    assert 'id' not in stats[0]  # attr from original shp

def test_copy_properties():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, copy_properties=True)
    assert 'id' in stats[0]  # attr from original shp

def test_range():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, stats="range min max")
    for stat in stats:
        assert stat['range'] == stat['max'] - stat['min']
    ranges = [x['range'] for x in stats]
    # without min/max specified
    stats = zonal_stats(polygons, raster, stats="range")
    assert 'min' not in stats[0]
    assert ranges == [x['range'] for x in stats]

def test_csv():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, stats="*")
    csv = stats_to_csv(stats)
    assert csv.split()[0] == ','.join(sorted(VALID_STATS + ['__fid__']))

def test_categorical_csv():
    polygons = os.path.join(DATA, 'polygons.shp')
    categorical_raster = os.path.join(DATA, 'slope_classes.tif') 
    stats = zonal_stats(polygons, categorical_raster, categorical=True)
    csv = stats_to_csv(stats)
    assert csv.split()[0] == "1.0,2.0,5.0,__fid__"

def test_nodata_value():
    polygons = os.path.join(DATA, 'polygons.shp')
    categorical_raster = os.path.join(DATA, 'slope_classes.tif') 
    stats = zonal_stats(polygons, categorical_raster, stats="*",
        categorical=True, nodata_value=1.0)
    assert stats[0]['majority'] == None
    assert stats[0]['count'] == 0  # no pixels; they're all null
    assert stats[1]['minority'] == 2.0
    assert stats[1]['count'] == 49 # used to be 50 if we allowed 1.0
    assert '1.0' not in stats[0]

def test_partial_overlap():
    polygons = os.path.join(DATA, 'polygons_partial_overlap.shp')
    stats = zonal_stats(polygons, raster, stats="count")
    for res in stats:
        # each polygon should have at least a few pixels overlap
        assert res['count'] > 0

def test_no_overlap():
    polygons = os.path.join(DATA, 'polygons_no_overlap.shp')
    stats = zonal_stats(polygons, raster, stats="count")
    for res in stats:
        # no polygon should have any overlap
        assert res['count'] is None

def test_bbox_offbyone():
    # Make sure we don't get the off-by-one error in calculating src offset
    rgt = (-4418000.0, 250.0, 0.0, 4876500.0, 0.0, -250.0)
    geom_bounds = [4077943.9961, -3873500.0, 4462000.0055, -3505823.7582]
    rsize = (37000, 35000)
    so = bbox_to_pixel_offsets(rgt, geom_bounds, rsize)
    assert so[1] + so[3] == rsize[1]

    # Another great example
    # based on https://github.com/perrygeo/python-raster-stats/issues/46
    rgt = (151.2006, 0.025, 0.0, -25.4896, 0.0, -0.025)
    geom_bounds = [153.39775866026284, -28.903022885889843, 153.51344076545288, -28.80117672778147]
    rsize = (92, 135)
    # should only be 5 pixels wide, not 6 due to rounding errors
    assert bbox_to_pixel_offsets(rgt, geom_bounds, rsize) == (87, 132, 5, 3)


def test_all_touched():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, all_touched=True)
    assert stats[0]['count'] == 95  # 75 if ALL_TOUCHED=False
    assert stats[1]['count'] == 73  # 50 if ALL_TOUCHED=False

def _get_raster_array_gt(raster):
    from osgeo import gdal
    rds = gdal.Open(raster, gdal.GA_ReadOnly)
    gt = rds.GetGeoTransform()
    band = rds.GetRasterBand(1)
    arr = band.ReadAsArray()
    return arr, gt

def test_ndarray_without_transform():
    arr, gt = _get_raster_array_gt(raster)
    polygons = os.path.join(DATA, 'polygons.shp')
    with pytest.raises(RasterStatsError):
        zonal_stats(polygons, arr)

def test_ndarray_nodata():
    arr, gt = _get_raster_array_gt(raster)
    polygons = os.path.join(DATA, 'polygons.shp')
    with pytest.raises(NotImplementedError):
        zonal_stats(polygons, arr, transform=gt, nodata_value=-999)

def test_ndarray():
    arr, gt = _get_raster_array_gt(raster)
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, arr, transform=gt)
    assert stats == zonal_stats(polygons, raster)
    assert stats[0]['count'] == 75
    assert stats[1]['count'] == 50

    points = os.path.join(DATA, 'points.shp')
    stats = zonal_stats(points, arr, transform=gt)
    assert stats == zonal_stats(points, raster)
    assert sum([x['count'] for x in stats]) == 3
    assert round(stats[0]['mean'], 3) == 11.386
    assert round(stats[1]['mean'], 3) == 35.547


def test_alias():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster)
    stats2 = raster_stats(polygons, raster)
    assert stats == stats2
    pytest.deprecated_call(raster_stats, polygons, raster)


def test_featurecollection():
    from geopandas import GeoDataFrame
    polygons = os.path.join(DATA, 'polygons.shp')
    df = GeoDataFrame.from_file(polygons)
    assert df.__geo_interface__['type'] == 'FeatureCollection'

    stats = zonal_stats(polygons, raster)

    # geointerface featurecollection
    stats2 = zonal_stats(df, raster)
    assert stats == stats2

def mymean(x):
    return np.ma.mean(x)

def test_add_stats():
    from geopandas import GeoDataFrame
    polygons = os.path.join(DATA, 'polygons.shp')
    df = GeoDataFrame.from_file(polygons)
    mymean= lambda x: np.ma.mean(x)
    stats = zonal_stats(df.geometry, raster, add_stats={'mymean':mymean})
    for i in range(len(stats)):
        assert stats[i]['mean'] == stats[i]['mymean']

def test_mini_raster():
    from geopandas import GeoDataFrame
    polygons = os.path.join(DATA, 'polygons.shp')
    df = GeoDataFrame.from_file(polygons)
    stats = zonal_stats(df.geometry, raster, raster_out=True, opt_georaster=False)
    stats2=zonal_stats(df.geometry, stats[0]['mini_raster'], raster_out=True, transform=stats[0]['mini_raster_GT'], opt_georaster=False)
    assert (stats[0]['mini_raster'] == stats2[0]['mini_raster']).sum()==stats[0]['count']

def test_mini_raster2():
    from geopandas import GeoDataFrame
    polygons = os.path.join(DATA, 'polygons.shp')
    df = GeoDataFrame.from_file(polygons)
    stats = zonal_stats(df.geometry, raster, raster_out=True, opt_georaster=True)
    stats2=zonal_stats(df.geometry, stats[0]['mini_raster'].raster.data, raster_out=True, transform=stats[0]['mini_raster'].geot, opt_georaster=True)
    assert (stats[0]['mini_raster'].raster == stats2[0]['mini_raster'].raster).sum()==stats[0]['count']
