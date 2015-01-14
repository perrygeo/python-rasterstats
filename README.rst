rasterstats
===========

|BuildStatus|_ 
|CoverageStatus|_
|PyPiVersion|_
|PyPiDownloads|_

The ``rasterstats`` python module provides a fast and flexible
tool to summarize geospatial raster datasets based on vector geometries
(i.e. zonal statistics). 

-  Raster data support

   -  Any raster data source supported by GDAL
   -  Support for continuous and categorical
   -  Respects null/no-data metadata or takes argument
-  Vector data support

   -  Points, Lines, Polygon and Multi-\* geometries
   -  Flexible input formats
   
      -  Any vector data source supported by OGR
      -  Python objects that are geojson-like mappings or support the `geo\_interface <https://gist.github.com/sgillies/2217756>`_
      -  Well-Known Text/Binary (WKT/WKB) geometries
-  Depends on GDAL, Shapely and numpy


Install
-------

Using ubuntu 12.04::

   sudo apt-get install python-numpy python-gdal 
   pip install rasterstats


Example Usage
-------------

Given a polygon vector layer and a digitial elevation model (DEM)
raster, calculate the mean elevation of each polygon:

.. figure:: https://github.com/perrygeo/python-raster-stats/raw/master/docs/img/zones_elevation.png
   :align: center
   :alt: zones elevation

::

    >>> from rasterstats import zonal_stats
    >>> stats = zonal_stats("tests/data/polygons.shp", "tests/data/elevation.tif")

    >>> stats[1].keys()
        ['__fid__', 'count', 'min', 'max', 'mean']

    >>> [(f['__fid__'], f['mean']) for f in stats]
        [(1, 756.6057470703125), (2, 114.660084635416666)]

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

You can specify the statistics to calculate using the ``stats`` argument::

    >>> stats = zonal_stats("tests/data/polygons.shp", 
                             "tests/data/elevation.tif"
                             stats=['min', 'max', 'median', 'majority', 'sum'])

    >>> # also takes space-delimited string
    >>> stats = zonal_stats("tests/data/polygons.shp", 
                             "tests/data/elevation.tif"
                             stats="min max median majority sum")


Note that the more complex statistics may require significantly more processing so 
performance can be impacted based on which statistics you choose to calculate.

Specifying Geometries
^^^^^^^^^^^^^^^^^^^^^

In addition to the basic usage above, rasterstats supports other
mechanisms of specifying vector geometeries.

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

There are two rasterization strategies to consider::

1. (DEFAULT) Rasterize to the line render path or cells having a center point within the polygon
2. The ``ALL_TOUCHED`` strategy which rasterizes the geometry according to every cell that it touches. You can enable this specifying::
    
    >>> zonal_stats(..., all_touched=True)

There is no right or wrong way to rasterize a vector; both approaches are valid and there are tradeoffs to consider. Using the default rasterizer may miss polygons that are smaller than your cell size. Using the ALL_TOUCHED strategy includes many cells along the edges that may not be representative of the geometry and give biased results when your geometries are much larger than your cell size.   


Working with categorical rasters 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can treat rasters as categorical (i.e. raster values represent
discrete classes) if you're only interested in the counts of unique pixel
values.

For example, you may have a raster vegetation dataset and want to summarize 
vegetation by polygon. Statistics such as mean, median, sum, etc. don't make much sense in this context
(What's the sum of oak + grassland?). 

The polygon below is comprised of 12 pixels of oak (raster value
32) and 78 pixels of grassland (raster value 33)::

    >>> zonal_stats(lyr.next(), '/path/to/vegetation.tif', categorical=True)

    >>> [{'__fid__': 1, 32: 12, 33: 78}]

Keep in mind that rasterstats just
reports on the pixel values as keys; It is up to the programmer to
associate the pixel values with their appropriate meaning (e.g. oak ==
32) for reporting.

Issues
------

Find a bug? Report it via github issues by providing

- a link to download the smallest possible raster and vector dataset necessary to reproduce the error
- python code or command to reproduce the error
- information on your environment: versions of python, gdal and numpy and system memory

.. |BuildStatus| image:: https://api.travis-ci.org/ozak/python-raster-stats.png
.. _BuildStatus: https://travis-ci.org/ozak/python-raster-stats

.. |CoverageStatus| image:: https://coveralls.io/repos/ozak/python-raster-stats/badge.png
.. _CoverageStatus: https://coveralls.io/r/ozak/python-raster-stats

.. |PyPiVersion| image:: https://pypip.in/v/rasterstats/badge.png
.. _PyPiVersion: http://pypi.python.org/pypi/rasterstats

.. |PyPiDownloads| image:: https://pypip.in/d/rasterstats/badge.png
.. _PyPiDownloads: http://pypi.python.org/pypi/rasterstats
