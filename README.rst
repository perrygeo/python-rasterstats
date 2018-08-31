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

What does it do? 
----------------
Given a vector layer and a raster band, calculate the summary statistics of each vector geometry.
For example, with a polygon vector layer and a digital elevation model (DEM) raster, compute the
mean elevation of each polygon.

.. figure:: https://github.com/perrygeo/python-raster-stats/raw/master/docs/img/zones_elevation.png
   :align: center
   :alt: zones elevation

Command Line Quick Start
------------------------

The command line interfaces to zonalstats and point_query 
are `rio` subcommands which read and write geojson features

.. code-block:: bash

    $ fio cat polygon.shp | rio zonalstats -r elevation.tif 

    $ fio cat points.shp | rio pointquery -r elevation.tif

See the `CLI Docs <http://pythonhosted.org/rasterstats/cli.html>`_. for more detail.

Python Quick Start
-----------

For zonal statistics

.. code-block:: python

    >>> from rasterstats import zonal_stats
    >>> stats = zonal_stats("tests/data/polygons.shp", "tests/data/elevation.tif")
    >>> stats[1].keys()
    ['count', 'min', 'max', 'mean']
    >>> [f['mean'] for f in stats]
    [756.6057470703125, 114.660084635416666]

and for point queries

.. code-block:: python

    >>> from rasterstats import point_query
    >>> point = "POINT(245309 1000064)"
    >>> point_query(point, "tests/data/elevation.tif")
    [723.9872347624]


Issues
------

Find a bug? Report it via github issues by providing

- a link to download the smallest possible raster and vector dataset necessary to reproduce the error
- python code or command to reproduce the error
- information on your environment: versions of python, gdal and numpy and system memory

.. |BuildStatus| image:: https://api.travis-ci.org/perrygeo/python-rasterstats.svg
.. _BuildStatus: https://travis-ci.org/perrygeo/python-rasterstats

.. |CoverageStatus| image:: https://coveralls.io/repos/github/perrygeo/python-rasterstats/badge.svg?branch=master
.. _CoverageStatus: https://coveralls.io/github/perrygeo/python-rasterstats?branch=master
