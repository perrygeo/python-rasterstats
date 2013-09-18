#!/bin/bash
# Provision base software required for running raster_stats

#apt-get install -y python-software-properties
#add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable

apt-get update

apt-get install -y libgdal-dev gdal-bin \
                   python-gdal python-pip python-numpy \
                   libspatialindex-dev libspatialindex1 \
                   build-essential git atop python-dev python-dateutil

cd /usr/local/src/python-raster-stats
sudo pip install shapely pytest coverage
python setup.py develop
