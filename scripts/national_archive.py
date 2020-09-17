"""
Radar calibration using the Sun as reference. Processing the Australian
National archive.

@creator: Valentin Louf <valentin.louf@bom.gov.au>
@institution: Monash University and Bureau of Meteorology
@date: 10/09/2020

    buffer
    check_rid
    extract_zip
    get_radar_archive_file
    mkdir
    remove
    savedata
    main
"""
import gc
import os
import sys
import glob
import time
import zipfile
import argparse
import datetime
import warnings
import traceback

from typing import List

import crayons
import numpy as np
import pandas as pd
import dask.bag as db

import suncal
from suncal import SunNotFoundError


def buffer(infile: str):
    """
    Buffer function to catch and kill errors about missing Sun hit.

    Parameters:
    ===========
    infile: str
        Input radar file.

    Returns:
    ========
    rslt: pd.DataFrame
        Pandas dataframe with the results from the solar calibration code.
    """
    try:
        rslt = suncal.sunpos_reflectivity(infile)
    except SunNotFoundError:
        return None
    except Exception:
        print(f"Problem with file {infile}.")
        traceback.print_exc()
        return None

    return rslt


def check_rid() -> bool:
    """
    Check if the Radar ID provided exists.
    """
    indir = f"/g/data/rq0/level_1/odim_pvol/{RID:02}"
    return os.path.exists(indir)


def extract_zip(inzip: str, path: str) -> List[str]:
    """
    Extract content of a zipfile inside a given directory.

    Parameters:
    ===========
    inzip: str
        Input zip file.
    path: str
        Output path.

    Returns:
    ========
    namelist: List
        List of files extracted from  the zip.
    """
    with zipfile.ZipFile(inzip) as zid:
        zid.extractall(path=path)
        namelist = [os.path.join(path, f) for f in zid.namelist()]
    return namelist


def get_radar_archive_file(date) -> str:
    """
    Return the archive containing the radar file for a given radar ID and a
    given date.

    Parameters:
    ===========
    date: datetime
        Date.

    Returns:
    ========
    file: str
        Radar archive if it exists at the given date.
    """
    datestr = date.strftime("%Y%m%d")
    file = f"/g/data/rq0/level_1/odim_pvol/{RID:02}/{date.year}/vol/{RID:02}_{datestr}.pvol.zip"

    if not os.path.exists(file):
        return None

    return file


def mkdir(path: str) -> None:
    """
    Create the DIRECTORY(ies), if they do not already exist
    """
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

    return None


def remove(flist: List[str]) -> None:
    """
    Remove file if it exists.
    """
    flist = [f for f in flist if f is not None]
    for f in flist:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    return None


def savedata(rslt_list: List, path: str) -> None:
    """
    Save the output data into a CSV file compatible with pandas.

    Parameters:
    ===========
    rslt_list: list
        List of solar calibration results for the given date.
    path: str
        Output directory.
    """
    df = pd.concat(rslt_list, ignore_index=True)
    dtime = df.time[0].strftime("%Y%m%d")

    path = os.path.join(path, str(RID))
    mkdir(path)

    outfilename = os.path.join(path, f"suncal.{RID}.{dtime}.csv")
    df.to_csv(outfilename, float_format="%g")
    print(crayons.green(f"{len(df)} solar hits on {dtime}."))
    print(crayons.green(f"Results saved in {outfilename}."))

    return None


def main(date_range: List) -> None:
    for date in date_range:
        zipfile = get_radar_archive_file(date)
        if zipfile is None:
            print(crayons.red(f"No file found for date {date}."))
            continue

        namelist = extract_zip(zipfile, path=ZIPDIR)
        print(crayons.yellow(f"{len(namelist)} files to process for {date}."))
        bag = db.from_sequence(namelist).map(buffer)
        rslt = bag.compute()
        rslt = [r for r in rslt if r is not None]

        if len(rslt) == 0:
            print(crayons.red(f"No results for date {date}."))
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
    parser.add_argument("-r", "--rid", dest="rid", type=int, required=True, help="Radar ID number.")
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default="/scratch/kl02/vhl548/solar_output/",
        type=str,
        help="Output directory",
    )
    parser.add_argument(
        "-s",
        "--start-date",
        dest="start_date",
        default=None,
        type=str,
        help="Starting date.",
        required=True,
    )
    parser.add_argument(
        "-e",
        "--end-date",
        dest="end_date",
        default=None,
        type=str,
        help="Ending date.",
        required=True,
    )

    args = parser.parse_args()
    RID = args.rid
    START_DATE = args.start_date
    END_DATE = args.end_date
    OUTPATH = args.output
    ZIPDIR = "/scratch/kl02/vhl548/unzipdir_solar/"

    if not check_rid():
        parser.error("Invalid Radar ID.")
        sys.exit()

    try:
        start = datetime.datetime.strptime(START_DATE, "%Y%m%d")
        end = datetime.datetime.strptime(END_DATE, "%Y%m%d")
        if start > end:
            parser.error("End date older than start date.")
        date_range = [start + datetime.timedelta(days=x) for x in range(0, (end - start).days + 1,)]
    except ValueError:
        parser.error("Invalid dates.")
        sys.exit()

    print(crayons.green(f"Processing sun calibration for radar {RID}."))
    print(crayons.green(f"Between {START_DATE} and {END_DATE}."))
    print(crayons.green(f"Data will be saved in {OUTPATH}."))

    tick = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        main(date_range)
    tock = time.time()
    print(crayons.magenta(f"Process finished in {tock - tick:0.2}s."))
