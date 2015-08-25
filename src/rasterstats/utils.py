# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import math
import sys
from rasterio import features
from affine import Affine


def bbox_to_pixel_offsets(gt, bbox, rshape):
    originX = gt[0]
    originY = gt[3]
    pixel_width = gt[1]
    pixel_height = gt[5]

    col1 = int(math.floor((bbox[0] - originX) / pixel_width))
    col2 = int(math.ceil((bbox[2] - originX) / pixel_width))

    row1 = int(math.floor((bbox[3] - originY) / pixel_height))
    row2 = int(math.ceil((bbox[1] - originY) / pixel_height))

    # "Clip" the geometry bounds to the overall raster bounding box
    # This should avoid any rasterIO errors for partially overlapping polys
    if col1 < 0:
        col1 = 0
    if col2 > rshape[0]:
        col2 = rshape[0]
    if row1 < 0:
        row1 = 0
    if row2 > rshape[1]:
        row2 = rshape[1]

    cols = col2 - col1
    rows = row2 - row1

    return (col1, row1, cols, rows)


def pixel_offsets_to_window(offsets):
    """
    Convert (col1, row1, cols, rows)
    to a rasterio-compatible window
    https://github.com/mapbox/rasterio/blob/master/docs/windowed-rw.rst#windows
    """
    if len(offsets) != 4:
        raise ValueError("offset should be a 4-element tuple")
    col1, row1, cols, rows = offsets
    return ((row1, row1 + rows), (col1, col1 + cols))


def raster_extent_as_bounds(gt, shape):
    x1 = gt[0]
    x2 = gt[0] + (gt[1] * shape[0])
    y1 = gt[3] + (gt[5] * shape[1])
    y2 = gt[3]
    return (x1, y1, x2, y2)


def get_percentile(stat):
    if not stat.startswith('percentile_'):
        raise ValueError("must start with 'percentile_'")
    qstr = stat.replace("percentile_", '')
    q = float(qstr)
    if q > 100.0:
        raise ValueError('percentiles must be <= 100')
    if q < 0.0:
        raise ValueError('percentiles must be >= 0')
    return q


def rasterize_geom(geom, src_offset, new_gt, all_touched):
    geoms = [(geom, 1)]
    affinetrans = Affine.from_gdal(*new_gt)
    rv_array = features.rasterize(
        geoms,
        out_shape=(src_offset[3], src_offset[2]),
        transform=affinetrans,
        fill=0,
        all_touched=all_touched)
    return rv_array


def is_nan(x):
    return isinstance(x, float) and math.isnan(x)


def combine_features_results(features, results, prefix, nan_to_None=True):
    """
    Given a list of geojson features and a list of zonal stats results
    Append the zonal stats to the feature's properties and yield a new feature
    """
    assert len(features) == len(results)
    for feat, res in zip(features, results):
        for key, val in res.items():
            if key == "__fid__":
                continue
            prefixed_key = "{}{}".format(prefix, key)

            # normalize
            if nan_to_None and is_nan(val):
                val = None

            feat['properties'][prefixed_key] = val
        yield feat


def stats_to_csv(stats):
    if sys.version_info[0] >= 3:
        from io import StringIO as IO
    else:
        from cStringIO import StringIO as IO
    import csv

    csv_fh = IO()

    keys = set()
    for stat in stats:
        for key in list(stat.keys()):
            keys.add(key)

    fieldnames = sorted(list(keys), key=str)

    csvwriter = csv.DictWriter(csv_fh, delimiter=str(","), fieldnames=fieldnames)
    csvwriter.writerow(dict((fn, fn) for fn in fieldnames))
    for row in stats:
        csvwriter.writerow(row)
    contents = csv_fh.getvalue()
    csv_fh.close()
    return contents

