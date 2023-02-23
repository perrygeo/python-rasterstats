#!/usr/bin/env python
# Additional functions to be used in raster stat computation
import numpy as np


def mymean(x):
    return np.ma.mean(x)
