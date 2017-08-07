# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import sys
from rasterio import features
from shapely.geometry import box, MultiPolygon
from .io import window_bounds


DEFAULT_STATS = ['count', 'min', 'max', 'mean']
VALID_STATS = DEFAULT_STATS + \
    ['sum', 'std', 'median', 'majority', 'minority', 'unique', 'range', 'nodata', 'nan']
#  also percentile_{q} but that is handled as special case


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


def round_to_grid(point, origin, pixel_size):
    """Round longitude, latitude values to nearest pixel edges

    Uses an origin's longitude, latitude value (upper left
    corner coordinates) along with pixel size to adjust
    an arbitrary point's longitude and latitude values to align
    with cell edges

    Assumes origin represents edge of pixel and not centroid

    Use to identify x or y coordinate of line for split_geom function
    to avoid splitting a geometry along the middle of a pixel. Splitting
    along the edge of pixels prevents errors when using percent cover
    options.
    """
    x_val, y_val = point
    x_origin, y_origin = origin
    if x_val < x_origin or y_val < y_origin:
        raise Exception("Longitude/latitude values for point cannot be less than "
                        "the longitude/latitude values for the origin.")
    adj_x_val = round((x_val - x_origin) / pixel_size) * pixel_size + x_origin
    adj_y_val = round((y_val - y_origin) / pixel_size) * pixel_size + y_origin
    return (adj_x_val, adj_y_val)


def split_geom(geom, limit, pixel_size, origin=None):
    """ split geometry into smaller geometries

    used to convert large features into multiple smaller features
    so that they can be used without running into memory limits

    Parameters
    ----------
    geom: geometry
    limit: maximum number of pixels
    pixel_size: pixel size of raster data geometry will be extracting

    Returns
    -------
    list of geometries
    """
    split_geom_list = []

    gb = tuple(geom.bounds)

    x_size = (gb[2] - gb[0]) / pixel_size
    y_size = (gb[3] - gb[1]) / pixel_size
    total_size = x_size * y_size

    if total_size < limit:
        return [geom]

    if x_size > y_size:
        x_split = gb[2] - (gb[2]-gb[0])/2
        if origin is not None:
            x_split = round_to_grid((x_split, origin[1]), origin, pixel_size)[0]
        box_a_bounds = (gb[0], gb[1], x_split, gb[3])
        box_b_bounds = (x_split, gb[1], gb[2], gb[3])

    else:
        y_split = gb[3] - (gb[3]-gb[1])/2
        if origin is not None:
            y_split = round_to_grid((origin[0], y_split), origin, pixel_size)[1]
        box_a_bounds = (gb[0], gb[1], gb[2], y_split)
        box_b_bounds = (gb[0], y_split, gb[2], gb[3])

    box_a = box(*box_a_bounds)
    geom_a = geom.intersection(box_a)
    split_a = split_geom(geom_a, limit, pixel_size)
    split_geom_list += split_a

    box_b = box(*box_b_bounds)
    geom_b = geom.intersection(box_b)
    split_b = split_geom(geom_b, limit, pixel_size)
    split_geom_list += split_b

    return split_geom_list


def rasterize_geom(geom, like, all_touched=False):
    """
    Parameters
    ----------
    geom: GeoJSON geometry
    like: raster object with desired shape and transform
    all_touched: rasterization strategy

    Returns
    -------
    ndarray: boolean
    """
    geoms = [(geom, 1)]
    rv_array = features.rasterize(
        geoms,
        out_shape=like.shape,
        transform=like.affine,
        fill=0,
        dtype='uint8',
        all_touched=all_touched)

    return rv_array.astype(bool)


def stats_to_csv(stats):
    if sys.version_info[0] >= 3:
        from io import StringIO as IO  # pragma: no cover
    else:
        from cStringIO import StringIO as IO  # pragma: no cover

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


def check_stats(stats, categorical):
    if not stats:
        if not categorical:
            stats = DEFAULT_STATS
        else:
            stats = []
    else:
        if isinstance(stats, str):
            if stats in ['*', 'ALL']:
                stats = VALID_STATS
            else:
                stats = stats.split()
    for x in stats:
        if x.startswith("percentile_"):
            get_percentile(x)
        elif x not in VALID_STATS:
            raise ValueError(
                "Stat `%s` not valid; "
                "must be one of \n %r" % (x, VALID_STATS))

    run_count = False
    if categorical or 'majority' in stats or 'minority' in stats or 'unique' in stats:
        # run the counter once, only if needed
        run_count = True

    return stats, run_count


def remap_categories(category_map, stats):
    def lookup(m, k):
        """ Dict lookup but returns original key if not found
        """
        try:
            return m[k]
        except KeyError:
            return k

    return {lookup(category_map, k): v
            for k, v in stats.items()}


def key_assoc_val(d, func, exclude=None):
    """return the key associated with the value returned by func
    """
    vs = list(d.values())
    ks = list(d.keys())
    key = ks[vs.index(func(vs))]
    return key


def boxify_points(geom, rast):
    """
    Point and MultiPoint don't play well with GDALRasterize
    convert them into box polygons 99% cellsize, centered on the raster cell
    """
    if 'Point' not in geom.type:
        raise ValueError("Points or multipoints only")

    buff = -0.01 * min(rast.affine.a, rast.affine.e)

    if geom.type == 'Point':
        pts = [geom]
    elif geom.type == "MultiPoint":
        pts = geom.geoms
    geoms = []
    for pt in pts:
        row, col = rast.index(pt.x, pt.y)
        win = ((row, row + 1), (col, col + 1))
        geoms.append(box(*window_bounds(win, rast.affine)).buffer(buff))

    return MultiPolygon(geoms)
