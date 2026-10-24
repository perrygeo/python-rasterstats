import json
from pathlib import Path

import numpy as np
import pyogrio
import pytest
import rasterio
from shapely.geometry import shape

from rasterstats.io import (  # todo parse_feature
    Raster,
    _is_vector_file,
    boundless_array,
    bounds_window,
    feature_generator,
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

target_features = list(feature_generator(polygons))

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
    geom = shape(next(iter(read_features(indata)))["geometry"])
    assert geom.equals_exact(target_geoms[0], eps)


def test_fiona_path():
    """read_features on a path uses pyogrio default; geometries match."""
    features = list(read_features(polygons))
    geoms = [shape(f["geometry"]) for f in features]
    _compare_geomlists(geoms, target_geoms)


def test_layer_index():
    fiona = pytest.importorskip("fiona")
    layer = fiona.listlayers(data_dir).index("polygons")
    result = list(read_features(data_dir, layer=layer))
    geoms = [shape(f["geometry"]) for f in result]
    _compare_geomlists(geoms, target_geoms)


def test_layer_name():
    result = list(read_features(data_dir, layer="polygons"))
    geoms = [shape(f["geometry"]) for f in result]
    _compare_geomlists(geoms, target_geoms)


def test_path_unicode():
    try:
        upolygons = unicode(polygons)
    except NameError:
        # python3, it's already unicode
        upolygons = polygons
    result = list(read_features(upolygons))
    geoms = [shape(f["geometry"]) for f in result]
    _compare_geomlists(geoms, target_geoms)


def test_featurecollection():
    fc_features = read_featurecollection(polygons)["features"]
    rf_features = list(read_features(polygons))
    geoms_fc = [shape(f["geometry"]) for f in fc_features]
    geoms_rf = [shape(f["geometry"]) for f in rf_features]
    _compare_geomlists(geoms_fc, target_geoms)
    _compare_geomlists(geoms_rf, target_geoms)


def test_shapely():
    indata = [shape(f["geometry"]) for f in feature_generator(polygons)]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_wkt():
    indata = [shape(f["geometry"]).wkt for f in feature_generator(polygons)]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_wkb():
    indata = [shape(f["geometry"]).wkb for f in feature_generator(polygons)]
    _test_read_features(indata)
    _test_read_features_single(indata[0])


def test_mapping_features():
    # list of Features
    indata = list(feature_generator(polygons))
    _test_read_features(indata)


def test_mapping_feature():
    # list of Features
    indata = list(feature_generator(polygons))
    _test_read_features(indata[0])


def test_mapping_geoms():
    indata = list(feature_generator(polygons))
    _test_read_features(indata[0]["geometry"])


def test_mapping_collection():
    indata = {"type": "FeatureCollection"}
    indata["features"] = list(feature_generator(polygons))
    _test_read_features(indata)


def test_jsonstr():
    # Feature str
    indata = list(feature_generator(polygons))
    indata = json.dumps(indata[0])
    _test_read_features(indata)


def test_jsonstr_geom():
    # geojson geom str
    indata = list(feature_generator(polygons))
    indata = json.dumps(indata[0]["geometry"])
    _test_read_features(indata)


def test_jsonstr_collection():
    indata = {"type": "FeatureCollection"}
    indata["features"] = list(feature_generator(polygons))
    indata = json.dumps(indata)
    _test_read_features(indata)


def test_jsonstr_collection_without_features():
    indata = {"type": "FeatureCollection", "features": []}
    indata = json.dumps(indata)
    # RFC 7946 section 3.3 permits an empty features array.
    assert list(read_features(indata)) == []


def test_invalid_jsonstr():
    indata = {"type": "InvalidGeometry", "coordinates": [30, 10]}
    indata = json.dumps(indata)
    with pytest.raises(ValueError):
        _test_read_features(indata)


class MockGeoInterface:
    def __init__(self, f):
        self.__geo_interface__ = f


def test_geo_interface():
    indata = [MockGeoInterface(f) for f in feature_generator(polygons)]
    _test_read_features(indata)


def test_geo_interface_geom():
    indata = [MockGeoInterface(f["geometry"]) for f in feature_generator(polygons)]
    _test_read_features(indata)


def test_geo_interface_collection():
    # geointerface for featurecollection?
    indata = {"type": "FeatureCollection"}
    indata["features"] = list(feature_generator(polygons))
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
        Raster(arr, affine, nodata, band=1).read()
    with pytest.raises(ValueError):
        Raster(arr, affine, nodata, band=1).read(bounds=1, window=1)

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
        Raster(raster, band=1).read(outside_bounds, boundless=False)

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
        Raster(arr, affine, nodata, band=1).read(outside_bounds, boundless=False)

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


# feature_generator / engine tests


def test_feature_generator_pyogrio_default():
    """feature_generator with no engine= uses pyogrio (new default)."""
    result = list(feature_generator(polygons))
    geoms = [shape(f["geometry"]) for f in result]
    _compare_geomlists(geoms, target_geoms)


def test_feature_generator_explicit_fiona():
    """feature_generator with engine='fiona' yields correct geometries."""
    pytest.importorskip("fiona")
    result = list(feature_generator(polygons, engine="fiona"))
    geoms = [shape(f["geometry"]) for f in result]
    _compare_geomlists(geoms, target_geoms)


def test_feature_generator_pyogrio():
    """feature_generator with engine='pyogrio' yields same geometries."""
    pytest.importorskip("pyogrio")
    result = list(feature_generator(polygons, engine="pyogrio"))
    geoms = [shape(f["geometry"]) for f in result]
    _compare_geomlists(geoms, target_geoms)


def test_feature_generator_pyogrio_properties():
    """pyogrio engine preserves feature properties."""
    pytest.importorskip("pyogrio")
    result = list(feature_generator(polygons, engine="pyogrio"))
    assert all("properties" in f for f in result)
    assert all("id" in f["properties"] for f in result)


def test_feature_generator_invalid_engine():
    """An unrecognised engine name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown engine"):
        list(feature_generator(polygons, engine="gdal"))


def test_read_features_pyogrio_engine():
    """read_features forwards engine= to the underlying generator."""
    pytest.importorskip("pyogrio")
    result = list(read_features(polygons, engine="pyogrio"))
    geoms = [shape(f["geometry"]) for f in result]
    _compare_geomlists(geoms, target_geoms)


def test_pyogrio_null_geometry(tmp_path):
    """_pyogrio_generator yields None geometry for features with null geometry
    rather than raising AttributeError."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "properties": {"n": 1},
            },
            {"type": "Feature", "geometry": None, "properties": {"n": 2}},
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1, 1]},
                "properties": {"n": 3},
            },
        ],
    }
    p = tmp_path / "null_geom.geojson"
    p.write_text(json.dumps(geojson))

    results = list(feature_generator(str(p), engine="pyogrio"))
    assert len(results) == 3
    assert results[0]["geometry"] is not None
    assert results[1]["geometry"] is None
    assert results[2]["geometry"] is not None
    assert results[1]["properties"]["n"] == 2


