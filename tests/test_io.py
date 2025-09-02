import json
from pathlib import Path

import fiona
import numpy as np
import pytest
import rasterio
from shapely.geometry import shape

from rasterstats.io import (  # todo parse_feature
    fiona_generator,
    Raster,
    boundless_array,
    bounds_window,
    read_featurecollection,
    read_features,
    rowcol,
    window_bounds,
)

data_dir = Path(__file__).parent / "data"
polygons = data_dir / "polygons.shp"
raster = data_dir / "slope.tif"

arr = np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1]])

arr3d = np.array([[[1, 1, 1], [1, 1, 1], [1, 1, 1]]])

eps = 1e-6

target_features = [f for f in fiona_generator(polygons)]

target_geoms = [shape(f["geometry"]) for f in target_features]


def _compare_geomlists(aa, bb):
    for a, b in zip(aa, bb):
        assert a.equals_exact(b, eps)


def _test_read_features(indata):
    features = list(read_features(indata))
    # multi
    geoms = [shape(f["geometry"]) for f in features]
    _compare_geomlists(geoms, target_geoms)


def _test_read_features_single(indata):
    # single (first target geom)
    geom = shape(list(read_features(indata))[0]["geometry"])
    assert geom.equals_exact(target_geoms[0], eps)


def test_fiona_path():
    assert list(read_features(polygons)) == target_features


def test_layer_index():
    layer = fiona.listlayers(data_dir).index("polygons")
    assert list(read_features(data_dir, layer=layer)) == target_features


def test_layer_name():
    assert list(read_features(data_dir, layer="polygons")) == target_features


def test_path_unicode():
    try:
        upolygons = unicode(polygons)
    except NameError:
        # python3, it's already unicode
        upolygons = polygons
    assert list(read_features(upolygons)) == target_features


def test_featurecollection():
    assert (
        read_featurecollection(polygons)["features"]
        == list(read_features(polygons))
        == target_features
    )


def test_shapely():
    indata = [shape(f["geometry"]) for f in fiona_generator(polygons)]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_wkt():
    indata = [shape(f["geometry"]).wkt for f in fiona_generator(polygons)]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_wkb():
    indata = [shape(f["geometry"]).wkb for f in fiona_generator(polygons)]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_mapping_features():
    # list of Features
    indata = [f for f in fiona_generator(polygons)]
    _test_read_features(indata)


def test_mapping_feature():
    # list of Features
    indata = [f for f in fiona_generator(polygons)]
    _test_read_features(indata[0])


def test_mapping_geoms():
    indata = [f for f in fiona_generator(polygons)]
    _test_read_features(indata[0]["geometry"])


def test_mapping_collection():
    indata = {"type": "FeatureCollection"}
    indata["features"] = [f for f in fiona_generator(polygons)]
    _test_read_features(indata)


def test_jsonstr():
    # Feature str
    indata = [f for f in fiona_generator(polygons)]
    indata = json.dumps(indata[0])
    _test_read_features(indata)


def test_jsonstr_geom():
    # geojson geom str
    indata = [f for f in fiona_generator(polygons)]
    indata = json.dumps(indata[0]["geometry"])
    _test_read_features(indata)


def test_jsonstr_collection():
    indata = {"type": "FeatureCollection"}
    indata["features"] = [f for f in fiona_generator(polygons)]
    indata = json.dumps(indata)
    _test_read_features(indata)


def test_jsonstr_collection_without_features():
    indata = {"type": "FeatureCollection", "features": []}
    indata = json.dumps(indata)
    with pytest.raises(ValueError):
        _test_read_features(indata)


def test_invalid_jsonstr():
    indata = {"type": "InvalidGeometry", "coordinates": [30, 10]}
    indata = json.dumps(indata)
    with pytest.raises(ValueError):
        _test_read_features(indata)


class MockGeoInterface:
    def __init__(self, f):
        self.__geo_interface__ = f


def test_geo_interface():
    indata = [MockGeoInterface(f) for f in fiona_generator(polygons)]
    _test_read_features(indata)


def test_geo_interface_geom():
    indata = [MockGeoInterface(f["geometry"]) for f in fiona_generator(polygons)]
    _test_read_features(indata)


def test_geo_interface_collection():
    # geointerface for featurecollection?
    indata = {"type": "FeatureCollection"}
    indata["features"] = [f for f in fiona_generator(polygons)]
    indata = MockGeoInterface(indata)
    _test_read_features(indata)


def test_notafeature():
    with pytest.raises(ValueError):
        list(read_features(["foo", "POINT(-122 42)"]))

    with pytest.raises(ValueError):
        list(read_features(Exception()))


