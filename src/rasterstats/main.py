# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import numpy as np
import warnings
from affine import Affine
from shapely.geometry import shape
from .io import read_features, Raster
from .utils import (rasterize_geom, get_percentile, check_stats,
                    remap_categories, key_assoc_val, boxify_points)


def raster_stats(*args, **kwargs):
    """Deprecated. Use zonal_stats instead."""
    warnings.warn("'raster_stats' is an alias to 'zonal_stats'"
                  " and will disappear in 1.0", DeprecationWarning)
    return zonal_stats(*args, **kwargs)


def zonal_stats(vectors,
                raster,
                layer=0,
                band=1,
                nodata=None,
                affine=None,
                stats=None,
                all_touched=False,
                categorical=False,
                category_map=None,
                add_stats=None,
                raster_out=False,
                prefix=None,
                geojson_out=False,
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

    band: int, optional
        If `raster` is a GDAL source, the band number to use (counting from 1).
        defaults to 1.

    nodata: float, optional
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

    add_stats: dict with names and functions of additional stats to compute, optional

    raster_out: Include the masked numpy array for each feature, optional
        Each feature dictionary will have the following additional keys:
        mini_raster_array: The clipped and masked numpy array
        mini_raster_affine: Affine transformation
        mini_raster_nodata: NoData Value

    prefix: add a prefix to the keys (default: None )

    geojson_out: Return list of geojson-like features (default: False)
        original feautur geometry and properties will be retained
        with zonal stats appended as additional properties.
        Use with `prefix` to ensure unique and meaningful property names.

    Returns
    -------
    list of dicts (if geojson_out is False)
        Each item corresponds to a single vector feature and
        contains keys for each of the specified stats.

    list of geojson features (if geojson_out is True)
        GeoJSON-like Feature as python dict
    """
    stats, run_count = check_stats(stats, categorical)

    # Handle 1.0 deprecations
    transform = kwargs.get('transform')
    if transform:
        warnings.warn("GDAL-style transforms will disappear in 1.0. "
                      "Use affine=Affine.from_gdal(*transform) instead",
                      DeprecationWarning)
        if not affine:
            affine = Affine.from_gdal(*transform)

    ndv = kwargs.get('nodata_value')
    if ndv:
        warnings.warn("Use `nodata` instead of `nodata_value`", DeprecationWarning)
        if not nodata:
            nodata = ndv

    cp = kwargs.get('copy_properties')
    if cp:
        warnings.warn("Use `geojson_out` to preserve feature properties",
                      DeprecationWarning)

    if band in ("all", "ALL", "*"):
        # TODO 
        band = [1, 2, 3]

    # arrays are zero offset
    if isinstance(band, int):
        band_iter = [band - 1]
    else:
        band_iter = [b - 1 for b in band]

    with Raster(raster, affine, nodata, band) as rast:
        results = []

        features_iter = read_features(vectors, layer)
        for i, feat in enumerate(features_iter):
            geom = shape(feat['geometry'])

            if 'Point' in geom.type:
                geom = boxify_points(geom, rast)

            geom_bounds = tuple(geom.bounds)

            fsrc = rast.read(bounds=geom_bounds)

            # create ndarray of rasterized geometry
            rv_array = rasterize_geom(geom, like=fsrc, all_touched=all_touched)

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
                feature_stats = dict((stat, None) for stat in stats)
                if 'count' in stats:  # special case, zero makes sense here
                    feature_stats['count'] = 0
            else:
                feature_stats = dict((stat, []) for stat in stats)

                for band in band_iter:
                    if len(masked.shape) == 3:
                        maskband = masked[band]
                    elif len(masked.shape) == 2:
                        maskband = masked

                    if run_count:
                        keys, counts = np.unique(maskband.compressed(), return_counts=True)
                        pixel_count = dict(zip([np.asscalar(k) for k in keys],
                                           [np.asscalar(c) for c in counts]))

                    if categorical:
                        if category_map:
                            category_stats = remap_categories(category_map, pixel_count)
                        else:
                            category_stats = pixel_count
                        feature_stats.update(category_stats)  # TODO this wipes prev bands

                    if 'min' in stats:
                        feature_stats['min'].append(float(maskband.min()))
                    if 'max' in stats:
                        feature_stats['max'].append(float(maskband.max()))
                    if 'mean' in stats:
                        feature_stats['mean'].append(float(maskband.mean()))
                    if 'count' in stats:
                        feature_stats['count'].append(int(maskband.count()))
                    # optional
                    if 'sum' in stats:
                        feature_stats['sum'].append(float(maskband.sum()))
                    if 'std' in stats:
                        feature_stats['std'].append(float(maskband.std()))
                    if 'median' in stats:
                        feature_stats['median'].append(float(np.median(maskband.compressed())))
                    if 'majority' in stats:
                        feature_stats['majority'].append(float(key_assoc_val(pixel_count, max)))
                    if 'minority' in stats:
                        feature_stats['minority'].append(float(key_assoc_val(pixel_count, min)))
                    if 'unique' in stats:
                        feature_stats['unique'].append(len(list(pixel_count.keys())))
                    if 'range' in stats:
                        rmin = float(maskband.min())
                        rmax = float(maskband.max())
                        feature_stats['range'].append(rmax - rmin)

                    for pctile in [s for s in stats if s.startswith('percentile_')]:
                        q = get_percentile(pctile)
                        pctarr = maskband.compressed()
                        feature_stats[pctile].append(np.percentile(pctarr, q))

                # Flatten if single band
                for k, v in feature_stats.items():
                    if isinstance(v, list) and len(v) == 1:
                        feature_stats[k] = v[0]

            if 'nodata' in stats:
                featmasked = np.ma.MaskedArray(fsrc.array, mask=np.logical_not(rv_array))
                nodata_count = float((featmasked == fsrc.nodata).sum())
                feature_stats['nodata'] = nodata_count

            if add_stats is not None:
                for stat_name, stat_func in add_stats.items():
                        feature_stats[stat_name] = stat_func(masked)



            if raster_out:
                feature_stats['mini_raster_array'] = masked
                feature_stats['mini_raster_affine'] = fsrc.affine
                feature_stats['mini_raster_nodata'] = fsrc.nodata

            if prefix is not None:
                prefixed_feature_stats = {}
                for key, val in feature_stats.items():
                    newkey = "{}{}".format(prefix, key)
                    prefixed_feature_stats[newkey] = val
                feature_stats = prefixed_feature_stats

            if geojson_out:
                for key, val in feature_stats.items():
                    if 'properties' not in feat:
                        feat['properties'] = {}
                    feat['properties'][key] = val
                results.append(feat)
            else:
                results.append(feature_stats)

    return results
