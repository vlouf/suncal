import gc
import os
import glob
import zipfile
import argparse
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
    flist = [f for f in flist if f is not None]
    for f in flist:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    return None


def savedata(rslt_list, path):

    df = pd.concat(rslt_list)
    outfilename = os.path.join(path, 'test.csv')
    df.to_csv(outfilename)

    return None


def buffer(infile):
    try:
        rslt = suncal.sunpos_reflectivity(infile)
    except SunNotFoundError:
        return None

    return rslt


def main():
    zipdir = '/scratch/kl02/vhl548/unzipdir/'
    outpath = f'/scratch/kl02/vhl548/solar_output/'

    flist = sorted(glob.glob('/g/data/rq0/odim_archive/odim_pvol/02/2019/vol/*.zip'))

    for zipfile in flist:
        namelist = extract_zip(zipfile, path=zipdir)

        bag = db.from_sequence(namelist).map(buffer)
        rslt = bag.compute()
        rslt = [r for r in rslt if r is not None]

        if not len(rslt) == 0:
            savedata(rslt, path=outpath)

        remove(namelist)
        del bag
        gc.collect()

    return None


if __name__ == "__main__":
    main()
