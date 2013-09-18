# python-raster-stats

Summary statistics of raster dataset values based on vector geometries.

Docs (API, Topics)
Examples
Build status
Test coverage

## Quickstart

You've got a raster dataset representing elevation and a vector dataset representing county boundaries. 
Show the average, min and max elevation for each county
Show percentage of land cover by county
Output to csv (via CLI)
Pass geometries via wkt or wkb (single & list)
Integrate with other python packages via __geo_interface__

## Features

* Raster data support: 
  * Any continuous raster band supported by GDAL
* Vector data support:
  * OGR layer
* Python module (returns built in python data structures - list of dicts)
* Depends on GDAL, GEOS, shapely and numpy
* Full coverage unit testing

## Issues
To report a bug via github issues: provide smallest possible raster, vector and code to reproduce it

## Docs

## TODO 
* respects null/no-data values
* covering edge cases for input datasets
* command line interface which returns csv data and optionally copies over original vector attrs
* supports categorical
* Vector data:
  * Points, Lines, Polygon and Multi-* geometries
  * Can specify:
    * OGR layer
    * single geoms or list of geometries represented by wkts, wkbs or any object that supports the __geo_interface__
* projection support
* pip installable
* python 2 & 3 support
* buildthedocs OR use some sort of literate programming
* travis-ci and https://coveralls.io/info/features
* Examples for PyShp, GeoDjango, Fiona, Path to OGR resource, ArcPy (as Ipython notebooks?)
* reproject on the fly using projection metadata
* heavily profiled using a wide range of input data. The resulting heuristics used to automatically configure for optimal performance. Optimzation heuristic for determining global_src_extent - number of features - extent of features - available system memory vs raster_extent
* CLI: pivots for categorical
* support parallel processing on multiple CPUs via the `multiprocessing` approach
* zonal majority (http://stackoverflow.com/questions/6252280/find-the-most-frequent-number-in-a-numpy-vector)

## Alternatives

Grass r.stats
R spatialdataframe
starspan
zonal statistics arcpy
QGIS

