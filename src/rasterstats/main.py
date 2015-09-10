# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import numpy as np
import warnings
from shapely.geometry import shape, box, MultiPolygon
from .io import read_features, Raster
from .utils import (rasterize_geom, get_percentile, check_stats, remap_categories, key_assoc_val)


def raster_stats(*args, **kwargs):
    """Deprecated. Use zonal_stats instead."""
    warnings.warn("'raster_stats' is an alias to 'zonal_stats'"
                  " and will disappear in 1.0", DeprecationWarning)
    return zonal_stats(*args, **kwargs)


def zonal_stats(vectors, raster, layer=0, band_num=1, nodata_value=None,
                global_src_extent=False, categorical=False, stats=None,
                copy_properties=False, all_touched=False, affine=None,
                add_stats=None, raster_out=False, category_map=None, **kwargs):
    """Summary statistics of a raster, broken out by vector geometries.

    Attributes
    ----------
    vectors : path to an OGR vector source or list of geo_interface or WKT str
    raster : ndarray or path to a GDAL raster source
        If ndarray is passed, the `transform` kwarg is required.
    layer : int or string, optional
        If `vectors` is a path to an fiona source,
        specify the vector layer to use either by name or number.
        defaults to 0
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
        Use `True` if limited by disk IO or indexing into raster;
            requires sufficient RAM to store array in memory
        Use `False` with fast disks and a well-indexed raster, or when
        memory-constrained.
        Ignored when `raster` is an ndarray,
            because it is already completely in memory.
        defaults to `False`.
    categorical : bool, optional
    stats : list of str, or space-delimited str, optional
        Which statistics to calculate for each zone.
        All possible choices are listed in `utils.VALID_STATS`.
        defaults to `DEFAULT_STATS`, a subset of these.
    copy_properties : bool, optional
        Include feature properties alongside the returned stats.
        defaults to `False`
    all_touched : bool, optional
        Whether to include every raster cell touched by a geometry, or only
        those having a center point within the polygon.
        defaults to `False`
    affine : Affine object or 6 tuple in Affine order NOT GDAL order
        required only for ndarrays, otherwise it is read from src
    add_stats : Dictionary with names and functions of additional statistics to
                compute, optional
    raster_out : Include the masked numpy array for each feature, optional
        Each feature dictionary will have the following additional keys:
            clipped raster (`mini_raster`)
            Geo-transform (`mini_raster_GT`)
            No Data Value (`mini_raster_NDV`)
    category_map : A dictionary mapping raster values to human-readable categorical names
        Only applies when categorical is True

    Returns
    -------
    list of dicts
        Each dict represents one vector geometry.
        Its keys include `__fid__` (the geometry feature id)
        and each of the `stats` requested.
    """
    stats, run_count = check_stats(stats, categorical)

    with Raster(raster, affine, nodata_value, band_num) as rast:
        results = []

        features_iter = read_features(vectors, layer)
        for i, feat in enumerate(features_iter):
            geom = shape(feat['geometry'])

            # Point and MultiPoint don't play well with GDALRasterize
            # convert them into box polygons the size of a raster cell
            # TODO warning, suggest point_query instead
            # TODO buff = rgt[1] / 2.0
            buff = rast.affine.a / 2.0  # TODO use affine not transform
            if geom.type == "MultiPoint":
                geom = MultiPolygon([box(*(pt.buffer(buff).bounds))
                                    for pt in geom.geoms])
            elif geom.type == 'Point':
                geom = box(*(geom.buffer(buff).bounds))

            geom_bounds = tuple(geom.bounds)

            # TODO if off the map, return array with all nodata and let the
            # masked.compressed.size() check handle it
            fsrc = rast.read(bounds=geom_bounds)

            # create ndarray of rasterized geometry
            rv_array = rasterize_geom(geom, like=fsrc, all_touched=all_touched)
            assert rv_array.shape == fsrc.shape  # TODO remove

            # Mask the source data array with our current feature
            # we take the logical_not to flip 0<->1 for the correct mask effect
            # we also mask out nodata values explicitly
            masked = np.ma.MaskedArray(
                fsrc.array,
                mask=np.logical_or(
                    fsrc.array == nodata_value,
                    np.logical_not(rv_array)))

            if masked.compressed().size == 0:
                # nothing here, fill with None and move on
                feature_stats = dict([(stat, None) for stat in stats])
                if 'count' in stats:  # special case, zero makes sense here
                    feature_stats['count'] = 0
            else:
                if run_count:
                    keys, counts = np.unique(masked.compressed(), return_counts=True)
                    pixel_count = dict(zip([np.asscalar(k) for k in keys],
                                       [np.asscalar(c) for c in counts]))

                if categorical:
                    feature_stats = dict(pixel_count)
                    if category_map:
                        feature_stats = remap_categories(category_map, feature_stats)
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
                        feature_stats['majority'] = float(key_assoc_val(pixel_count, max))
                    except IndexError:
                        feature_stats['majority'] = None
                if 'minority' in stats:
                    try:
                        feature_stats['minority'] = float(key_assoc_val(pixel_count, min))
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

                for pctile in [s for s in stats if s.startswith('percentile_')]:
                    q = get_percentile(pctile)
                    pctarr = masked.compressed()
                    if pctarr.size == 0:
                        feature_stats[pctile] = None
                    else:
                        feature_stats[pctile] = np.percentile(pctarr, q)

            if 'nodata' in stats:
                featmasked = np.ma.MaskedArray(fsrc.array, mask=np.logical_not(rv_array))
                keys, counts = np.unique(featmasked.compressed(), return_counts=True)
                pixel_count = dict(zip([np.asscalar(k) for k in keys],
                                   [np.asscalar(c) for c in counts]))
                feature_stats['nodata'] = pixel_count.get(nodata_value, 0)

            if add_stats is not None:
                for stat_name, stat_func in add_stats.items():
                        feature_stats[stat_name] = stat_func(masked)

            if raster_out:
                masked.fill_value = nodata_value
                masked.data[masked.mask] = nodata_value
                feature_stats['mini_raster'] = masked
                feature_stats['mini_raster_GT'] = fsrc.transform  # TODO affine
                feature_stats['mini_raster_NDV'] = rast.nodata

            if 'fid' in feat:
                # Use the fid directly,
                # likely came from OGR data via .utils.feature_to_geojson
                feature_stats['__fid__'] = feat['fid']
            else:
                # Use the enumerated id
                feature_stats['__fid__'] = i

            if 'properties' in feat and copy_properties:
                for key, val in list(feat['properties'].items()):
                    feature_stats[key] = val

            results.append(feature_stats)

    return results
