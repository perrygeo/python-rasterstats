rasterstats
===========

|BuildStatus|_
|CoverageStatus|_

The ``rasterstats`` python module provides a fast and flexible
tool to summarize geospatial raster datasets based on vector geometries
(i.e. zonal statistics).

-  Raster data support

   -  Any raster data source supported by `rasterio <https://github.com/mapbox/rasterio>`_ and GDAL
   -  Support for continuous and categorical
   -  Respects null/no-data metadata or takes argument
-  Vector data support

   -  Points, Lines, Polygon and Multi-\* geometries
   -  Flexible input formats

      -  Any vector data source supported by `fiona <http://toblerity.org/fiona/>`_
      -  Python objects that are GeoJSON-like mappings or support the `geo\_interface <https://gist.github.com/sgillies/2217756>`_
      -  Well-Known Text/Binary (WKT/WKB) geometries
-  Depends on libgdal, rasterio, fiona, shapely and numpy


Install
-------

Using Ubuntu 14.04::

   sudo apt-get install python-numpy libgdal1h gdal-bin libgdal-dev
   pip install rasterstats

Or homebrew on OS X::

    brew install gdal
    pip install rasterstats

For Windows, follow the `rasterio installation <https://github.com/mapbox/rasterio#windows-1>`_ and then run::

    pip install rasterstats


Example Usage - Python
------------------------

Given a polygon vector layer and a digitial elevation model (DEM)
raster, calculate the mean elevation of each polygon:

.. figure:: https://github.com/perrygeo/python-raster-stats/raw/master/docs/img/zones_elevation.png
   :align: center
   :alt: zones elevation

::

    >>> from rasterstats import zonal_stats
    >>> stats = zonal_stats("tests/data/polygons.shp", "tests/data/elevation.tif")

    >>> stats[1].keys()
        ['count', 'min', 'max', 'mean']

    >>> [f['mean'] for f in stats]
        [756.6057470703125, 114.660084635416666]


Example Usage - Command Line
------------------------------

``rasterstats`` includes a `rasterio plugin <https://github.com/mapbox/rasterio/blob/master/docs/cli.rst#rio-plugins>`_ 
for performing zonal statistics at the command line. 
Given a raster and geojson input, the ``rio zonalstats`` command will summarize the raster cell values for all features and output to geojson. In the resulting GeoJSON FeatureCollection, each Feature will have additional properties containing summary statistics of the overlapping raster cells. 

For example, you could summarize the elevation (``srtm5k.tif``) by country (``countries.json``) using the following command:

.. code-block:: console

    $ rio zonalstats -r srtm5k.tif countries.json countries_with_elevation.geojson

Or use stdin/stdout to pipe geojson data between processes 

.. code-block:: console

    $ ogr2ogr -f GeoJSON /vsistdout/ countries.shp | rio zonalstats -r srtm5k.tif | geojsonio

For more comprehensive documentation of the command line interface, see `the docs <https://github.com/perrygeo/python-raster-stats/blob/master/docs/cli.rst>`_.

Statistics
^^^^^^^^^^

By default, the ``zonal_stats`` function will return the following statistics

- min
- max
- mean
- count

Optionally, these statistics are also available

- sum
- std
- median
- majority
- minority
- unique
- range
- nodata
- percentile (see note below for details)

You can specify the statistics to calculate using the ``stats`` argument::

    >>> stats = zonal_stats("tests/data/polygons.shp",
                             "tests/data/elevation.tif",
                             stats=['min', 'max', 'median', 'majority', 'sum'])

    >>> # also takes space-delimited string
    >>> stats = zonal_stats("tests/data/polygons.shp",
                             "tests/data/elevation.tif",
                             stats="min max median majority sum")


Note that certain statistics (majority, minority, and unique) require significantly more processing
due to expensive counting of unique occurences for each pixel value.

You can also use a percentile statistic by specifying
``percentile_<q>`` where ``<q>`` can be a floating point number between 0 and 100.

User-defined Statistics
^^^^^^^^^^^^^^^^^^^^^^^
You can define your own aggregate functions using the ``add_stats`` argument.
This is a dictionary with the name(s) of your statistic as keys and the function(s)
as values. For example, to reimplement the `mean` statistic::

    from __future__ import division
    import numpy as np

    def mymean(x):
        return np.ma.mean(x)

then use it in your ``zonal_stats`` call like so::

    stats = zonal_stats(vector, raster, add_stats={'mymean':mymean})


Specifying Geometries
^^^^^^^^^^^^^^^^^^^^^

