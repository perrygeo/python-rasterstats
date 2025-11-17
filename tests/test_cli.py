import json
import warnings
from pathlib import Path

from click.testing import CliRunner

from rasterstats.cli import pointquery, zonalstats

# Some warnings must be ignored to parse output properly
# https://github.com/pallets/click/issues/371#issuecomment-223790894

data_dir = Path(__file__).parent / "data"


def test_cli_feature():
    raster = str(data_dir / "slope.tif")
    vector = str(data_dir / "feature.geojson")
    runner = CliRunner()
    warnings.simplefilter("ignore")
    result = runner.invoke(
        zonalstats, [vector, "--raster", raster, "--stats", "mean", "--prefix", "test_"]
    )
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    assert len(outdata["features"]) == 1
    feature = outdata["features"][0]
    assert "test_mean" in feature["properties"]
    assert round(feature["properties"]["test_mean"], 2) == 14.66
    assert "test_count" not in feature["properties"]


def test_cli_feature_stdin():
    raster = str(data_dir / "slope.tif")
    vector_pth = data_dir / "feature.geojson"

    runner = CliRunner()
    warnings.simplefilter("ignore")
    result = runner.invoke(
        zonalstats,
        ["--raster", raster, "--stats", "all", "--prefix", "test_"],
        input=vector_pth.read_text(),
    )
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    assert len(outdata["features"]) == 1
    feature = outdata["features"][0]
    assert "test_mean" in feature["properties"]
    assert "test_std" in feature["properties"]


def test_cli_features_sequence():
    raster = str(data_dir / "slope.tif")
    vector = str(data_dir / "featurecollection.geojson")
    runner = CliRunner()
    result = runner.invoke(
        zonalstats,
        [
            vector,
            "--raster",
            raster,
            "--stats",
            "mean",
            "--prefix",
            "test_",
            "--sequence",
        ],
    )
    assert result.exit_code == 0
    results = result.output.splitlines()
    for r in results:
        outdata = json.loads(r)
        assert outdata["type"] == "Feature"


def test_cli_features_sequence_rs():
    raster = str(data_dir / "slope.tif")
    vector = str(data_dir / "featurecollection.geojson")
    runner = CliRunner()
    result = runner.invoke(
        zonalstats,
        [
            vector,
            "--raster",
            raster,
            "--stats",
            "mean",
            "--prefix",
            "test_",
            "--sequence",
            "--rs",
        ],
    )
    assert result.exit_code == 0
    # assert result.output.startswith(b'\x1e')
    assert result.output[0] == "\x1e"


def test_cli_featurecollection():
    raster = str(data_dir / "slope.tif")
    vector = str(data_dir / "featurecollection.geojson")
    runner = CliRunner()
    result = runner.invoke(
        zonalstats, [vector, "--raster", raster, "--stats", "mean", "--prefix", "test_"]
    )
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    assert len(outdata["features"]) == 2
    feature = outdata["features"][0]
    assert "test_mean" in feature["properties"]
    assert round(feature["properties"]["test_mean"], 2) == 14.66
    assert "test_count" not in feature["properties"]


def test_cli_pointquery():
    raster = str(data_dir / "slope.tif")
    vector = str(data_dir / "featurecollection.geojson")
    runner = CliRunner()
    result = runner.invoke(
        pointquery, [vector, "--raster", raster, "--property-name", "slope"]
    )
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    assert len(outdata["features"]) == 2
    feature = outdata["features"][0]
    assert "slope" in feature["properties"]


def test_cli_point_sequence():
    raster = str(data_dir / "slope.tif")
    vector = str(data_dir / "featurecollection.geojson")
    runner = CliRunner()
    result = runner.invoke(
        pointquery,
        [vector, "--raster", raster, "--property-name", "slope", "--sequence"],
    )
    assert result.exit_code == 0
    results = result.output.splitlines()
    for r in results:
        outdata = json.loads(r)
        assert outdata["type"] == "Feature"


def test_cli_point_sequence_rs():
    raster = str(data_dir / "slope.tif")
    vector = str(data_dir / "featurecollection.geojson")
    runner = CliRunner()
    result = runner.invoke(
        pointquery,
        [vector, "--raster", raster, "--property-name", "slope", "--sequence", "--rs"],
    )
    assert result.exit_code == 0
    assert result.output[0] == "\x1e"
