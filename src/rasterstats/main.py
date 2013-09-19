# -*- coding: utf-8 -*-
from shapely.geometry import mapping, shape
import numpy as np
import json
from osgeo import gdal, ogr
from osgeo.gdalconst import GA_ReadOnly
from .utils import bbox_to_pixel_offsets, feature_to_geojson, shapely_to_ogr_type
ogr.UseExceptions()


class RasterStatsError(Exception):
    pass


class OGRError(Exception):
    pass


def get_ogr_ds(vds):
    if not isinstance(vds, basestring):
        raise OGRError("OGR cannot open %r: not a string" % vds)

    try:
        ds = ogr.Open(vds)
    except:
        raise OGRError("OGR cannot open %r" % vds)

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
        yield vector.__geo_interface__


def raster_stats(vectors, raster, layer_num=0, band_num=1, nodata_value=None, 
                 global_src_extent=False, categorical=False):

    rds = gdal.Open(raster, GA_ReadOnly)
    assert(rds)
    rb = rds.GetRasterBand(band_num)
    rgt = rds.GetGeoTransform()

    if nodata_value is not None:
        nodata_value = float(nodata_value)
        rb.SetNoDataValue(nodata_value)

    try:
        # are we dealing with an ogr path?
        get_ogr_ds(vectors)
        features_iter = ogr_records(vectors, layer_num)
        strategy = "ogr"
    except OGRError:
        # treat vectors as an iterable of objects with a __geo_interface__ 
        features_iter = geo_records(vectors)
        strategy = "iter_geo"
        gdal.ErrorReset()
        # TODO single geo)interface
        # TODO multi and single wkt/wkb

    # create an in-memory numpy array of the source raster data
    # covering the whole extent of the vector layer
    if global_src_extent:

        # find extent of ALL features
        if strategy != "ogr":
            raise RasterStatsError("global_src_extent is only supported for OGR vector layers")

        ds = ogr.Open(vectors)
        layer = ds.GetLayer(layer_num)
        ex = layer.GetExtent()
        # transform from OGR extent to xmin, xmax, ymin, ymax
        layer_extent = (ex[0], ex[2], ex[1], ex[3])

        # use global source extent
        # useful only when disk IO or raster scanning inefficiencies are your limiting factor
        # advantage: reads raster data in one pass
        # disadvantage: large vector extents may have big memory requirements
        src_offset = bbox_to_pixel_offsets(rgt, layer_extent)
        src_array = rb.ReadAsArray(*src_offset)

        # calculate new geotransform of the layer subset
        new_gt = (
            (rgt[0] + (src_offset[0] * rgt[1])),
            rgt[1],
            0.0,
            (rgt[3] + (src_offset[1] * rgt[5])),
            0.0,
            rgt[5]
        )

    mem_drv = ogr.GetDriverByName('Memory')
    driver = gdal.GetDriverByName('MEM')

    stats = []

    # Loop through geometries

    for feat in features_iter:
        # Load shapely geom from __geo_interface__
        if feat['type'] == "Feature":
            geom = shape(feat['geometry'])
        else:  # it's just a geometry
            geom = shape(feat)
        ogr_geom_type = shapely_to_ogr_type(geom.type)

        if not global_src_extent:
            # use local source extent
            # fastest option when you have fast disks and well indexed raster (ie tiled Geotiff)
            # advantage: each feature uses the smallest raster chunk
            # disadvantage: lots of reads on the source raster
            src_offset = bbox_to_pixel_offsets(rgt, geom.bounds)
            src_array = rb.ReadAsArray(*src_offset)

            # calculate new geotransform of the feature subset
            new_gt = (
                (rgt[0] + (src_offset[0] * rgt[1])),
                rgt[1],
                0.0,
                (rgt[3] + (src_offset[1] * rgt[5])),
                0.0,
                rgt[5]
            )

        # Create a temporary vector layer in memory
        mem_ds = mem_drv.CreateDataSource('out')
        #mem_layer = mem_ds.CreateLayer('poly', None, ogr.wkbPolygon)
        mem_layer = mem_ds.CreateLayer('mem_ds', None, ogr_geom_type)
        ogr_feature = ogr.Feature(feature_def=mem_layer.GetLayerDefn())
        ogr_geom = ogr.CreateGeometryFromWkb(geom.wkb)
        ogr_feature.SetGeometryDirectly(ogr_geom)
        mem_layer.CreateFeature(ogr_feature)

        # Rasterize it
        rvds = driver.Create('', src_offset[2], src_offset[3], 1, gdal.GDT_Byte)
        rvds.SetGeoTransform(new_gt)

        gdal.RasterizeLayer(rvds, [1], mem_layer, burn_values=[1])
        rv_array = rvds.ReadAsArray()

        # Mask the source data array with our current feature
        # we take the logical_not to flip 0<->1 to get the correct mask effect
        # we also mask out nodata values explictly
        masked = np.ma.MaskedArray(
            src_array,
            mask=np.logical_or(
                src_array == nodata_value,
                np.logical_not(rv_array)
            )
        )

        feature_stats = {}
        if categorical:
            from collections import Counter
            feature_stats = dict(Counter(masked.flatten()))
        else:
            # Continuous variable, 1 dict per feature
            feature_stats = {
                'min': float(masked.min()),
                'mean': float(masked.mean()),
                'max': float(masked.max()),
                'std': float(masked.std()),
                'sum': float(masked.sum()),
                'count': int(masked.count()),
            }

        if feat.has_key('properties'):  # if it's an actual feature, not geometry
            for key, val in feat['properties'].items():
                feature_stats[key] = val

        stats.append(feature_stats)

    return stats
