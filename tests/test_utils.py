from pathlib import Path

import pytest
from shapely.geometry import LineString

from rasterstats import zonal_stats
from rasterstats.utils import (
    VALID_STATS,
    boxify_points,
    get_percentile,
    remap_categories,
    stats_to_csv,
)

data_dir = Path(__file__).parent / "data"
raster = data_dir / "slope.tif"


def test_csv():
    polygons = data_dir / "polygons.shp"
    stats = zonal_stats(polygons, raster, stats="*")
    csv = stats_to_csv(stats)
    assert csv.split()[0] == ",".join(sorted(VALID_STATS))


def test_categorical_csv():
    polygons = data_dir / "polygons.shp"
    categorical_raster = data_dir / "slope_classes.tif"
    stats = zonal_stats(polygons, categorical_raster, categorical=True)
    csv = stats_to_csv(stats)
    assert csv.split()[0] == "1.0,2.0,5.0"


def test_get_percentile():
    assert get_percentile("percentile_0") == 0.0
    assert get_percentile("percentile_100") == 100.0
    assert get_percentile("percentile_13.2") == 13.2


def test_get_bad_percentile():
    with pytest.raises(ValueError):
        get_percentile("foo")

    with pytest.raises(ValueError):
        get_percentile("percentile_101")

    with pytest.raises(ValueError):
        get_percentile("percentile_101")

    with pytest.raises(ValueError):
        get_percentile("percentile_-1")

    with pytest.raises(ValueError):
        get_percentile("percentile_foobar")


def test_remap_categories():
    feature_stats = {1: 22.343, 2: 54.34, 3: 987.5}
    category_map = {1: "grassland", 2: "forest"}
    new_stats = remap_categories(category_map, feature_stats)
    assert 1 not in new_stats.keys()
    assert "grassland" in new_stats.keys()
    assert 3 in new_stats.keys()


def test_boxify_non_point():
    line = LineString([(0, 0), (1, 1)])
    with pytest.raises(ValueError):
        boxify_points(line, None)


# TODO # def test_boxify_multi_point
# TODO # def test_boxify_point
