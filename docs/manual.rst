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

basics::

    from rasterstats import zonal_stats, point_query
    stats = zonal_stats('polygons.shp', 'raster.tif')
    pts = point_query('points.shp', 'raster.tif')
   
`stats` gives us a list of two dictionaries, one for each polygon::

    [{'count': 75,
      'max': 22.273418426513672,
      'mean': 14.660084635416666,
      'min': 6.575114727020264},
     {'count': 50,
      'max': 82.69043731689453,
      'mean': 56.60576171875,
      'min': 16.940950393676758}]

while `pts` gives us a list of raster values, one for each point::

    [14.037668283186257, 33.1370268256543]

Vector Data Sources
-------------------
The most common use case is having vector data sources in a file such as an ESRI Shapefile or any
other format supported by ``fiona``. The path to the file can be passed in directly as the first argument::
    
    zonal_stats('/path/to/shapefile.shp', ..)

or if you'd prefer to use fiona explicity::
    
    import fiona
    with fiona.open('/path/to/shapefile.shp') as src:
        zonal_stats(src, ...)

In addition to the basic usage above, rasterstats supports other
mechanisms of specifying vector geometries.

It integrates with other python objects that support the geo\_interface
(e.g. Shapely, ArcPy, PyShp, GeoDjango)::

    # TODO 

Or strings in well known text (WKT) format ::

    zonal_stats('POINT(-124 42)', '/path/to/elevation.tif')

TODO 
^^^^
layer numbers
GeoJSON-like features
Geojson strings
WKB
Other sources (postgis, spatialite, etc)

Raster Data Sources
-------------------

Any format that can be read by ``rasterio`` is supported by ``rasterstats``. This generally means any of the GDAL-supported data source as that library is used rasterio for data access.
To test if a data source is supported, use the rio command line tool::

    $ rio info raster.tif

If that succeeds, the raster is supported.  

TODO
^^^^
Band numbers
Multiband

Zonal Statistics
----------------

Statistics
^^^^^^^^^^

By default, the ``zonal_stats`` function will return the following statistics

- min
- max
- mean
- count

Optionally, these statistics are also available. TODO describe in more detail

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



Feature Properties
^^^^^^^^^^^^^^^^^^

By default, an \_\_fid\_\_ property is added to each feature's results. None of
the other feature attributes/proprties are copied over unless ``copy_properties``
is set to True::

    >>> stats = zonal_stats("tests/data/polygons.shp",
                             "tests/data/elevation.tif"
                             copy_properties=True)

    >>> stats[0].has_key('name')  # name field from original shapefile is retained
    True


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

Point Query
------------
TODO

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


