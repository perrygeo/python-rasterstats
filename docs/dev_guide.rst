Developers Guide
================

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


