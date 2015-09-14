# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import numpy as np
import warnings
from affine import Affine
from shapely.geometry import shape, box, MultiPolygon
from .io import read_features, Raster
from .utils import (rasterize_geom, get_percentile, check_stats, remap_categories, key_assoc_val)


def raster_stats(*args, **kwargs):
    """Deprecated. Use zonal_stats instead."""
    warnings.warn("'raster_stats' is an alias to 'zonal_stats'"
                  " and will disappear in 1.0", DeprecationWarning)
    return zonal_stats(*args, **kwargs)


def zonal_stats(vectors,
                raster,
                layer=0,
                band_num=1,
                nodata_value=None,
                affine=None,
                stats=None,
                all_touched=False,
                categorical=False,
                category_map=None,
                copy_properties=False,
                add_stats=None,
                raster_out=False,
                **kwargs):
    """Zonal statistics of raster values aggregated to vector geometries.

    Parameters
    ----------
    vectors: path to an vector source or geo-like python objects

    raster: ndarray or path to a GDAL raster source
        If ndarray is passed, the `transform` kwarg is required.

    layer: int or string, optional
        If `vectors` is a path to an fiona source,
        specify the vector layer to use either by name or number.
        defaults to 0

    band_num: int, optional
        If `raster` is a GDAL source, the band number to use (counting from 1).
        defaults to 1.

    nodata_value: float, optional
        If `raster` is a GDAL source, this value overrides any NODATA value
        specified in the file's metadata.
        If `None`, the file's metadata's NODATA value (if any) will be used.
        defaults to `None`.

    affine: Affine object or 6 tuple in Affine order NOT GDAL order
        required only for ndarrays, otherwise it is read from src

    stats:  list of str, or space-delimited str, optional
        Which statistics to calculate for each zone.
        All possible choices are listed in `utils.VALID_STATS`.
        defaults to `DEFAULT_STATS`, a subset of these.

    all_touched: bool, optional
        Whether to include every raster cell touched by a geometry, or only
        those having a center point within the polygon.
        defaults to `False`

    categorical: bool, optional

    category_map: A dictionary mapping raster values to human-readable categorical names
        Only applies when categorical is True

    copy_properties: bool, optional
        Include feature properties alongside the returned stats.
        defaults to `False`

    add_stats: dict with names and functions of additional stats to compute, optional

    raster_out: Include the masked numpy array for each feature, optional
        Each feature dictionary will have the following additional keys:
        mini_raster: The clipped and masked numpy array
        mini_raster_affine: Affine transformation
        mini_raster_nodata: NoData Value

    Returns
    -------
    list of dicts
        Each item corresponds to a single vector feature and
        contains keys for each of the specified stats.
    """
    stats, run_count = check_stats(stats, categorical)

    transform = kwargs.get('transform')
    if transform:
        warnings.warn("GDAL-style transforms will disappear in 1.0. "
                      "Use affine=Affine.from_gdal(*transform) instead",
                      DeprecationWarning)
        if not affine:
            affine = Affine.from_gdal(*transform)

    with Raster(raster, affine, nodata_value, band_num) as rast:
        results = []

        features_iter = read_features(vectors, layer)
        for i, feat in enumerate(features_iter):
            geom = shape(feat['geometry'])

            # Point and MultiPoint don't play well with GDALRasterize
            # convert them into box polygons the size of a raster cell
            # TODO warning, suggest point_query instead
            buff = rast.affine.a / 2.0
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
                    fsrc.array == fsrc.nodata,
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
                    feature_stats['majority'] = float(key_assoc_val(pixel_count, max))
                if 'minority' in stats:
                    feature_stats['minority'] = float(key_assoc_val(pixel_count, min))
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
                    feature_stats[pctile] = np.percentile(pctarr, q)

            if 'nodata' in stats:
                featmasked = np.ma.MaskedArray(fsrc.array, mask=np.logical_not(rv_array))
                keys, counts = np.unique(featmasked.compressed(), return_counts=True)
                pixel_count = dict(zip([np.asscalar(k) for k in keys],
                                       [np.asscalar(c) for c in counts]))
                feature_stats['nodata'] = pixel_count.get(fsrc.nodata, 0)

            if add_stats is not None:
                for stat_name, stat_func in add_stats.items():
                        feature_stats[stat_name] = stat_func(masked)

            if raster_out:
                feature_stats['mini_raster'] = masked
                feature_stats['mini_raster_affine'] = fsrc.affine
                feature_stats['mini_raster_nodata'] = fsrc.nodata

            if 'id' in feat:
                # Use the feature id directly
                feature_stats['__fid__'] = feat['id']
            else:
                # Use the enumerated id
                feature_stats['__fid__'] = i

            if 'properties' in feat and copy_properties:
                for key, val in list(feat['properties'].items()):
                    feature_stats[key] = val

            results.append(feature_stats)

    return results
