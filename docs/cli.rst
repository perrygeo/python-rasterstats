Command Line Interface
======================

As of version 0.8, ``rasterstats`` includes a command line interface (as a `rasterio plugin <https://github.com/mapbox/rasterio/blob/master/docs/cli.rst#rio-plugins>`_)
for performing zonal statistics and point_queries at the command line.


.. code-block:: console

    Usage: rio zonalstats [OPTIONS] FEATURES...

    zonalstats generates summary statistics of geospatial raster datasets
    based on vector features.

    The input arguments to zonalstats should be valid GeoJSON Features. (see
    cligj)

    The output GeoJSON will be mostly unchanged but have additional properties
    per feature describing the summary statistics (min, max, mean, etc.) of
    the underlying raster dataset.

    The raster is specified by the required -r/--raster argument.

    Example, calculate rainfall stats for each state and output to file:

      rio zonalstats states.geojson -r rainfall.tif > mean_rainfall_by_state.geojson

    Options:
    --version                       Show the version and exit.
    -r, --raster PATH               [required]
    --all-touched / --no-all-touched
    --band INTEGER
    --categorical / --no-categorical
    --indent INTEGER
    --info / --no-info
    --nodata INTEGER
    --prefix TEXT
    --stats TEXT
    --sequence / --no-sequence      Write a LF-delimited sequence of texts
                                    containing individual objects or write a
                                    single JSON text containing a feature
                                    collection object (the default).
    --rs / --no-rs                  Use RS (0x1E) as a prefix for individual
                                    texts in a sequence as per
                                    http://tools.ietf.org/html/draft-ietf-json-
                                    text-sequence-13 (default is False).
    -h, --help                      Show this message and exit.


.. code-block:: console

    $ rio pointquery --help
    Usage: rio pointquery [OPTIONS] FEATURES...

    Queries the raster values at the points of the input GeoJSON Features. The
    raster values are added to the features properties and output as GeoJSON
    Feature Collection.

    If the Features are Points, the point geometery is used. For other
    Feauture types, all of the verticies of the geometry will be queried. For
    example, you can provide a linestring and get the profile along the line
    if the verticies are spaced properly.

    You can use either bilinear (default) or nearest neighbor interpolation.

    Options:
    --version                   Show the version and exit.
    -r, --raster PATH           [required]
    --band INTEGER
    --nodata INTEGER
    --indent INTEGER
    --interpolate TEXT
    --property-name TEXT
    --sequence / --no-sequence  Write a LF-delimited sequence of texts
                                containing individual objects or write a single
                                JSON text containing a feature collection object
                                (the default).
    --rs / --no-rs              Use RS (0x1E) as a prefix for individual texts
                                in a sequence as per http://tools.ietf.org/html
                                /draft-ietf-json-text-sequence-13 (default is
                                False).
    -h, --help                  Show this message and exit.


Example
-----------

In the following examples we use a polygon shapefile representing countries (``countries.shp``) and a raster digitial elevation model (``dem.tif``). The data are assumed to be in the same spatial reference system.

GeoJSON inputs
^^^^^^^^^^^^^^
First we must get our data into GeoJSON format. There are a number of options for that but we will use ``fio cat`` command that ships with the ``fiona`` python library::

    fio cat countries.shp

This will print the GeoJSON Features to the terminal (stdout) with Features like::

    {"type": Feature, "geometry": {...} ,"properties": {...}}

We'll use unix pipes to pass this data directly into our zonal stats command without an intemediate file.

Specifying the Raster
^^^^^^^^^^^^^^^^^^^^^

There is one required option to ``rio zonalstats``: the ``--raster`` or ``-r`` option which is a file path to a raster dataset that can be read by rasterio.

So now our command becomes::

    fio cat countries.shp | rio zonalstats -r dem.tif

GeoJSON Output
^^^^^^^^^^^^^^

The output FeatureCollection will contain the same number of features, same geometries, etc. but will have several additional properties attached to each feature::


    {
      "type": "Feature",
      "geometry": {...} ,
      "properties": {
        "country_name": "Grenada",
        "_min": 0.0,
        "_mean": 210.47,
        "_max": 840.33,
        "_count": 94
      }
    }

Fairly self explanatory; the min, mean and max are the default summary statistics and the count is the number of overlapping raster cells. By default the property names are prefixed with ``_`` but you can specify your own with ``--prefix``::

    $ fio cat countries.shp | rio zonalstats -r dem.tif --prefix "elevation_"
    ...
    {
      "type": "Feature",
      "geometry": {...} ,
      "properties": {
        "country_name": "Grenada",
        "elevation_min": 0.0,
        "elevation_mean": 210.47,
        "elevation_max": 840.33,
        "elevation_count": 94
      }
    }

If we want to save the output, simply redirect to a file::

    fio cat countries.shp | rio zonalstats -r dem.tif --prefix "elevation_" > countries_with_elevation.geojson

Sequences or FeatureCollections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
By default, all of the features are collected into a single GeoJSON FeatureCollection which is echoed to ``stdout``.

You can choose to emit sequences of line-delimited Features with `--use-sequence` and add the optional rs-delimiter with ``--use-rs``. The use of sequences for input and output features allows you to stream large datasets without memory limitations::

    fio cat large.shp | rio zonalstats -r elevation.tif --sequence | some-other-process


Other statistics
^^^^^^^^^^^^^^^^

The main README contains the complete list of summary statistics, any number of which can be specified using the ``--stats`` option in the form of a space-delimited string::

    $ fio cat countries.shp \
        | rio zonalstats -r dem.tif \
              --prefix "elevation_" \
              --stats "min max median percentile_95"
    ...
    {
      "type": "Feature",
      "geometry": {...} ,
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
