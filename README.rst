rasterstats
===========

|BuildStatus|_
|CoverageStatus|_

``rasterstats`` is a Python module for summarizing geospatial raster datasets based on vector geometries.
It includes functions for **zonal statistics** and interpolated **point queries**. The command-line interface allows for
easy interoperability with other GeoJSON tools. 

Documentation
-------------
For details on installation and usage, visit the documentation at `http://pythonhosted.org/rasterstats <http://pythonhosted.org/rasterstats/>`_.

Quick Start
-----------

Given a polygon vector layer and a digitial elevation model (DEM)
raster, calculate the mean elevation of each polygon:

.. figure:: https://github.com/perrygeo/python-raster-stats/raw/master/docs/img/zones_elevation.png
   :align: center
   :alt: zones elevation

.. code-block:: python

    >>> from rasterstats import zonal_stats
    >>> stats = zonal_stats("tests/data/polygons.shp", "tests/data/elevation.tif")

    >>> stats[1].keys()
    ['count', 'min', 'max', 'mean']

    >>> [f['mean'] for f in stats]
    [756.6057470703125, 114.660084635416666]

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