In addition to the basic usage above, rasterstats supports other
mechanisms of specifying vector geometries.

It integrates with other python objects that support the geo\_interface
(e.g. Fiona, Shapely, ArcPy, PyShp, GeoDjango)::

    >>> import fiona

    >>> # an iterable of objects with geo_interface
    >>> lyr = fiona.open('/path/to/vector.shp')
    >>> features = (x for x in lyr if x['properties']['state'] == 'CT')
    >>> zonal_stats(features, '/path/to/elevation.tif')
    ...

    >>> # a single object with a geo_interface
    >>> lyr = fiona.open('/path/to/vector.shp')
    >>> zonal_stats(lyr.next(), '/path/to/elevation.tif')
    ...

Or by using with geometries in "Well-Known" formats::

    >>> zonal_stats('POINT(-124 42)', '/path/to/elevation.tif')
    ...

Retaining Feature info with GeoJSON output
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, `zonal_stats` returns a list of dictionaries containing the statistics.
If you want to retain all of the feature (geometry, id, properties, etc) and 
just append the stats as additional properties, you can set `geojson_out` to `True`::

    >>> stats = zonal_stats("tests/data/polygons.shp",
                             "tests/data/elevation.tif"
                             geojson_out=True, prefix="elevation", stats="mean")

    >>> stats[0]['properties']['elevation_mean'] 
    756.6057470703125


Rasterization Strategy
^^^^^^^^^^^^^^^^^^^^^^

There is no right or wrong way to rasterize a vector. The default strategy is to include all pixels along the line render path (for lines), or cells where the *center point* is within the polygon (for polygons).  Alternatively, you can opt for the ``all_touched`` strategy which rasterizes the geometry by including all pixels that it touches. You can enable this specifying::

    >>> zonal_stats(..., all_touched=True)

.. figure:: https://github.com/perrygeo/python-raster-stats/raw/master/docs/img/rasterization.png
   :align: center
   :alt: rasterization

The figure above illustrates the difference; the default ``all_touched=False`` is on the left
while the ``all_touched=True`` option is on the right.
Both approaches are valid and there are tradeoffs to consider. Using the default rasterizer may miss polygons that are smaller than your cell size resulting in ``None`` stats for those geometries. Using the ``all_touched`` strategy includes many cells along the edges that may not be representative of the geometry and may give severly biased results in some cases.


Working with categorical rasters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can treat rasters as categorical (i.e. raster values represent
discrete classes) if you're only interested in the counts of unique pixel
values.

For example, you may have a raster vegetation dataset and want to summarize
vegetation by polygon. Statistics such as mean, median, sum, etc. don't make much sense in this context
(What's the sum of ``oak + grassland``?).

The polygon below is comprised of 12 pixels of oak (raster value
32) and 78 pixels of grassland (raster value 33)::

    >>> zonal_stats(lyr.next(), '/path/to/vegetation.tif', categorical=True)
    [{32: 12, 33: 78}]

rasterstats will report using the pixel values as keys. 
To associate the pixel values with their appropriate meaning 
(for example ``oak`` instead of ``32``), you can use a ``category_map``::

    >>> cmap = {32: 'oak', 33: 'grassland'}
    >>> zonal_stats(lyr.next(), '/path/to/vegetation.tif',
                    categorical=True, category_map=cmap)
    [{'oak': 12, 'grassland': 78}]

"Mini-Rasters"
^^^^^^^^^^^^^^^

Internally, we create a masked raster dataset for each feature in order to
calculate statistics. Optionally, we can include these data in the output
of ``zonal_stats`` using the ``raster_out`` argument::

    stats = zonal_stats(vector, raster, raster_out=True)

Which gives us three additional keys for each feature::

    mini_raster_array: The clipped and masked numpy array
    mini_raster_affine: Affine transform (not a GDAL-style geotransform)
    mini_raster_nodata: nodata Value

Keep in mind that having ndarrays in your stats dictionary means it is more
difficult to serialize to json and other text formats.

Issues
------

Find a bug? Report it via github issues by providing

- a link to download the smallest possible raster and vector dataset necessary to reproduce the error
- python code or command to reproduce the error
- information on your environment: versions of python, gdal and numpy and system memory

.. |BuildStatus| image:: https://api.travis-ci.org/perrygeo/python-rasterstats.png
.. _BuildStatus: https://travis-ci.org/perrygeo/python-rasterstats

.. |CoverageStatus| image:: https://coveralls.io/repos/perrygeo/python-rasterstats/badge.png
.. _CoverageStatus: https://coveralls.io/r/perrygeo/python-raster-stats

