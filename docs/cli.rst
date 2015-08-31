Command Line Interface
======================

As of version 0.8, ``rasterstats`` includes a command line interface (as a `rasterio plugin <https://github.com/mapbox/rasterio/blob/master/docs/cli.rst#rio-plugins>`_)
for performing zonal statistics at the command line.

.. code-block:: console

    $ rio zonalstats --help
    Usage: rio zonalstats [OPTIONS] [INPUT_GEOJSON] [OUTPUT_GEOJSON]

      zonalstats generates summary statistics of geospatial raster datasets
      based on vector features.

      The input and output arguments of zonalstats should be valid GeoJSON
      FeatureCollections. The output GeoJSON will be mostly unchanged but have
      additional properties per feature describing the summary statistics (min,
      max, mean, etc.) of the underlying raster dataset. The input and output
      arguments default to stdin and stdout but can also be file paths.

      The raster is specified by the required -r/--raster argument.

      Example, calculate rainfall stats for each state and output to file:

      zonalstats states.geojson -r rainfall.tif > mean_rainfall_by_state.geojson

    Options:
      --version                       Show the version and exit.
      -r, --raster PATH               [required]
      --all-touched / --no-all-touched
      --band INTEGER
      --categorical / --no-categorical
      --global-src-extent / --no-global-src-extent
      --indent INTEGER
      --info / --no-info
      --nodata INTEGER
      --prefix TEXT
      --stats TEXT
      -h, --help                      Show this message and exit.


Example
-----------

In the following examples we use a polygon shapefile representing countries (``countries.shp``) and a raster digitial elevation model (``dem.tif``). The data are assumed to be in the same spatial reference system.

GeoJSON inputs
^^^^^^^^^^^^^^
First we must get our data into GeoJSON format. There are a number of options for that but we will use ``fio dump`` command that ships with the ``fiona`` python library::

    fio dump countries.shp

This will print the GeoJSON FeatureCollection to the terminal (stdout) with Features like::

    {
      "geometry": .... ,
      "properties": {
        "country_name": "Grenada"
      }
    }

We'll use unix pipes to pass this data directly into our zonal stats command without an intemediate file.

Specifying the Raster
^^^^^^^^^^^^^^^^^^^^^

There is one required option to ``rio zonalstats``: the ``--raster`` or ``-r`` option which is a file path to a raster dataset that can be read by rasterio.

So now our command becomes::

    fio dump countries.shp | rio zonalstats -r dem.tif

GeoJSON Output
^^^^^^^^^^^^^^

The output FeatureCollection will contain the same number of features, same geometries, etc. but will have several additional properties attached to each feature::


    {
      "geometry": .... ,
      "properties": {
        "country_name": "Grenada",
        "_min": 0.0,
        "_mean": 210.47,
        "_max": 840.33,
        "_count": 94
      }
    }

Fairly self explanatory; the min, mean and max are the default summary statistics and the count is the number of overlapping raster cells. By default the property names are prefixed with ``_`` but you can specify your own with ``--prefix``::

    $ fio dump countries.shp | rio zonalstats -r dem.tif --prefix "elevation_"
    ...
    {
      "geometry": .... ,
      "properties": {
        "country_name": "Grenada",
        "elevation_min": 0.0,
        "elevation_mean": 210.47,
        "elevation_max": 840.33,
        "elevation_count": 94
      }
    }

If we want to save the output, simply redirect to a file::

    fio dump countries.shp | rio zonalstats -r dem.tif --prefix "elevation_" > countries_with_elevation.geojson

Other statistics
^^^^^^^^^^^^^^^^

The main README contains the complete list of summary statistics, any number of which can be specified using the ``--stats`` option in the form of a space-delimited string::

    $ fio dump countries.shp \
        | rio zonalstats -r dem.tif \
              --prefix "elevation_" \
              --stats "min max median percentile_95"
    ...
    {
      "geometry": .... ,
      "properties": {
        "country_name": "Grenada",
        "elevation_min": 0.0,
        "elevation_median": 161.33
        "elevation_max": 840.33,
        "elevation_percentile_95": 533.6
      }
    }

Rasterization strategy
^^^^^^^^^^^^^^^^^^^^^^

As discussed in the main README, the default rasterization of each feature only considers those cells whose *centroids* intersect with the geometry. If you want to include all cells touched by the geometry, even if there is only a small degree of overlap, you can specify the ``--all-touched`` option. This is helpful if your features are much smaller scale than your raster data (e.g. tax lot parcels on a coarse weather data raster)

Putting it all together
^^^^^^^^^^^^^^^^^^^^^^^

The great part about working at the command line is the ability to pipe the data (in this case GeoJSON) between processes. This allows the construction of complex data processing pipelines with very simple code. It also allows developers fluent in different programming languages to collaborate on workflows via a common text interchange format.

In this example, we take our original country data and

* filter the features to limit the analysis to the Latin America & Caribbean region (using `TurfJS <http://turfjs.org>`_ written in javascript)
* flatten the multipart geometries so I can analyze each island individually (using `geojson-flatten <https://github.com/mapbox/geojson-flatten>`_ written in javascript)
* run zonal statistics against the raster elevation data (using ``rio zonalstats`` written in python)
* save the geojson locally (using the `tee` unix command)
* and finally display the data in an HTML interface (using the geojson.io web service)

To implement this as a shell script::

    #!/bin/bash
    countries="countries.shp"
    dem="dem.tif"
    output="elevation_centralsouthamerica.geojson"

    fio dump $countries \
    | turf filter /dev/stdin "region_wb" "Latin America & Caribbean" \
    | geojson-flatten \
    | rio zonalstats --raster $dem --prefix "elevation_" \
    | tee $output \
    | geojsonio

And the result: a geojson-based web map of South & Central American islands containing their elevation stats.

.. image:: img/bahamas.png

For analysts, if you've ever performed similar work in a Desktop GIS environment, you might imagine the pages of screenshots and elaborate instructions necessary to document a process like this. By contrast, our script is only 10 lines and is nearly as easy to understand as our narrative description (if just a bit more terse). Scripting on the command line also means that your workflows are now sharable in version control systems, repeatable and automated.

For developers, each tool in the pipeline needs only concern itself with doing one thing well in the language of your choice; a truly modular system composed of smaller parts which help to avoid the pitfalls of monolithic solutions.

It is now possible to do many (though not all) common GIS data analyses at the shell using open source software.
The ecosystem of command line spatial data processing tools (particularly in the JavaScript and Python communities) are constantly evolving and fairly soon I suspect that all but the most specialized spatial tools will be readily available and easily integrated at the shell, just a ``pip install`` or ``npm install`` away.

