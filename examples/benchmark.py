from rasterstats import raster_stats
import time

class Timer():
    def __enter__(self):
        self.start = time.time()
    def __exit__(self, *args):
        print "Time:", time.time() - self.start

states = '/data/workspace/rasterstats_blog/boundaries_contus.shp'
precip = '/data/workspace/rasterstats_blog/NA_Annual_Precipitation_GRID/NA_Annual_Precipitation/data/na_anprecip/hdr.adf'
with Timer():
    stats = raster_stats(states, precip, stats="*")

