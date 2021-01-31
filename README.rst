rasterstats
===========

|BuildStatus|_

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
------------------

For zonal statistics

.. code-block:: python

    >>> from rasterstats import zonal_stats
    >>> stats = zonal_stats("tests/data/polygons.shp", "tests/data/slope.tif")
    >>> stats[0].keys()
    dict_keys(['min', 'max', 'mean', 'count'])
    >>> [f['mean'] for f in stats]
    [14.660084635416666, 56.60576171875]

and for point queries

.. code-block:: python

    >>> from rasterstats import point_query
    >>> point = {'type': 'Point', 'coordinates': (245309.0, 1000064.0)}
    >>> point_query(point, "tests/data/slope.tif")
    [74.09817594635244]


Issues
------

Find a bug? Report it via github issues by providing

- a link to download the smallest possible raster and vector dataset necessary to reproduce the error
- python code or command to reproduce the error
- information on your environment: versions of python, gdal and numpy and system memory

.. |BuildStatus| image:: https://github.com/perrygeo/python-rasterstats/workflows/Rasterstats%20Python%20package/badge.svg
.. _BuildStatus: https://github.com/perrygeo/python-rasterstats/actions
