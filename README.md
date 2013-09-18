# python-raster-stats

Summary statistics of raster dataset values based on vector geometries.

* Raster data support: 
  * Any continuous raster band supported by GDAL
* Vector data support:
  * OGR layer
* Depends on GDAL, Shapely and numpy

## Quickstart

**Install** with
```
sudo apt-get ?
pip install rasterstats
```
For more details on installation and dependencies, see documentation.

**Usage**
Raster dataset of elevation
(Pic of Raster)

Vector dataset of census tract boundaries (polygons)
(Pic of Vector)

Python interface
```
>>> from rasterstats import raster_stats
>>> stats = raster_stats('/path/to/census_tracts.shp', '/path/to/elevation.tif')
{...}
```

Command line interface
```
$ rasterstats --vector /path/to/census_tracts.shp --raster /path/to/elevation.tif
```


## More Resources
* Documentation
* Examples
* Build status
* Test coverage

## Issues
Find a bug? Report it via github issues: provide smallest possible raster, vector and code to reproduce it

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

