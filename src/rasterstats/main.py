# -*- coding: utf-8 -*-
from shapely.geometry import shape, box, MultiPolygon
import numpy as np
from osgeo import gdal, ogr
from osgeo.gdalconst import GA_ReadOnly
from .utils import bbox_to_pixel_offsets, shapely_to_ogr_type, get_features, \
                   RasterStatsError

ogr.UseExceptions()


def raster_stats(vectors, raster, layer_num=0, band_num=1, nodata_value=None, 
                 global_src_extent=False, categorical=False):

    rds = gdal.Open(raster, GA_ReadOnly)
    assert(rds)
    rb = rds.GetRasterBand(band_num)
    rgt = rds.GetGeoTransform()

    if nodata_value is not None:
        nodata_value = float(nodata_value)
        rb.SetNoDataValue(nodata_value)

    features_iter, strategy = get_features(vectors, layer_num)

    # create an in-memory numpy array of the source raster data
    # covering the whole extent of the vector layer
    if global_src_extent:

        # find extent of ALL features
        if strategy != "ogr":
            raise RasterStatsError("global_src_extent requires OGR vector")

        ds = ogr.Open(vectors)
        layer = ds.GetLayer(layer_num)
        ex = layer.GetExtent()
        # transform from OGR extent to xmin, xmax, ymin, ymax
        layer_extent = (ex[0], ex[2], ex[1], ex[3])

        # use global source extent
        # useful only when disk IO or raster scanning 
        #   inefficiencies are your limiting factor
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

    for feat in features_iter:
        if feat['type'] == "Feature":
            geom = shape(feat['geometry'])
        else:  # it's just a geometry
            geom = shape(feat)

        # Point and MultiPoint don't play well with GDALRasterize
        # convert them into box polygons the size of a raster cell
        buff = rgt[1] / 2.0
        if geom.type == "MultiPoint":
            geom = MultiPolygon([box(*(pt.buffer(buff).bounds)) 
                                for pt in geom.geoms])
        elif geom.type == 'Point':
            geom = box(*(geom.buffer(buff).bounds))

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

        rasterize_opts = {}
        # if geom.type == "MultiPoint":
        #     rasterize_opts = {'options': ['ALL_TOUCHED=TRUE']}

        gdal.RasterizeLayer(rvds, [1], mem_layer, burn_values=[1], **rasterize_opts)
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

        if feat.has_key('properties'):  # if it's a feature, not geometry
            for key, val in feat['properties'].items():
                feature_stats[key] = val

        stats.append(feature_stats)

    return stats
