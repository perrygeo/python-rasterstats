import os.path
import json
from click.testing import CliRunner
from rasterstats.cli import zonalstats


def test_cli_geometry():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/geometry.geojson')
    runner = CliRunner()
    result = runner.invoke(zonalstats, [vector, '-',
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

def test_cli_feature():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/feature.geojson')
    runner = CliRunner()
    result = runner.invoke(zonalstats, [vector, '-',
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

def test_cli_featurecollection():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/featurecollection.geojson')
    runner = CliRunner()
    result = runner.invoke(zonalstats, [vector, '-',
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
