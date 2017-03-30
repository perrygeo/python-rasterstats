import os.path
import json
import warnings
# Some warnings must be ignored to parse output properly
# https://github.com/pallets/click/issues/371#issuecomment-223790894

from click.testing import CliRunner
from rasterstats.cli import zonalstats, pointquery


def test_cli_feature():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/feature.geojson')
    runner = CliRunner()
    warnings.simplefilter('ignore')
    result = runner.invoke(zonalstats, [vector,
                                        '--raster', raster,
                                        '--stats', 'mean',
                                        '--prefix', 'test_'])
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    assert len(outdata['features']) == 1
    feature = outdata['features'][0]
    assert 'test_mean' in feature['properties']
    assert round(feature['properties']['test_mean'], 2) == 14.66
    assert 'test_count' not in feature['properties']


def test_cli_feature_stdin():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/feature.geojson')

    runner = CliRunner()
    warnings.simplefilter('ignore')
    result = runner.invoke(zonalstats,
                           ['--raster', raster,
                            '--stats', 'all',
                            '--prefix', 'test_'],
                           input=open(vector, 'r').read())
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    assert len(outdata['features']) == 1
    feature = outdata['features'][0]
    assert 'test_mean' in feature['properties']
    assert 'test_std' in feature['properties']


def test_cli_features_sequence():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/featurecollection.geojson')
    runner = CliRunner()
    result = runner.invoke(zonalstats, [vector,
                                        '--raster', raster,
                                        '--stats', 'mean',
                                        '--prefix', 'test_',
                                        '--sequence'])
    assert result.exit_code == 0
    results = result.output.splitlines()
    for r in results:
        outdata = json.loads(r)
        assert outdata['type'] == 'Feature'


def test_cli_features_sequence_rs():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/featurecollection.geojson')
    runner = CliRunner()
    result = runner.invoke(zonalstats, [vector,
                                        '--raster', raster,
                                        '--stats', 'mean',
                                        '--prefix', 'test_',
                                        '--sequence', '--rs'])
    assert result.exit_code == 0
    # assert result.output.startswith(b'\x1e')
    assert result.output[0] == '\x1e'


def test_cli_featurecollection():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/featurecollection.geojson')
    runner = CliRunner()
    result = runner.invoke(zonalstats, [vector,
                                        '--raster', raster,
                                        '--stats', 'mean',
                                        '--prefix', 'test_'])
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    assert len(outdata['features']) == 2
    feature = outdata['features'][0]
    assert 'test_mean' in feature['properties']
    assert round(feature['properties']['test_mean'], 2) == 14.66
    assert 'test_count' not in feature['properties']


def test_cli_pointquery():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/featurecollection.geojson')
    runner = CliRunner()
    result = runner.invoke(pointquery, [vector,
                                        '--raster', raster,
                                        '--property-name', 'slope'])
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    assert len(outdata['features']) == 2
    feature = outdata['features'][0]
    assert 'slope' in feature['properties']

def test_cli_point_sequence():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/featurecollection.geojson')
    runner = CliRunner()
    result = runner.invoke(pointquery, [vector,
                                        '--raster', raster,
                                        '--property-name', 'slope',
                                        '--sequence'])
    assert result.exit_code == 0
    results = result.output.splitlines()
    for r in results:
        outdata = json.loads(r)
        assert outdata['type'] == 'Feature'


def test_cli_point_sequence_rs():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/featurecollection.geojson')
    runner = CliRunner()
    result = runner.invoke(pointquery, [vector,
                                        '--raster', raster,
                                        '--property-name', 'slope',
                                        '--sequence', '--rs'])
    assert result.exit_code == 0
    assert result.output[0] == '\x1e'
