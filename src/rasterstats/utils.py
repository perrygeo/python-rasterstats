# -*- coding: utf-8 -*-
import json
from osgeo import ogr, gdal
from shapely import wkt, wkb
from shapely.geos import ReadingError

ogr.UseExceptions()

class RasterStatsError(Exception):
    pass


class OGRError(Exception):
    pass


def bbox_to_pixel_offsets(gt, bbox):
    originX = gt[0]
    originY = gt[3]
    pixel_width = gt[1]
    pixel_height = gt[5]

    x1 = int((bbox[0] - originX) / pixel_width)
    x2 = int((bbox[2] - originX) / pixel_width) + 1

    y1 = int((bbox[3] - originY) / pixel_height)
    y2 = int((bbox[1] - originY) / pixel_height) + 1

    xsize = x2 - x1
    ysize = y2 - y1
    return (x1, y1, xsize, ysize)


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

    output = {'type':'Feature',
               'geometry': geom_json_object,
               'properties': {}
              } 
   
    fid = feature.GetFID()
    if fid:
        output['id'] = fid
       
    for key in feature.keys():
        output['properties'][key] = feature.GetField(key)
   
    return output


def shapely_to_ogr_type(shapely_type):
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

    # object implementing geo_interface
    try:
        geo = thing.__geo_interface__
        return geo
    except AttributeError:
        pass

    # wkt
    try:
        shape = wkt.loads(thing)
        return shape.__geo_interface__
    except (ReadingError, TypeError):
        pass

    # geojson-like python mapping
    try:
        assert thing['type'] in ["Feature", "Point", "LineString", "Polygon", 
                                "MultiPoint", "MultiLineString", "MultiPolygon"]
        return thing
    except (AssertionError, TypeError):
        pass

    # geojson string
    try:
        maybe_geo = json.loads(thing)
        assert maybe_geo['type'] in ["Feature", "Point", "LineString", "Polygon", 
                       "MultiPoint", "MultiLineString", "MultiPolygon"]
        return maybe_geo
    except (ValueError, AssertionError):
        pass

    # wkb
    try:
        shape = wkb.loads(thing)
        return shape.__geo_interface__
    except (ReadingError, TypeError):
        pass

    raise RasterStatsError("Can't parse %s as a geo-like object" % thing)


def get_ogr_ds(vds):
    if not isinstance(vds, basestring):
        raise OGRError("OGR cannot open %r: not a string" % vds)

    ds = ogr.Open(vds)
    if not ds:
        raise OGRError("OGR cannot open %r" % vds)

    return ds


def ogr_records(vector, layer_num=0):  
    ds = get_ogr_ds(vector)
    layer = ds.GetLayer(layer_num)
    for i in range(layer.GetFeatureCount()):
        feature = layer.GetFeature(i)
        yield feature_to_geojson(feature)


def geo_records(vectors):
    for vector in vectors:
        yield parse_geo(vector)


def get_features(vectors, layer_num=0):
    if isinstance(vectors, basestring):
        try:
        # either an OGR layer ...
            get_ogr_ds(vectors)
            features_iter = ogr_records(vectors, layer_num)
            strategy = "ogr"
        except OGRError:
        # ... or a single string to be parsed as wkt/wkb/json
            feat = parse_geo(vectors)
            features_iter = [feat]
            strategy = "single_geo"
            gdal.ErrorReset()
    elif hasattr(vectors, '__geo_interface__'):
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

    return features_iter, strategy

