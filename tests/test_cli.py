import os.path
import json
from click.testing import CliRunner
from rasterstats.cli import zonalstats


def test_cli_basic():
    raster = os.path.join(os.path.dirname(__file__), 'data/slope.tif')
    vector = os.path.join(os.path.dirname(__file__), 'data/polygons.geojson')
    runner = CliRunner()
    result = runner.invoke(zonalstats, [vector, '-',
                                        '--raster', raster,
                                        '--stats', 'mean',
                                        '--prefix', 'test_'])
    assert result.exit_code == 0
    outdata = json.loads(result.output)
    feature = outdata['features'][0]
    assert 'test_mean' in feature['properties']
    assert 'test_count' not in feature['properties']
