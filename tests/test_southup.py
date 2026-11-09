"""Positive-y rectilinear rasters retain native row order, including reads."""

import numpy as np
import pytest
import rasterio
from affine import Affine
from shapely.geometry import Point, box

from rasterstats import point_query, zonal_stats
from rasterstats.io import Raster, bounds_window, window_bounds

DATA = np.array([[0, 10, 20, 30], [100, 110, 120, 130], [200, 210, 220, 230]])
TRANSFORM = Affine(2, 0, 5, 0, 3, 10)
NODATA = -999


@pytest.fixture(params=["array", "geotiff"])
def southup_source(request, tmp_path):
    if request.param == "array":
        return DATA, {"affine": TRANSFORM, "nodata": NODATA}
    path = tmp_path / "southup.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=3,
        width=4,
        count=1,
        dtype=DATA.dtype,
        transform=TRANSFORM,
        nodata=NODATA,
    ) as dst:
        dst.write(DATA, 1)
    return path, {}


@pytest.mark.parametrize("ystep", [3, -3])
def test_rectilinear_bounds_round_trip(ystep):
    transform = Affine(2, 0, 5, 0, ystep, 10 if ystep > 0 else 19)
    # Fractional world bounds require full-cover floor/ceil, not truncation.
    bounds = (6, 11, 10, 14)
    expected = ((0, 2), (0, 3)) if ystep > 0 else ((1, 3), (0, 3))
    assert bounds_window(bounds, transform) == expected
    assert window_bounds(expected, transform) == (5, 10, 11, 16)
    assert bounds_window(window_bounds(expected, transform), transform) == expected


def test_southup_fractional_bounds_and_native_origin(southup_source):
    source, kwargs = southup_source
    with Raster(source, **kwargs) as raster:
        cropped = raster.read(bounds=(6, 11, 10, 14))
        np.testing.assert_array_equal(cropped.array, DATA[:2, :3])
        assert cropped.affine == TRANSFORM
        assert cropped.index(8, 14.5) == (1, 1)
        sub = raster.read(window=((1, 3), (1, 4)))
        np.testing.assert_array_equal(sub.array, DATA[1:3, 1:4])
        assert sub.affine == Affine(2, 0, 7, 0, 3, 13)
        reread = cropped.read(bounds=(7, 13, 11, 16))
        np.testing.assert_array_equal(reread.array, DATA[1:2, 1:3])
        assert reread.affine == Affine(2, 0, 7, 0, 3, 13)


def test_southup_boundless_mask_and_strict_extent(southup_source):
    source, kwargs = southup_source
    with Raster(source, **kwargs) as raster:
        padded = raster.read(bounds=(3, 7, 11, 16), masked=True)
        assert padded.array.shape == (3, 4)
        assert padded.affine == Affine(2, 0, 3, 0, 3, 7)
        assert padded.array.mask[0].all()
        assert padded.array.mask[:, 0].all()
        np.testing.assert_array_equal(padded.array[1:, 1:], DATA[:2, :3])
        with pytest.raises(ValueError, match="outside dataset extent"):
            raster.read(bounds=(3, 7, 11, 16), boundless=False)
        valid = raster.read(bounds=(7, 13, 11, 19), boundless=False)
        np.testing.assert_array_equal(valid.array, DATA[1:, 1:3])


def test_southup_zonal_stats_and_mini_raster(southup_source):
    source, kwargs = southup_source
    zone = box(7.2, 10.4, 10.9, 15.6)
    result = zonal_stats(
        [zone], source, stats="count sum mean", raster_out=True, **kwargs
    )[0]
    assert {key: result[key] for key in ["count", "sum", "mean"]} == {
        "count": 4,
        "sum": 260,
        "mean": 65,
    }
    np.testing.assert_array_equal(result["mini_raster_array"], DATA[:2, 1:3])
    assert result["mini_raster_affine"] == Affine(2, 0, 7, 0, 3, 10)


@pytest.mark.parametrize("interpolate", ["nearest", "bilinear"])
def test_southup_point_queries_match_pixel_reference(southup_source, interpolate):
    source, kwargs = southup_source
    # Native pixel centers and a true off-center interior bilinear query.
    points = [Point(8, 14.5), Point(8.5, 13.75)]
    expected = [110, 110] if interpolate == "nearest" else [110, 87.5]
    assert point_query(points, source, interpolate=interpolate, **kwargs) == expected
    assert point_query([Point(0, 0)], source, interpolate=interpolate, **kwargs) == [
        None
    ]


def test_southup_matches_equivalent_northup_grid():
    north = Affine(2, 0, 5, 0, -3, 19)
    points = [Point(8.5, 13.75), Point(10, 17.5)]
    for interpolation in ["nearest", "bilinear"]:
        expected = point_query(
            points, DATA[::-1], affine=north, nodata=NODATA, interpolate=interpolation
        )
        assert (
            point_query(
                points, DATA, affine=TRANSFORM, nodata=NODATA, interpolate=interpolation
            )
            == expected
        )
    zone = box(7.2, 10.4, 10.9, 15.6)
    expected = zonal_stats([zone], DATA[::-1], affine=north, nodata=NODATA)
    assert zonal_stats([zone], DATA, affine=TRANSFORM, nodata=NODATA) == expected


def test_southup_fractional_affine_and_three_dimensional_array():
    transform = Affine(1.25, 0, -2.5, 0, 0.75, 8.125)
    # Analytical coordinates for pixel corners (0.25,0.25) and (2.25,1.75).
    bounds = (-2.1875, 8.3125, 0.3125, 9.4375)
    assert bounds_window(bounds, transform) == ((0, 2), (0, 3))
    assert window_bounds(((0, 2), (0, 3)), transform) == (-2.5, 8.125, 1.25, 9.625)
    # Both dimensions use native array indices; bands are not flipped either.
    array = np.stack([DATA, DATA + 1000])
    with Raster(array, affine=transform, nodata=NODATA) as raster:
        result = raster.read(bounds=bounds)
        np.testing.assert_array_equal(result.array, array[:, :2, :3])
        assert result.affine == transform
