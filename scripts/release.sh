rm -rf ~/python-raster-stats/ \
  && cp -r /usr/local/src/python-raster-stats/ ~/python-raster-stats \
  && cd ~/python-raster-stats \
  && python setup.py sdist upload