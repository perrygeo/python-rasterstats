rasterstats
===========

``rasterstats`` is a Python module for summarizing geospatial raster datasets based on vector geometries.
It includes functions for zonal statistics and interpolated point queries. The command-line interface allows for
easy interoperability with other GeoJSON tools. 

Raster data support
-------------------
Can work with any raster data source supported by `rasterio <https://github.com/mapbox/rasterio>`_.
Data can be categorical (e.g. vegetation types) or continuous values (e.g. elevation).

Vector data support
-------------------
Flexible support for vector features with Point, LineString, Polygon or Multi\* geometries. 
Any `fiona <http://toblerity.org/fiona/>`_ data source,
GeoJSON-like mapping, objects with a `geo\_interface <https://gist.github.com/sgillies/2217756>`_, 
GeoJSON strings and Well-Known Text/Binary (WKT/WKB) geometries are all supported via the ``io`` submodule.

Quickstart
------------------------

Install::

    pip install rasterstats


Given a polygon vector layer and a digitial elevation model (DEM) raster:

.. figure:: https://github.com/perrygeo/python-raster-stats/raw/master/docs/img/zones_elevation.png
   :align: center
   :alt: zones elevation

calculate summary statistics of elevation for each polygon using::

    from rasterstats import zonal_stats
    zonal_stats("polygons.shp", "elevation.tif",
                stats="count min mean max median")

returns a ``list`` of ``dicts``, one for each Feature in ``polygons.shp``::

    [...,
     {'count': 89,
      'max': 69.52958679199219,
      'mean': 20.08093536034059,
      'median': 19.33736801147461,
      'min': 1.5106816291809082},
    ]


Next steps
----------

.. toctree::
  :maxdepth: 2

  installation
  manual
  cli
  rasterstats


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

