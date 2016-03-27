User Manual
===========

Introduction
------------
Geospatial data typically comes in one of two data models:
*rasters* which are similar to images with a regular grid of pixels whose values represent some spatial phenomenon (e.g. elevation) and
*vectors* which are entities with discrete geometries (e.g. state boundaries).
This software, ``rasterstats``, exists solely to extract information from geospatial raster data
based on vector geometries.

Primarily, this involves *zonal statistics*: a method of summarizing and aggregating the raster values intersecting a vector geometry. For example, zonal statistics provides answers such as the mean precipitation or maximum elevation of an administrative unit.  Additionally, functions are provided for *point queries*, most notably the ability to query a raster at a point and get an interpolated value rather than the simple nearest pixel.

Basic Example
-------------

The typical usage of rasterstats functions involves two arguments, a vector and a raster dataset::

    >>> from rasterstats import zonal_stats, point_query
    >>> stats = zonal_stats('tests/data/polygons.shp', 'tests/data/slope.tif')
    >>> pts = point_query('tests/data/points.shp', 'tests/data/slope.tif')
   
``zonal_stats`` gives us a list of two dictionaries corresponding to each input polygon::

    >>> from pprint import pprint
    >>> pprint(stats)
    [{'count': 75,
      'max': 22.273418426513672,
      'mean': 14.660084635416666,
      'min': 6.575114727020264},
     {'count': 50,
      'max': 82.69043731689453,
      'mean': 56.60576171875,
      'min': 16.940950393676758}]

while ``point_query`` gives us a list of raster values corresponding to each input point::

    >>> pts
    [14.037668283186257, 33.1370268256543, 36.46848854950241]

Vector Data Sources
-------------------
The most common use case is having vector data sources in a file such as an ESRI Shapefile or any
other format supported by ``fiona``. The path to the file can be passed in directly as the first argument::
    
    >>> zs = zonal_stats('tests/data/polygons.shp', 'tests/data/slope.tif')

If you have multi-layer sources, you can specify the ``layer`` by either name or index::

    >>> zs = zonal_stats('tests/data', 'tests/data/slope.tif', layer="polygons")

In addition to the basic usage above, rasterstats supports other
mechanisms of specifying vector geometries. 

The vector argument can be an iterable of GeoJSON-like features such as a fiona source::
    
    >>> import fiona
    >>> with fiona.open('tests/data/polygons.shp') as src:
    ...    zs = zonal_stats(src, 'tests/data/slope.tif')


You can also pass in an iterable of python objects that support
the ``__geo_interface__`` (e.g. Shapely, ArcPy, PyShp, GeoDjango)::

    >>> from shapely.geometry import Point
    >>> pt = Point(245000, 1000000)
    >>> pt.__geo_interface__
    {'type': 'Point', 'coordinates': (245000.0, 1000000.0)}
    >>> point_query([pt], 'tests/data/slope.tif')
    [21.32739672330894]


Strings in well known text (WKT) and binary (WKB) format ::

    >>> pt.wkt
    'POINT (245000 1000000)'
    >>> point_query([pt], 'tests/data/slope.tif')
    [21.32739672330894]
    
    >>> pt.wkb
    '\x01\x01\x00\x00\x00\x00\x00\x00\x00@\xe8\rA\x00\x00\x00\x00\x80\x84.A'
    >>> point_query([pt], 'tests/data/slope.tif')
    [21.32739672330894]


Raster Data Sources
-------------------

Any format that can be read by ``rasterio`` is supported by ``rasterstats``.
To test if a data source is supported by your installation (this might differ depending on the
format support of the underlying GDAL library), use the rio command line tool::

    $ rio info raster.tif

You can specify the path to the raster directly::

    >>> zs = zonal_stats('tests/data/polygons.shp', 'tests/data/slope.tif')

If the raster contains multiple bands, you must specify the band (1-indexed)::

    >>> zs = zonal_stats('tests/data/polygons.shp', 'tests/data/slope.tif', band=1)

Or you can pass a numpy ``ndarray`` with an affine transform mapping the array dimensions 
to a coordinate reference system::

    >>> import rasterio
    >>> with rasterio.open('tests/data/slope.tif') as src:
    ...     affine = src.affine
    ...     array = src.read(1)
    >>> zs = zonal_stats('tests/data/polygons.shp', array, affine=affine)


Zonal Statistics
----------------

Statistics
^^^^^^^^^^

By default, the ``zonal_stats`` function will return the following statistics

- min
- max
- mean
- count

Optionally, these statistics are also available.

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
    ...                     "tests/data/slope.tif",
    ...                     stats=['min', 'max', 'median', 'majority', 'sum'])

You can also specify as a space-delimited string::

    >>> stats = zonal_stats("tests/data/polygons.shp",
    ...                     "tests/data/slope.tif",
    ...                     stats="min max median majority sum")


