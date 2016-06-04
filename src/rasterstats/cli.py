# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import logging

try:
    import simplejson as json
except:
    import json

import click
import cligj

from rasterstats import gen_zonal_stats, gen_point_query
from rasterstats._version import __version__ as version

SETTINGS = dict(help_option_names=['-h', '--help'])

@click.command(context_settings=SETTINGS)
@cligj.features_in_arg
@click.version_option(version=version, message='%(version)s')
@click.option('--raster', '-r', required=True)
@click.option('--all-touched/--no-all-touched', default=False)
@click.option('--band', type=int, default=1)
@click.option('--categorical/--no-categorical', default=False)
@click.option('--indent', type=int, default=None)
@click.option('--info/--no-info', default=False)
@click.option('--nodata', type=int, default=None)
@click.option('--prefix', type=str, default='_')
@click.option('--stats', type=str, default=None)
@cligj.sequence_opt
@cligj.use_rs_opt
def zonalstats(features, raster, all_touched, band, categorical,
               indent, info, nodata, prefix, stats, sequence, use_rs):
    '''zonalstats generates summary statistics of geospatial raster datasets
    based on vector features.

    The input arguments to zonalstats should be valid GeoJSON Features. (see cligj)

    The output GeoJSON will be mostly unchanged but have additional properties per feature
    describing the summary statistics (min, max, mean, etc.) of the underlying raster dataset.

    The raster is specified by the required -r/--raster argument.

    Example, calculate rainfall stats for each state and output to file:

    \b
       rio zonalstats states.geojson -r rainfall.tif > mean_rainfall_by_state.geojson
    '''

    if info:
        logging.basicConfig(level=logging.INFO)

    if stats is not None:
        stats = stats.split(" ")
        if 'all' in [x.lower() for x in stats]:
            stats = "ALL"

    zonal_results = gen_zonal_stats(
        features,
        raster,
        all_touched=all_touched,
        band=band,
        categorical=categorical,
        nodata=nodata,
        stats=stats,
        prefix=prefix,
        geojson_out=True)

    if sequence:
        for feature in zonal_results:
            if use_rs:
                click.echo(b'\x1e', nl=False)
            click.echo(json.dumps(feature))
    else:
        click.echo(json.dumps(
            {'type': 'FeatureCollection',
             'features': list(zonal_results)}))


@click.command(context_settings=SETTINGS)
@cligj.features_in_arg
@click.version_option(version=version, message='%(version)s')
@click.option('--raster', '-r', required=True)
@click.option('--band', type=int, default=1)
@click.option('--nodata', type=int, default=None)
@click.option('--indent', type=int, default=None)
@click.option('--interpolate', type=str, default='bilinear')
@click.option('--property-name', type=str, default='value')
@cligj.sequence_opt
@cligj.use_rs_opt
def pointquery(features, raster, band, indent, nodata,
               interpolate, property_name, sequence, use_rs):
    """
    Queries the raster values at the points of the input GeoJSON Features.
    The raster values are added to the features properties and output as GeoJSON
    Feature Collection.

    If the Features are Points, the point geometery is used.
    For other Feauture types, all of the verticies of the geometry will be queried.
    For example, you can provide a linestring and get the profile along the line
    if the verticies are spaced properly.

    You can use either bilinear (default) or nearest neighbor interpolation.
    """

    results = gen_point_query(
        features,
        raster,
        band=band,
        nodata=nodata,
        interpolate=interpolate,
        property_name=property_name,
        geojson_out=True)

    if sequence:
        for feature in results:
            if use_rs:
                click.echo(b'\x1e', nl=False)
            click.echo(json.dumps(feature))
    else:
        click.echo(json.dumps(
            {'type': 'FeatureCollection',
             'features': list(results)}))
