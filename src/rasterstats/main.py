# -*- coding: utf-8 -*-
import sys
from shapely.geometry import shape, box, MultiPolygon
import numpy as np
from collections import Counter
from osgeo import gdal, ogr
from osgeo.gdalconst import GA_ReadOnly
from .utils import bbox_to_pixel_offsets, shapely_to_ogr_type, get_features, \
                   RasterStatsError, raster_extent_as_bounds
import warnings

try:
    import georasters as gr
    opt_georaster = True
except:
    opt_georaster = False

try:
    if ogr.GetUseExceptions() != 1:
        ogr.UseExceptions()
except(AttributeError):
    warnings.warn(
        "This version of GDAL/OGR does not support python Exceptions",
        Warning
    )

DEFAULT_STATS = ['count', 'min', 'max', 'mean']
VALID_STATS = DEFAULT_STATS + \
    ['sum', 'std', 'median', 'majority', 'minority', 'unique', 'range']


def raster_stats(*args, **kwargs):
    """Deprecated. Use zonal_stats instead."""
    warnings.warn(
        "'raster_stats' is an alias to 'zonal_stats' and will disappear in 1.0",
        DeprecationWarning
    )
    return zonal_stats(*args, **kwargs)


def zonal_stats(vectors, raster, layer_num=0, band_num=1, nodata_value=None, 
                 global_src_extent=False, categorical=False, stats=None, 
                 copy_properties=False, all_touched=False, transform=None,
                 add_stats=None, raster_out=False, opt_georaster=opt_georaster):
    """Summary statistics of a raster, broken out by vector geometries.

    Attributes
    ----------
    vectors : path to an OGR vector source, or list of geo_interface, or WKT str
    raster : ndarray or path to a GDAL raster source
        If ndarray is passed, the `transform` kwarg is required.
    layer_num : int, optional
        If `vectors` is a path to an OGR source, the vector layer to use
        (counting from 0).
        defaults to 0.
    band_num : int, optional
        If `raster` is a GDAL source, the band number to use (counting from 1).
        defaults to 1.
    nodata_value : float, optional
        If `raster` is a GDAL source, this value overrides any NODATA value
        specified in the file's metadata.
        If `None`, the file's metadata's NODATA value (if any) will be used.
        `ndarray`s don't support `nodata_value`.
        defaults to `None`.
    global_src_extent : bool, optional
        Pre-allocate entire raster before iterating over vector features.
        Use `True` if limited by disk IO or indexing into raster; can hog memory.
        Use `False` with fast disks and a well-indexed raster, or when
        memory-constrained.
        Ignored when `raster` is an ndarray, because it is already completely in
        memory.
        defaults to `False`.
    categorical : bool, optional
    stats : list of str, or space-delimited str, optional
        Which statistics to calculate for each zone.
        All possible choices are listed in `VALID_STATS`.
        defaults to `DEFAULT_STATS`, a subset of these.
    copy_properties : bool, optional
        Include feature properties alongside the returned stats.
        defaults to `False`
    all_touched : bool, optional
        Whether to include every raster cell touched by a geometry, or only
        those having a center point within the polygon.
        defaults to `False`
    transform : list of float, optional
        GDAL-style geotransform coordinates when `raster` is an ndarray.
        Required when `raster` is an ndarray, otherwise ignored.
    add_stats : Dictionary with names and functions of additional statistics to compute, optional
    mini_raster : Output the clipped raster for each geometry, optional
        Returns additionally: 
            clipped raster (mini_raster)
            Geo-transform (mini_raster_GT)
            No Data Value (mini_raster_NDV)

    Returns
    -------
    list of dicts
        Each dict represents one vector geometry.
        Its keys include `__fid__` (the geometry feature id)
        and each of the `stats` requested.
    """

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
        if x not in VALID_STATS:
            raise RasterStatsError("Stat `%s` not valid;" \
                " must be one of \n %r" % (x, VALID_STATS))

    run_count = False
    if categorical or 'majority' in stats or 'minority' in stats or \
       'unique' in stats:
        # run the counter once, only if needed
        run_count = True

    if isinstance(raster, np.ndarray):
        raster_type = 'ndarray'

        # must have transform arg
        if not transform:
            raise RasterStatsError("Must provide the 'transform' kwarg when "\
                "using ndarrays as src raster")
        rgt = transform
        rsize = (raster.shape[1], raster.shape[0])

        # global_src_extent is implicitly turned on, array is already in memory
        if not global_src_extent:
            global_src_extent = True

        if nodata_value:
            raise NotImplementedError("ndarrays don't support 'nodata_value'")

    else:
        raster_type = 'gdal'
        rds = gdal.Open(raster, GA_ReadOnly)
        if not rds:
            raise RasterStatsError("Cannot open %r as GDAL raster" % raster)
        rb = rds.GetRasterBand(band_num)
        rgt = rds.GetGeoTransform()
        rsize = (rds.RasterXSize, rds.RasterYSize)

        if nodata_value is not None:
            nodata_value = float(nodata_value)
            rb.SetNoDataValue(nodata_value)
        else:
            nodata_value = rb.GetNoDataValue()

    rbounds = raster_extent_as_bounds(rgt, rsize)

    features_iter, strategy, spatial_ref = get_features(vectors, layer_num)

    if global_src_extent and raster_type == 'gdal':
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

        global_src_offset = bbox_to_pixel_offsets(rgt, layer_extent, rsize)
        global_src_array = rb.ReadAsArray(*global_src_offset)
    elif global_src_extent and raster_type == 'ndarray':
        global_src_offset = (0, 0, raster.shape[0], raster.shape[1])
        global_src_array = raster

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

        geom_bounds = list(geom.bounds)

        # calculate new pixel coordinates of the feature subset
        src_offset = bbox_to_pixel_offsets(rgt, geom_bounds, rsize)

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
                feature_stats['unique'] = len(list(pixel_count.keys()))
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
            if add_stats is not None:
                for stat_name, stat_func in add_stats.items():
                        feature_stats[stat_name] = stat_func(masked)
            if raster_out:
                masked.fill_value=nodata_value
                masked.data[masked.mask]=nodata_value
                if opt_georaster:
                    feature_stats['mini_raster'] = gr.GeoRaster(masked, new_gt, nodata_value=nodata_value, projection=spatial_ref) 
                else:
                    feature_stats['mini_raster'] = masked
                    feature_stats['mini_raster_GT'] = new_gt
                    feature_stats['mini_raster_NDV'] = nodata_value
        
        # Use the enumerated id as __fid__
        feature_stats['__fid__'] = i

        if 'properties' in feat and copy_properties:
            for key, val in list(feat['properties'].items()):
                feature_stats[key] = val

        results.append(feature_stats)

    return results

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

    csvwriter = csv.DictWriter(csv_fh, delimiter=',', fieldnames=fieldnames)
    csvwriter.writerow(dict((fn,fn) for fn in fieldnames))
    for row in stats:
        csvwriter.writerow(row)
    contents = csv_fh.getvalue()
    csv_fh.close()
    return contents

