# -*- coding: utf-8 -*-
import json
from osgeo import ogr

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
    raise Exception("Unknown shapely_type %s" % shapely_type)