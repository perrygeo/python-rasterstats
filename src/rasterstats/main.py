# -*- coding: utf-8 -*-
from shapely.geometry import shape, box, MultiPolygon
import numpy as np
from collections import Counter
from osgeo import gdal, ogr
from osgeo.gdalconst import GA_ReadOnly
from .utils import bbox_to_pixel_offsets, shapely_to_ogr_type, get_features, \
                   RasterStatsError, raster_extent_as_bounds


if ogr.GetUseExceptions() != 1:
    ogr.UseExceptions()


DEFAULT_STATS = ['count', 'min', 'max', 'mean']
VALID_STATS = DEFAULT_STATS + \
    ['sum', 'std', 'median', 'majority', 'minority', 'unique', 'range']

def raster_stats(vectors, raster, layer_num=0, band_num=1, nodata_value=None, 
                 global_src_extent=False, categorical=False, stats=None, 
                 copy_properties=False, all_touched=False):

    if not stats:
        if not categorical:
            stats = DEFAULT_STATS
        else:
            stats = []
    else:
        if isinstance(stats, basestring):
            if stats in ['*', 'ALL']:
                stats = VALID_STATS
            else:
                stats = stats.split()
    for x in stats:
        if x not in VALID_STATS:
            raise RasterStatsError("Stat `%s` not valid;" \
                " must be one of \n %r" % (x, VALID_STATS))

    run_count = False
    if categorical or 'majority' in stats or 'minority' in stats or \
       'unique' in stats:
        # run the counter once, only if needed
        run_count = True

    rds = gdal.Open(raster, GA_ReadOnly)
    if not rds:
        raise RasterStatsError("Cannot open %r as GDAL raster" % raster)
    rb = rds.GetRasterBand(band_num)
    rgt = rds.GetGeoTransform()
    rsize = (rds.RasterXSize, rds.RasterYSize)
    rbounds = raster_extent_as_bounds(rgt, rsize)

    if nodata_value is not None:
        nodata_value = float(nodata_value)
        rb.SetNoDataValue(nodata_value)
    else:
        nodata_value = rb.GetNoDataValue()

    features_iter, strategy, spatial_ref = get_features(vectors, layer_num)

    if global_src_extent:
        # create an in-memory numpy array of the source raster data
        # covering the whole extent of the vector layer
        if strategy != "ogr":
            raise RasterStatsError("global_src_extent requires OGR vector")

        # find extent of ALL features
        ds = ogr.Open(vectors)
        layer = ds.GetLayer(layer_num)
        ex = layer.GetExtent()
        # transform from OGR extent to xmin, ymin, xmax, ymax
        layer_extent = (ex[0], ex[2], ex[1], ex[3])

        global_src_offset = bbox_to_pixel_offsets(rgt, layer_extent)
        global_src_array = rb.ReadAsArray(*global_src_offset)

    mem_drv = ogr.GetDriverByName('Memory')
    driver = gdal.GetDriverByName('MEM')

    results = []

    for i, feat in enumerate(features_iter):
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

        # "Clip" the geometry bounds to the overall raster bounding box
        # This should avoid any rasterIO errors for partially overlapping polys
        geom_bounds = list(geom.bounds)
        if geom_bounds[0] < rbounds[0]:
            geom_bounds[0] = rbounds[0]
        if geom_bounds[1] < rbounds[1]:
            geom_bounds[1] = rbounds[1]
        if geom_bounds[2] > rbounds[2]:
            geom_bounds[2] = rbounds[2]
        if geom_bounds[3] > rbounds[3]:
            geom_bounds[3] = rbounds[3]

        # calculate new geotransform of the feature subset
        src_offset = bbox_to_pixel_offsets(rgt, geom_bounds)

        new_gt = (
            (rgt[0] + (src_offset[0] * rgt[1])),
            rgt[1],
            0.0,
            (rgt[3] + (src_offset[1] * rgt[5])),
            0.0,
            rgt[5]
        )

        if src_offset[2] <= 0 or src_offset[3] <= 0:
            # we're off the raster completely, no overlap at all
            # so there's no need to even bother trying to calculate
            feature_stats = dict([(s, None) for s in stats])
        else:
            if not global_src_extent:
                # use feature's source extent and read directly from source
                # fastest option when you have fast disks and well-indexed raster
                # advantage: each feature uses the smallest raster chunk
                # disadvantage: lots of disk reads on the source raster
                src_array = rb.ReadAsArray(*src_offset)
            else:
                # derive array from global source extent array
                # useful *only* when disk IO or raster format inefficiencies are your limiting factor
                # advantage: reads raster data in one pass before loop
                # disadvantage: large vector extents combined with big rasters need lotsa memory
                xa = src_offset[0] - global_src_offset[0]
                ya = src_offset[1] - global_src_offset[1]
                xb = xa + src_offset[2]
                yb = ya + src_offset[3]
                src_array = global_src_array[ya:yb, xa:xb]

            # Create a temporary vector layer in memory
            mem_ds = mem_drv.CreateDataSource('out')
            mem_layer = mem_ds.CreateLayer('out', spatial_ref, ogr_geom_type)
            ogr_feature = ogr.Feature(feature_def=mem_layer.GetLayerDefn())
            ogr_geom = ogr.CreateGeometryFromWkt(geom.wkt)
            ogr_feature.SetGeometryDirectly(ogr_geom)
            mem_layer.CreateFeature(ogr_feature)

            # Rasterize it
            rvds = driver.Create('rvds', src_offset[2], src_offset[3], 1, gdal.GDT_Byte)
            rvds.SetGeoTransform(new_gt)
            
            if all_touched:
                gdal.RasterizeLayer(rvds, [1], mem_layer, None, None, burn_values=[1], options = ['ALL_TOUCHED=True'])
            else:
                gdal.RasterizeLayer(rvds, [1], mem_layer, None, None, burn_values=[1], options = ['ALL_TOUCHED=False'])
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

            if run_count:
                pixel_count = Counter(masked.compressed())

            if categorical:  
                feature_stats = dict(pixel_count)
            else:
                feature_stats = {}

            if 'min' in stats:
                feature_stats['min'] = float(masked.min())
            if 'max' in stats:
                feature_stats['max'] = float(masked.max())
            if 'mean' in stats:
                feature_stats['mean'] = float(masked.mean())
            if 'count' in stats:
                feature_stats['count'] = int(masked.count())
            # optional
            if 'sum' in stats:
                feature_stats['sum'] = float(masked.sum())
            if 'std' in stats:
                feature_stats['std'] = float(masked.std())
            if 'median' in stats:
                feature_stats['median'] = float(np.median(masked.compressed()))
            if 'majority' in stats:
                try:
                    feature_stats['majority'] = pixel_count.most_common(1)[0][0]
                except IndexError:
                    feature_stats['majority'] = None
            if 'minority' in stats:
                try:
                    feature_stats['minority'] = pixel_count.most_common()[-1][0]
                except IndexError:
                    feature_stats['minority'] = None
            if 'unique' in stats:
                feature_stats['unique'] = len(pixel_count.keys())
            if 'range' in stats:
                try:
                    rmin = feature_stats['min']
                except KeyError:
                    rmin = float(masked.min())
                try:
                    rmax = feature_stats['max']
                except KeyError:
                    rmax = float(masked.max())
                feature_stats['range'] = rmax - rmin
        
        try:
            # Use the provided feature id as __fid__
            feature_stats['__fid__'] = feat['id']
        except KeyError:
            # use the enumerator
            feature_stats['__fid__'] = i 

        if feat.has_key('properties') and copy_properties:
            for key, val in feat['properties'].items():
                feature_stats[key] = val

        results.append(feature_stats)

    return results

def stats_to_csv(stats):
    from cStringIO import StringIO
    import csv

    csv_fh = StringIO()

    keys = set()
    for stat in stats:
        for key in stat.keys():
            keys.add(key)

    fieldnames = sorted(list(keys))

    csvwriter = csv.DictWriter(csv_fh, delimiter=',', fieldnames=fieldnames)
    csvwriter.writerow(dict((fn,fn) for fn in fieldnames))
    for row in stats:
        csvwriter.writerow(row)
    contents = csv_fh.getvalue()
    csv_fh.close()
    return contents

