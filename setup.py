import os
import sys
import re
from setuptools import setup
from setuptools.command.test import test as TestCommand


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def get_version():
    vfile = os.path.join(
        os.path.dirname(__file__), "src", "rasterstats", "_version.py")
    with open(vfile, "r") as vfh:
        vline = vfh.read()
    vregex = r"^__version__ = ['\"]([^'\"]*)['\"]"
    match = re.search(vregex, vline, re.M)
    if match:
        return match.group(1)
    else:
        raise RuntimeError("Unable to find version string in {}.".format(vfile))

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name="rasterstats",
    version=get_version(),
    author="Matthew Perry",
    author_email="perrygeo@gmail.com",
    description="Summarize geospatial raster datasets based on vector geometries",
    license="BSD",
    keywords="gis geospatial geographic raster vector zonal statistics",
    url="https://github.com/perrygeo/python-raster-stats",
    package_dir={'': 'src'},
    packages=['rasterstats'],
    long_description=read('README.rst'),
    install_requires=read('requirements.txt').splitlines(),
    tests_require=['pytest', 'pyshp>=1.1.4', 'coverage'],
    cmdclass={'test': PyTest},
    classifiers=[
        "Development Status :: 4 - Beta",
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        "License :: OSI Approved :: BSD License",
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        "Topic :: Utilities",
        'Topic :: Scientific/Engineering :: GIS',
    ],
    entry_points="""
      [rasterio.rio_plugins]
      zonalstats=rasterstats.cli:zonalstats
      pointquery=rasterstats.cli:pointquery
    """)