# Raster tests
def test_boundless():
    # Exact
    assert boundless_array(arr, window=((0, 3), (0, 3)), nodata=0).sum() == 9

    # Intersects
    assert boundless_array(arr, window=((-1, 2), (-1, 2)), nodata=0).sum() == 4
    assert boundless_array(arr, window=((1, 4), (-1, 2)), nodata=0).sum() == 4
    assert boundless_array(arr, window=((1, 4), (1, 4)), nodata=0).sum() == 4
    assert boundless_array(arr, window=((-1, 2), (1, 4)), nodata=0).sum() == 4

    # No overlap
    assert boundless_array(arr, window=((-4, -1), (-4, -1)), nodata=0).sum() == 0
    assert boundless_array(arr, window=((-4, -1), (4, 7)), nodata=0).sum() == 0
    assert boundless_array(arr, window=((4, 7), (4, 7)), nodata=0).sum() == 0
    assert boundless_array(arr, window=((4, 7), (-4, -1)), nodata=0).sum() == 0
    assert boundless_array(arr, window=((-3, 0), (-3, 0)), nodata=0).sum() == 0

    # Covers
    assert boundless_array(arr, window=((-1, 4), (-1, 4)), nodata=0).sum() == 9

    # 3D
    assert boundless_array(arr3d, window=((0, 3), (0, 3)), nodata=0).sum() == 9
    assert boundless_array(arr3d, window=((-1, 2), (-1, 2)), nodata=0).sum() == 4
    assert boundless_array(arr3d, window=((-3, 0), (-3, 0)), nodata=0).sum() == 0

    # 1D
    with pytest.raises(ValueError):
        boundless_array(np.array([1, 1, 1]), window=((0, 3),), nodata=0)


def test_boundless_masked():
    a = boundless_array(arr, window=((-4, -1), (-4, -1)), nodata=0, masked=True)
    assert a.mask.all()
    b = boundless_array(arr, window=((0, 3), (0, 3)), nodata=0, masked=True)
    assert not b.mask.any()
    c = boundless_array(arr, window=((-1, 2), (-1, 2)), nodata=0, masked=True)
    assert c.mask.any() and not c.mask.all()


def test_window_bounds():
    with rasterio.open(raster) as src:
        win = ((0, src.shape[0]), (0, src.shape[1]))
        assert src.bounds == window_bounds(win, src.transform)

        win = ((5, 10), (5, 10))
        assert src.window_bounds(win) == window_bounds(win, src.transform)


def test_bounds_window():
    with rasterio.open(raster) as src:
        assert bounds_window(src.bounds, src.transform) == (
            (0, src.shape[0]),
            (0, src.shape[1]),
        )


def test_rowcol():
    import math

    with rasterio.open(raster) as src:
        x, _, _, y = src.bounds
        x += 1.0
        y -= 1.0
        assert rowcol(x, y, src.transform, op=math.floor) == (0, 0)
        assert rowcol(x, y, src.transform, op=math.ceil) == (1, 1)


def test_Raster_index():
    x, y = 245114, 1000968
    with rasterio.open(raster) as src:
        c1, r1 = src.index(x, y)
    with Raster(raster) as rast:
        c2, r2 = rast.index(x, y)
    assert c1 == c2
    assert r1 == r2


def test_Raster():
    import numpy as np

    bounds = (244156, 1000258, 245114, 1000968)
    r1 = Raster(raster, band=1).read(bounds)

    with rasterio.open(raster) as src:
        arr = src.read(1)
        affine = src.transform
        nodata = src.nodata

    r2 = Raster(arr, affine, nodata, band=1).read(bounds)

    with pytest.raises(ValueError):
        r3 = Raster(arr, affine, nodata, band=1).read()
    with pytest.raises(ValueError):
        r4 = Raster(arr, affine, nodata, band=1).read(bounds=1, window=1)

    # If the abstraction is correct, the arrays are equal
    assert np.array_equal(r1.array, r2.array)


def test_Raster_boundless_disabled():
    import numpy as np

    bounds = (
        244300.61494985913,
        998877.8262535353,
        246444.72726211764,
        1000868.7876863468,
    )
    outside_bounds = (244156, 1000258, 245114, 1000968)

    # rasterio src fails outside extent
    with pytest.raises(ValueError):
        r1 = Raster(raster, band=1).read(outside_bounds, boundless=False)

    # rasterio src works inside extent
    r2 = Raster(raster, band=1).read(bounds, boundless=False)

    with rasterio.open(raster) as src:
        arr = src.read(1)
        affine = src.transform
        nodata = src.nodata

    # ndarray works inside extent
    r3 = Raster(arr, affine, nodata, band=1).read(bounds, boundless=False)

    # ndarray src fails outside extent
    with pytest.raises(ValueError):
        r4 = Raster(arr, affine, nodata, band=1).read(outside_bounds, boundless=False)

    # If the abstraction is correct, the arrays are equal
    assert np.array_equal(r2.array, r3.array)


def test_Raster_context():
    # Assigned a regular name, stays open
    r1 = Raster(raster, band=1)
    assert not r1.src.closed
    r1.src.close()

    # Used as a context manager, closes itself
    with Raster(raster, band=1) as r2:
        pass
    assert r2.src.closed


def test_geointerface():
    class MockGeo:
        def __init__(self, features):
            self.__geo_interface__ = {"type": "FeatureCollection", "features": features}

        # Make it iterable just to ensure that geo interface
        # takes precendence over iterability
        def __iter__(self):
            pass

        def __next__(self):
            pass

        def next(self):
            pass

    features = [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        },
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-50, -10], [-40, 10], [-30, -10], [-50, -10]]],
            },
        },
    ]

    geothing = MockGeo(features)
    assert list(read_features(geothing)) == features


# Optional tests
def test_geodataframe():
    gpd = pytest.importorskip("geopandas")

    df = gpd.read_file(polygons)
    if not hasattr(df, "__geo_interface__"):
        pytest.skip("This version of geopandas doesn't support df.__geo_interface__")
    assert list(read_features(df))


# TODO # io.parse_features on a feature-only geo_interface
# TODO # io.parse_features on a feature-only geojson-like object
# TODO # io.read_features on a feature-only
# TODO # io.Raster.read() on an open rasterio dataset
