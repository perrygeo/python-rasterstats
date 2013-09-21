#!/bin/bash
# Provision base software required for running raster_stats

#apt-get install -y python-software-properties
#add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable

apt-get update

sudo apt-get install -y libgdal-dev gdal-bin \
                   python-gdal python-pip python-numpy \
                   libspatialindex-dev libspatialindex1 \
                   build-essential git atop python-dev \
                   libfreetype6 libfreetype6-dev libpng12-dev screen


cd /usr/local/src/python-raster-stats
sudo pip install --upgrade setuptools
sudo pip install --upgrade shapely pytest coverage tornado jinja2 pyzmq ipython matplotlib
python setup.py develop
