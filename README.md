# rasterstats

[![Build Status](https://api.travis-ci.org/perrygeo/python-raster-stats.png)](https://api.travis-ci.org/perrygeo/python-raster-stats) [![Coverage Status](https://coveralls.io/repos/perrygeo/python-raster-stats/badge.png)](https://coveralls.io/r/perrygeo/python-raster-stats)

The `rasterstats` python module provides a fast, flexible and robust tool to summarize geospatial raster
datasets based on vector geometries.  

* Raster data support: 
  * Any raster supported by GDAL
  * Support for continuous and categorical
* Vector data support:
  * Points, Lines, Polygon and Multi-* geometries
  * Flexible input formats
      * Any vector layer supported by OGR
      * Python objects that support the [geo_interface](https://gist.github.com/sgillies/2217756)
      * Well-Known Text/Binary (WKT/WKB) geometries
* Command Line interface with CSV output
* Depends on GDAL, Shapely and numpy

## Install
```
sudo apt-get python-numpy python-gdal
pip install rasterstats
```
For more details on installation and dependencies, see documentation.

## Example Usage
Given a polygon vector layer and a digitial elevation model (DEM) raster, calculate the mean elevation of each polygon:

![zones elevation](https://github.com/perrygeo/python-raster-stats/raw/master/docs/img/zones_elevation.png)

```
>>> from rasterstats import raster_stats
>>> stats = raster_stats("tests/data/polygons.shp", "tests/data/elevation.tif")

>>> stats[1].keys()
    ['std', 'count', 'min', 'max', 'sum', 'fid', 'mean']
    
>>> [(f['fid'], f['mean']) for f in stats]
    [(1, 756.6057470703125), (2, 114.660084635416666)]
```

#### Python interface 

In addition to the basic usage above, rasterstats supports other mechanisms of specifying vector geometeries.

It integrates with other python objects that support the geo_interface (e.g. Fiona, Shapely, ArcPy, PyShp, GeoDjango)
```
>>> import fiona
>>>
>>> # an iterable of objects with geo_interface
>>> lyr = fiona.open('/path/to/vector.shp')
>>> features = (x for x in lyr if x['properties']['state'] == 'CT')
>>> raster_stats(features, '/path/to/elevation.tif')
...
>>> 
>>> # a single object with a geo_interface
>>> lyr = fiona.open('/path/to/vector.shp')
>>> raster_stats(lyr.next(), '/path/to/elevation.tif')
...
```

Or by using with geometries in "Well-Known" formats.
```
>>> raster_stats('POINT(-124 42)', '/path/to/elevation.tif')
...
```

Working with categorical rasters (e.g. vegetation map)
```
>>> raster_stats(lyr.next(), '/path/to/vegetation.tif', categorical=True)
...
```

#### Command line interface
```
$ rasterstats --vector /path/to/census_tracts.shp --raster /path/to/elevation.tif
```


## More resources
 * Documentation
 * Examples


## Issues
Find a bug? Report it via github issues: provide smallest possible raster, vector and code to reproduce it

## TODO 
* respects null/no-data values
* unit tests covering edge cases for input datasets
* command line interface which returns csv data and optionally copies over original vector attrs
* support for categorical
* pip installable
* python 2 & 3 support
* buildthedocs OR use some sort of literate programming
* Examples for PyShp, GeoDjango, Fiona, Path to OGR resource, ArcPy (as Ipython notebooks?)
* reproject on the fly using projection metadata
* heavily profiled using a wide range of input data. The resulting heuristics used to automatically configure for optimal performance. Optimzation heuristic for determining global_src_extent - number of features - extent of features - available system memory vs raster_extent
* CLI: pivots for categorical
* support parallel processing on multiple CPUs via the `multiprocessing` approach
* zonal majority... [example](http://stackoverflow.com/questions/6252280/find-the-most-frequent-number-in-a-numpy-vector)

## Alternatives
There are several other packages for different computing environments that provide similar functionality:

* Grass r.stats 
* R spatialdataframe
* starspan
* zonal statistics arcpy
* QGIS
