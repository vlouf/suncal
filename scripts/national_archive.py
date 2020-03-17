import gc
import os
import sys
import glob
import zipfile
import argparse
import datetime
import warnings
import traceback

import crayons
import numpy as np
import pandas as pd
import dask.bag as db

import suncal
from suncal import SunNotFoundError


def buffer(infile):
    try:
        rslt = suncal.sunpos_reflectivity(infile)
    except SunNotFoundError:
        return None

    return rslt


def check_rid():
    indir = f'/g/data/rq0/odim_archive/odim_pvol/{RID}'
    return os.path.exists(indir)


def extract_zip(inzip, path):
    with zipfile.ZipFile(inzip) as zid:
        zid.extractall(path=path)
        namelist = [os.path.join(path, f) for f in zid.namelist()]
    return namelist


def get_radar_archive_file(date):
    datestr = date.strftime('%Y%m%d')
    file = f"/g/data/rq0/odim_archive/odim_pvol/{RID}/{date.year}/vol/{RID}_{datestr}.pvol.zip"
    if not os.path.exists(file):
        return None

    return file


def mkdir(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

    return None


def remove(flist):
    flist = [f for f in flist if f is not None]
    for f in flist:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    return None


def savedata(rslt_list, path):

    df = pd.concat(rslt_list).reset_index()
    dtime = df.time[0].strftime('%Y%m%d')
    year = df.time[0].strftime('%Y')

    path = os.path.join(path, RID)
    mkdir(path)
    path = os.path.join(path, year)
    mkdir(path)

    outfilename = os.path.join(path, f'suncal.{RID}.{dtime}.csv')
    df.to_csv(outfilename)
    print(crayons.green(f'{len(df)} solar hits on {dtime}.'))
    print(crayons.green(f'Results saved in {outfilename}.'))

    return None


def main(date_range):
    for date in date_range:
        zipfile = get_radar_archive_file(date)
        if zipfile is None:
            print(crayons.red(f'No file found for date {date}.'))
            continue

        namelist = extract_zip(zipfile, path=ZIPDIR)
        print(crayons.yellow(f'{len(namelist)} files to process for {date}.'))
        bag = db.from_sequence(namelist).map(buffer)
        rslt = bag.compute()
        rslt = [r for r in rslt if r is not None]

        if len(rslt) == 0:
            print(crayons.red(f'No results for date {date}.'))
        else:
            savedata(rslt, path=OUTPATH)

        # Removing unzipped files, collecting memory garbage.
        remove(namelist)
        del bag
        gc.collect()

    return None


if __name__ == "__main__":
    parser_description = "Solar calibration of radar in the National radar archive."
    parser = argparse.ArgumentParser(description=parser_description)
    parser.add_argument(
        "-r",
        "--rid",
        dest="rid",
        type=int,
        required=True,
        help="Radar ID number.")
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default='/scratch/kl02/vhl548/solar_output/',
        type=str,
        help="Output directory")
    parser.add_argument(
        '-s',
        '--start-date',
        dest='start_date',
        default=None,
        type=str,
        help='Starting date.',
        required=True)
    parser.add_argument(
        '-e',
        '--end-date',
        dest='end_date',
        default=None,
        type=str,
        help='Ending date.',
        required=True)

    args = parser.parse_args()
    RID = f"{args.rid:02}"
    START_DATE = args.start_date
    END_DATE = args.end_date
    OUTPATH = args.output
    ZIPDIR = '/scratch/kl02/vhl548/unzipdir/'

    if not check_rid():
        parser.error('Invalid Radar ID.')
        sys.exit()

    try:
        start = datetime.datetime.strptime(START_DATE, "%Y%m%d")
        end = datetime.datetime.strptime(END_DATE, "%Y%m%d")
        if start > end:
            parser.error('End date older than start date.')
        date_range = [start + datetime.timedelta(days=x) for x in range(0, (end - start).days + 1, )]
    except ValueError:
        parser.error('Invalid dates.')
        sys.exit()

    print(crayons.green(f'Processing sun calibration for radar {RID}.'))
    print(crayons.green(f'Between {START_DATE} and {END_DATE}.'))
    print(crayons.green(f'Data will be saved in {OUTPATH}.'))

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        main(date_range)
