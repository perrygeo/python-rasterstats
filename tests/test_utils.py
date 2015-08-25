import sys
import os
import pytest
from rasterstats.utils import stats_to_csv, bbox_to_pixel_offsets, get_percentile
from rasterstats import zonal_stats
from rasterstats.main import VALID_STATS


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
raster = os.path.join(DATA, 'slope.tif')


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


def test_bbox_offbyone():
    # Make sure we don't get the off-by-one error in calculating src offset
    rgt = (-4418000.0, 250.0, 0.0, 4876500.0, 0.0, -250.0)
    geom_bounds = [4077943.9961, -3873500.0, 4462000.0055, -3505823.7582]
    rshape = (37000, 35000)
    so = bbox_to_pixel_offsets(rgt, geom_bounds, rshape)
    assert so[1] + so[3] == rshape[1]

    # Another great example
    # based on https://github.com/perrygeo/python-raster-stats/issues/46
    rgt = (151.2006, 0.025, 0.0, -25.4896, 0.0, -0.025)
    geom_bounds = [153.39775866026284, -28.903022885889843,
                   153.51344076545288, -28.80117672778147]
    rshape = (92, 135)
    # should only be 5 pixels wide, not 6 due to rounding errors
    assert bbox_to_pixel_offsets(rgt, geom_bounds, rshape) == (87, 132, 5, 3)


def test_get_percentile():
    assert get_percentile('percentile_0') == 0.0
    assert get_percentile('percentile_100') == 100.0
    assert get_percentile('percentile_13.2') == 13.2

    with pytest.raises(ValueError):
        get_percentile('percentile_101')

    with pytest.raises(ValueError):
        get_percentile('percentile_-1')

    with pytest.raises(ValueError):
        get_percentile('percentile_foobar')
