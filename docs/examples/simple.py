from rasterstats import raster_stats
from pprint import pprint
polys = "tests/data/multilines.shp"
raster = "tests/data/slope.tif"
pprint(raster_stats(polys, raster, stats="*"))
