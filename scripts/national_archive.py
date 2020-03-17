import os
import glob
import zipfile
import datetime
import warnings
import traceback

import numpy as np
import pandas as pd
import dask.bag as db

import suncal
from suncal import SunNotFoundError


def mkdir(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

    return None


def extract_zip(inzip, path):
    with zipfile.ZipFile(inzip) as zid:
        zid.extractall(path=path)
        namelist = [os.path.join(path, f) for f in zid.namelist()]
    return namelist


def remove(flist):
    for f in flist:
        if f is None:
            continue
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    return None


def buffer(infile):
    try:
        rslt = suncal.sunpos_reflectivity(infile)
    except SunNotFoundError:
        return None

    return rslt


def main():

    return None


if __name__ == "__main__":
    main()
