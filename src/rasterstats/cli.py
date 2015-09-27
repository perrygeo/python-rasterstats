# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import click
from rasterstats import zonal_stats, point_query
from rasterstats.io import read_features
import logging
try:
    import simplejson as json
except:
    import json

SETTINGS = dict(help_option_names=['-h', '--help'])
version = 0.9


@click.command(context_settings=SETTINGS)
@click.argument('input-geojson', type=click.File('r'), default='-')
@click.argument('output-geojson', type=click.File('w'), default='-')
@click.version_option(version=version, message='%(version)s')
@click.option('--raster', '-r', required=True, type=click.Path(exists=True))
@click.option('--all-touched/--no-all-touched', default=False)
@click.option('--band', type=int, default=1)
@click.option('--categorical/--no-categorical', default=False)
@click.option('--indent', type=int, default=None)
@click.option('--info/--no-info', default=False)
@click.option('--nodata', type=int, default=None)
@click.option('--prefix', type=str, default='_')
@click.option('--stats', type=str, default=None)
def zonalstats(input_geojson, raster, output_geojson, all_touched, band, categorical,
               indent, info, nodata, prefix, stats):
    '''zonalstats generates summary statistics of geospatial raster datasets
    based on vector features.

    The input and output arguments of zonalstats should be valid GeoJSON FeatureCollections. The output GeoJSON will be mostly unchanged but have additional properties per feature describing the summary statistics (min, max, mean, etc.) of the underlying raster dataset. The input and output arguments default to stdin and stdout but can also be file paths.

    The raster is specified by the required -r/--raster argument.

    Example, calculate rainfall stats for each state and output to file:

    \b
    zonalstats states.geojson -r rainfall.tif > mean_rainfall_by_state.geojson
    '''

    if info:
        logging.basicConfig(level=logging.INFO)
    mapping = json.loads(input_geojson.read())
    input_geojson.close()
    try:
        if mapping['type'] == "FeatureCollection":
            feature_collection = mapping
        else:
            feature_collection = {'type': 'FeatureCollection'}
        features = read_features(mapping)
    except (AssertionError, KeyError):
        raise ValueError("input_geojson must be valid GeoJSON")

    if stats is not None:
        stats = stats.split(" ")
        if 'all' in [x.lower() for x in stats]:
            stats = "ALL"

    zonal_results = zonal_stats(
        features,
        raster,
        all_touched=all_touched,
        band_num=band,
        categorical=categorical,
        nodata=nodata,
        stats=stats,
        prefix=prefix,
        geojson_out=True)

    feature_collection['features'] = zonal_results

    output_geojson.write(json.dumps(feature_collection, indent=indent))
    output_geojson.write("\n")


@click.command(context_settings=SETTINGS)
@click.argument('input-geojson', type=click.File('r'), default='-')
@click.argument('output-geojson', type=click.File('w'), default='-')
@click.version_option(version=version, message='%(version)s')
@click.option('--raster', '-r', required=True, type=click.Path(exists=True))
@click.option('--band', type=int, default=1)
@click.option('--nodata', type=int, default=None)
@click.option('--indent', type=int, default=None)
@click.option('--interpolate', type=str, default='bilinear')
@click.option('--property-name', type=str, default='value')
def pointquery(input_geojson, raster, output_geojson, band, indent, nodata,
               interpolate, property_name):
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
    mapping = json.loads(input_geojson.read())
    input_geojson.close()
    try:
        if mapping['type'] == "FeatureCollection":
            feature_collection = mapping
        else:
            feature_collection = {'type': 'FeatureCollection'}
        features = read_features(mapping)
    except (AssertionError, KeyError):
        raise ValueError("input_geojson must be valid GeoJSON")

    results = point_query(
        features,
        raster,
        band=band,
        nodata=nodata,
        interpolate=interpolate,
        property_name=property_name,
        geojson_out=True)

    feature_collection['features'] = results

    output_geojson.write(json.dumps(feature_collection, indent=indent))
    output_geojson.write("\n")