def test_pyogrio_unknown_feature_count(tmp_path, monkeypatch):
    """_pyogrio_generator reads all features when read_info returns features=-1.

    Some GDAL drivers (e.g. WFS) cannot report feature count ahead of time and
    return -1.  The old ``while skip < total`` loop silently yielded nothing in
    this case.  The new unconditional loop must still yield all features.
    """
    import pyogrio

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(i), 0.0]},
                "properties": {"n": i},
            }
            for i in range(5)
        ],
    }
    p = tmp_path / "unknown_count.geojson"
    p.write_text(json.dumps(geojson))

    real_read_info = pyogrio.read_info

    def fake_read_info(path, **kwargs):
        info = real_read_info(path, **kwargs)
        info["features"] = -1
        return info

    monkeypatch.setattr(pyogrio, "read_info", fake_read_info)
    # Also patch the name used inside the io module
    import rasterstats.io as io_mod

    monkeypatch.setattr(io_mod, "pyogrio", pyogrio)

    results = list(feature_generator(str(p), engine="pyogrio"))
    assert len(results) == 5
    assert [f["properties"]["n"] for f in results] == list(range(5))


# Test detection of vector files
# Private function but deserves unit tests


def test_is_vector_file():
    assert _is_vector_file(polygons, "polygons")


