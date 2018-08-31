import sys
import os
import pytest
import numpy as np
from affine import Affine
from shapely.geometry import LineString, Polygon
from rasterstats.utils import \
    stats_to_csv, get_percentile, remap_categories, boxify_points, \
    rebin_sum, rasterize_pctcover_geom
from rasterstats import zonal_stats
from rasterstats.utils import VALID_STATS


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
raster = os.path.join(DATA, 'slope.tif')


def test_csv():
    polygons = os.path.join(DATA, 'polygons.shp')
    stats = zonal_stats(polygons, raster, stats="*")
    csv = stats_to_csv(stats)
    assert csv.split()[0] == ','.join(sorted(VALID_STATS))


def test_categorical_csv():
    polygons = os.path.join(DATA, 'polygons.shp')
    categorical_raster = os.path.join(DATA, 'slope_classes.tif')
    stats = zonal_stats(polygons, categorical_raster, categorical=True)
    csv = stats_to_csv(stats)
    assert csv.split()[0] == "1.0,2.0,5.0"


def test_get_percentile():
    assert get_percentile('percentile_0') == 0.0
    assert get_percentile('percentile_100') == 100.0
    assert get_percentile('percentile_13.2') == 13.2

def test_get_bad_percentile():
    with pytest.raises(ValueError):
        get_percentile('foo')

    with pytest.raises(ValueError):
        get_percentile('percentile_101')

    with pytest.raises(ValueError):
        get_percentile('percentile_101')

    with pytest.raises(ValueError):
        get_percentile('percentile_-1')

    with pytest.raises(ValueError):
        get_percentile('percentile_foobar')


def test_remap_categories():
    feature_stats = {1: 22.343, 2: 54.34, 3: 987.5}
    category_map = {1: 'grassland', 2: 'forest'}
    new_stats = remap_categories(category_map, feature_stats)
    assert 1 not in new_stats.keys()
    assert 'grassland' in new_stats.keys()
    assert 3 in new_stats.keys()


def test_boxify_non_point():
    line = LineString([(0, 0), (1, 1)])
    with pytest.raises(ValueError):
        boxify_points(line, None)


def test_rebin_sum():
    test_input = np.array(
        [
            [1, 1, 2, 2],
            [1, 1, 2, 2],
            [3, 3, 4, 4],
            [3, 3, 4, 4]
        ])
    test_output = rebin_sum(test_input, (2,2), np.int32)
    correct_output = np.array([[4, 8],[12, 16]])
    assert np.array_equal(test_output, correct_output)


def test_rasterize_pctcover_geom():
    # https://goodcode.io/articles/python-dict-object/
    class objectview(object):
        def __init__(self, d):
            self.__dict__ = d

    polygon_a = Polygon([[0, 0], [2, 0], [2, 2], [0, 2]])
    shape_a = (2, 2)
    affine_a = Affine(1, 0, 0,
                      0, -1, 2)
    like_a = objectview({'shape': shape_a, 'affine': affine_a})

    pct_cover_a = rasterize_pctcover_geom(polygon_a, like_a, scale=10, all_touched=False)
    correct_output_a = np.array([[1, 1], [1, 1]])
    assert np.array_equal(pct_cover_a, correct_output_a)

    polygon_b = Polygon([[0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5]])
    shape_b = (2, 2)
    affine_b = Affine(1, 0, 0,
                      0, -1, 2)
    like_b = objectview({'shape': shape_b, 'affine': affine_b})

    pct_cover_b = rasterize_pctcover_geom(polygon_b, like_b, scale=10, all_touched=False)
    correct_output_b = np.array([[0.25, 0.25], [0.25, 0.25]])
    assert np.array_equal(pct_cover_b, correct_output_b)

    polygon_c = Polygon([[0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5]])
    shape_c = (2, 2)
    affine_c = Affine(1, 0, 0,
                      0, -1, 2)
    like_c = objectview({'shape': shape_c, 'affine': affine_c})

    pct_cover_c = rasterize_pctcover_geom(polygon_c, like_c, scale=100, all_touched=False)
    correct_output_c = np.array([[0.25, 0.25], [0.25, 0.25]])
    assert np.array_equal(pct_cover_c, correct_output_c)
