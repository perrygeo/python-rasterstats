from __future__ import print_function
"""
First, download the data and place in `benchmark_data`

1. Download countries from
    wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/50m/cultural/ne_50m_admin_0_countries.zip
    unzip

2. Download the SRTM data from
    https://hc.app.box.com/shared/1yidaheouv
    Password is `ThanksCSI!`
    select `SRTM_1km_TIF.rar`
    $ unrar e SRTM_1km_TIF.rar

Runtime history:
   1bc8711 130.93s MacBook Pro (Retina, 15-inch, Mid 2014) 2.2GHz i7, 16GB RAM
   2277962  80.68s MacBook Pro (Retina, 15-inch, Mid 2014) 2.2GHz i7, 16GB RAM
"""
from rasterstats import zonal_stats
import time

class Timer():
    def __enter__(self):
        self.start = time.time()

    def __exit__(self, *args):
        print("Time:", time.time() - self.start)

countries = "./benchmark_data/ne_50m_admin_0_countries.shp"
elevation = "./benchmark_data/SRTM_1km.tif"

with Timer():
    stats = zonal_stats(countries, elevation, stats="*")