def test_wrong_vector_layer():
    "Data source is fine. DataLayerErrors pass through to fail fast."
    with pytest.raises(pyogrio.errors.DataLayerError):
        _is_vector_file(polygons, "something-else")


def test_isnt_vector_file():
    assert not _is_vector_file(raster, "raster")


def test_is_absent_file():
    assert not _is_vector_file("/tmp/sdfjaohgoadfknkjdsfj", "dnf")


# Optional tests


def test_geodataframe():
    gpd = pytest.importorskip("geopandas")

    df = gpd.read_file(polygons)
    if not hasattr(df, "__geo_interface__"):
        pytest.skip("This version of geopandas doesn't support df.__geo_interface__")
    assert list(read_features(df))


@pytest.mark.parametrize("as_text", [False, True])
def test_empty_featurecollection(as_text):
    collection = {"type": "FeatureCollection", "features": []}
    source = json.dumps(collection) if as_text else collection
    assert list(read_features(source)) == []


def test_empty_geodataframe():
    gpd = pytest.importorskip("geopandas")

    frame = gpd.read_file(polygons).iloc[:0]
    assert list(read_features(frame)) == []


@pytest.mark.parametrize("engine", ["pyogrio", "fiona"])
def test_empty_vector_file(tmp_path, engine):
    if engine == "fiona":
        pytest.importorskip("fiona")
    path = tmp_path / "empty.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    assert _is_vector_file(path, 0)
    assert list(read_features(path, engine=engine)) == []


@pytest.mark.parametrize("filename", ["123", "{}"])
@pytest.mark.parametrize("as_path", [False, True])
def test_json_like_filename(tmp_path, monkeypatch, filename, as_path):
    collection = read_featurecollection(polygons)
    monkeypatch.chdir(tmp_path)
    path = Path(filename)
    path.write_text(json.dumps(collection))
    features = list(read_features(path if as_path else filename))
    assert len(features) == len(target_geoms)
    _compare_geomlists([shape(f["geometry"]) for f in features], target_geoms)


def test_feature_generator_chunk_size(tmp_path):
    """Reading with default engine vs alternative chunk sizes,
    all result in equivalent feature dicts."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(i), 0.0]},
                "properties": {"n": i},
            }
            for i in range(6)
        ],
    }
    p = tmp_path / "chunked.geojson"
    p.write_text(json.dumps(geojson))

    default_results = list(feature_generator(polygons))
    small_chunk_results = list(feature_generator(polygons, chunk_size=2))

    assert default_results == small_chunk_results


def test_feature_generator_engines(tmp_path):
    """Reading with default engine vs fiona engine,
    all result in equivalent feature dicts."""
    _ = pytest.importorskip("fiona")
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(i), 0.0]},
                "properties": {"n": i},
            }
            for i in range(6)
        ],
    }
    p = tmp_path / "chunked.geojson"
    p.write_text(json.dumps(geojson))

    default_results = list(feature_generator(polygons))
    fiona_results = list(feature_generator(polygons, engine="fiona", chunk_size=2))

    # cannot compare them directly since they differ in tuples vs list representation for some reason
    # let json roundtrip normalize it
    assert json.loads(json.dumps(default_results)) == json.loads(
        json.dumps(fiona_results)
    )


# TODO # io.parse_features on a feature-only geo_interface
# TODO # io.parse_features on a feature-only geojson-like object
# TODO # io.read_features on a feature-only
# TODO # io.Raster.read() on an open rasterio dataset