Note that certain statistics (majority, minority, and unique) require significantly more processing
due to expensive counting of unique occurences for each pixel value.

You can also use a percentile statistic by specifying
``percentile_<q>`` where ``<q>`` can be a floating point number between 0 and 100.

User-defined Statistics
^^^^^^^^^^^^^^^^^^^^^^^
You can define your own aggregate functions using the ``add_stats`` argument.
This is a dictionary with the name(s) of your statistic as keys and the function(s)
as values. For example, to reimplement the `mean` statistic::

    >>> from __future__ import division
    >>> import numpy as np

    >>> def mymean(x):
    ...     return np.ma.mean(x)

then use it in your ``zonal_stats`` call like so::

    >>> zonal_stats("tests/data/polygons.shp",
    ...             "tests/data/slope.tif",
    ...             stats="count",
    ...             add_stats={'mymean':mymean})
    [{'count': 75, 'mymean': 14.660084635416666}, {'count': 50, 'mymean': 56.605761718750003}]


GeoJSON output
^^^^^^^^^^^^^^

If you want to retain the geometries and properties of the input features,
you can output a list of geojson features using ``geojson_out``. The features
contain the zonal statistics as additional properties::

    >>> stats = zonal_stats("tests/data/polygons.shp",
    ...                     "tests/data/slope.tif",
    ...                     geojson_out=True)

    >>> stats[0]['type']
    'Feature'
    >>> stats[0]['properties'].keys()
    [u'id', 'count', 'max', 'mean', 'min']


Rasterization Strategy
^^^^^^^^^^^^^^^^^^^^^^

There is no right or wrong way to rasterize a vector. The default strategy is to include all pixels along the line render path (for lines), or cells where the *center point* is within the polygon (for polygons).  Alternatively, you can opt for the ``all_touched`` strategy which rasterizes the geometry by including all pixels that it touches. You can enable this specifying::

    >>> zs = zonal_stats("tests/data/polygons.shp",
    ...                  "tests/data/slope.tif",
    ...                  all_touched=True)

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

Using ``categorical``, the output is dictionary with the unique raster values as keys
and pixel counts as values::

    >>> zonal_stats('tests/data/polygons.shp',
    ...             'tests/data/slope_classes.tif',
    ...             categorical=True)[1]
    {1.0: 1, 2.0: 9, 5.0: 40}

rasterstats will report using the pixel values as keys. 
To associate the pixel values with their appropriate meaning,
you can use a ``category_map``::

    >>> cmap = {1.0: 'low', 2.0: 'med', 5.0: 'high'}
    >>> zonal_stats('tests/data/polygons.shp',
    ...             'tests/data/slope_classes.tif',
    ...             categorical=True, category_map=cmap)[1]
    {'high': 40, 'med': 9, 'low': 1}

"Mini-Rasters"
^^^^^^^^^^^^^^^

Internally, we create a masked raster dataset for each feature in order to
calculate statistics. Optionally, we can include these data in the output
of ``zonal_stats`` using the ``raster_out`` argument::

    >>> zonal_stats('tests/data/polygons.shp',
    ...             'tests/data/slope_classes.tif',
    ...             stats="count",
    ...             raster_out=True)[0].keys()
    ['count', 'mini_raster_affine', 'mini_raster_array', 'mini_raster_nodata']
    
Notice we have three additional keys::

* ``mini_raster_array``: The clipped and masked numpy array
* ``mini_raster_affine``: transformation as an Affine object
* ``mini_raster_nodata``: The nodata value

Keep in mind that having ndarrays in your stats dictionary means it is more
difficult to serialize to json and other text formats.


Design Goals
------------

``rasterstats`` aims to do only one thing well: getting information from rasters based on vector geometry.
This module doesn't support coordinate reprojection, raster re-sampling, geometry manipulations or any other
geospatial data transformations as those are better left to other Python packages. To the extent possible,
data input is handled by ``fiona`` and ``rasterio``, though there are some wrapper functions for IO to
maintain usability. Where interoperability between packages is needed, loose coupling, simple python data structure
and standard interfaces like GeoJSON are employed to keep the core library lean.

History
--------
This work grew out of a need to have a native python implementation (based on numpy) for zonal statisics.
I had been `using starspan <http://www.perrygeo.com/starspan-for-vector-on-raster-analysis.html>`_, a C++
command line tool, as well as GRASS's `r.statistics <https://grass.osgeo.org/grass70/manuals/r.statistics.html>`_ for many years.
They were suitable for offline analyses but were rather clunky to deploy in a large python application.
In 2013, I implemented a proof-of-concept zonal stats function which eventually became ``rasterstats``. It has
been in production in several large python web applications ever since, replacing the starspan wrapper `madrona.raster_stats <https://github.com/Ecotrust/madrona/blob/master/docs/raster_stats.rst>`_.


