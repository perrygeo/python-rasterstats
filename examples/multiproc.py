#!/usr/bin/env python
import itertools
from multiprocessing import Pool
import multiprocessing

from rasterstats import zonal_stats
import fiona


shp = "benchmark_data/ne_50m_admin_0_countries.shp"
tif = "benchmark_data/srtm.tif"


def chunks(data, n):
    """Yield successive n-sized chunks from list data."""
    for i in range(0, len(data), n):
        yield data[i:i+n]


def zonal_stats_partial(feats):
    """Wrapper for zonal stats, takes a list of features"""
    return zonal_stats(feats, tif, all_touched=True)


if __name__ == "__main__":

    with fiona.open(shp) as src:
        features = list(src)

    # Create a process pool using all cores
    cores = multiprocessing.cpu_count()
    p = Pool(cores)

    # parallel map
    stats_lists = p.map(zonal_stats_partial, chunks(features, cores))

    # flatten to a single list
    stats = itertools.chain(*stats_lists)
