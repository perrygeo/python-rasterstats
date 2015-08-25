from rasterstats import zonal_stats

polys = "../tests/data/multilines.shp"
raster = "../tests/data/slope.tif"
stats = zonal_stats(polys, raster, stats="*")

from pprint import pprint
pprint(stats)
