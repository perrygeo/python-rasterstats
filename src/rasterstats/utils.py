# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import math
import sys
from rasterio import features
from affine import Affine


class OGRError(Exception):
    pass


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
    x1, y1, xsize, ysize = offsets
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


def feature_to_geojson(feature):
    """ This duplicates the feature.ExportToJson ogr method
    but is safe across gdal versions since it was fixed only in 1.8+
    see http://trac.osgeo.org/gdal/ticket/3870"""

    geom = feature.GetGeometryRef()
    if geom is not None:
        geom_json_string = geom.ExportToJson()
        geom_json_object = json.loads(geom_json_string)
    else:
        geom_json_object = None

    output = {
        'type': 'Feature',
        'geometry': geom_json_object,
        'properties': {}
    }

    fid = feature.GetFID()
    if fid:
        output['fid'] = fid

    for key in list(feature.keys()):
        output['properties'][key] = feature.GetField(key)

    return output


def shapely_to_ogr_type(shapely_type):
    from osgeo import ogr
    if shapely_type == "Polygon":
        return ogr.wkbPolygon
    elif shapely_type == "LineString":
        return ogr.wkbLineString
    elif shapely_type == "MultiPolygon":
        return ogr.wkbMultiPolygon
    elif shapely_type == "MultiLineString":
        return ogr.wkbLineString
    raise TypeError("shapely type %s not supported" % shapely_type)


def parse_geo(thing):
    """ Given a python object, try to get a geo-json like mapping from it
    """
    from shapely.geos import ReadingError
    from shapely import wkt, wkb

    # object implementing geo_interface
    try:
        geo = thing.__geo_interface__
        return geo
    except AttributeError:
        pass

    # wkb
    try:
        shape = wkb.loads(thing)
        return shape.__geo_interface__
    except (ReadingError, TypeError):
        pass

    # wkt
    try:
        shape = wkt.loads(thing)
        return shape.__geo_interface__
    except (ReadingError, TypeError, AttributeError):
        pass

    # geojson-like python mapping
    valid_types = ["Feature", "Point", "LineString", "Polygon",
                   "MultiPoint", "MultiLineString", "MultiPolygon"]
    try:
        assert thing['type'] in valid_types
        return thing
    except (AssertionError, TypeError):
        pass

    # geojson string
    try:
        maybe_geo = json.loads(thing)
        assert maybe_geo['type'] in valid_types + ["FeatureCollection"]
        return maybe_geo
    except (ValueError, AssertionError, TypeError):
        pass

    raise ValueError("Can't parse %s as a geo-like object" % thing)


def get_ogr_ds(vds):
    from osgeo import ogr
    if not isinstance(vds, str):
        raise OGRError("OGR cannot open %r: not a string" % vds)

    ds = ogr.Open(vds)
    if not ds:
        raise OGRError("OGR cannot open %r" % vds)

    return ds


def ogr_srs(vector, layer_num):
    ds = get_ogr_ds(vector)
    layer = ds.GetLayer(layer_num)
    return layer.GetSpatialRef()


def ogr_records(vector, layer_num=0):
    ds = get_ogr_ds(vector)
    layer = ds.GetLayer(layer_num)
    if layer.GetFeatureCount() == 0:
        raise OGRError("No Features")
    feature = layer.GetNextFeature()
    while feature is not None:
        yield feature_to_geojson(feature)
        feature = layer.GetNextFeature()


def geo_records(vectors):
    for vector in vectors:
        yield parse_geo(vector)


def get_features(vectors, layer_num=0):
    from osgeo import osr
    spatial_ref = osr.SpatialReference()
    if isinstance(vectors, str):
        try:
            # either an OGR layer ...
            get_ogr_ds(vectors)
            features_iter = ogr_records(vectors, layer_num)
            spatial_ref = ogr_srs(vectors, layer_num)
            strategy = "ogr"
        except (OGRError, AttributeError):
            # ... or a single string to be parsed as wkt/wkb/json
            feat = parse_geo(vectors)
            features_iter = [feat]
            strategy = "single_geo"
    elif isinstance(vectors, bytes):
        # wkb
        feat = parse_geo(vectors)
        features_iter = [feat]
        strategy = "single_geo"
    elif hasattr(vectors, '__geo_interface__'):
        geotype = vectors.__geo_interface__['type']
        if geotype.lower() == 'featurecollection':
            # ... a featurecollection
            features_iter = geo_records(vectors.__geo_interface__['features'])
            strategy = "geo_featurecollection"
        else:
            # ... or an single object
            feat = parse_geo(vectors)
            features_iter = [feat]
            strategy = "single_geo"
    elif isinstance(vectors, dict):
        # ... or an python mapping
        feat = parse_geo(vectors)
        features_iter = [feat]
        strategy = "single_geo"
    else:
        # ... or an iterable of objects
        features_iter = geo_records(vectors)
        strategy = "iter_geo"

    return features_iter, strategy, spatial_ref


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
    Append the zonal stats to the feature's properties and yield the feature
    """
    # TODO call this join instead of combine?
    assert len(features) == len(results)
    for feat, res in zip(features, results):
        for key, val in res.items():
            if key == "__fid__":
                continue
            prefixed_key = "{}{}".format(prefix, key)

            # TODO Not certain if this is the correct place for this functionality
            # maybe belongs in zonal_stats?
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
