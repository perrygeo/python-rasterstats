python setup.py sdist --formats=gztar,zip upload
#python setup.py sdist --formats=gztar,zip bdist_wininst upload

echo "Don't forget to publish the docs..."
echo "  cd docs && make zip  # then manually upload via https://pypi.python.org/pypi?%3Aaction=pkg_edit&name=rasterstats"
