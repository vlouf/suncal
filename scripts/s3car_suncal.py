"""
Quality control of antenna alignment and receiver calibration using the sun

@creator: Valentin Louf <valentin.louf@bom.gov.au>
@project: s3car-server
@institution: Bureau of Meteorology
@date: 22/02/2021

    buffer
    check_file
    check_reflectivity
    driver
    mkdir
    main
"""
# Python Standard Library
import os
import sys
import glob
import argparse
import warnings
import traceback

# Other libraries.
import netCDF4
import pandas as pd
import dask.bag as db

import suncal
from suncal import SunNotFoundError


def buffer(func):
    """
    Decorator to catch and kill error message.
    """

    def wrapper(*args, **kwargs):
        try:
            rslt = func(*args, **kwargs)
        except OSError:
            print(f"File invalid: {args}.")
            return None
        except Exception:
            traceback.print_exc()
            rslt = None
        return rslt

    return wrapper


@buffer
def check_file(infile: str) -> bool:
    """
    Check if file is empty.

    Parameter:
    ==========
    infile: str
        Input ODIM H5 file.

    Returns:
    ========
        True/False if file is not empty/empty.
    """
    if os.stat(infile).st_size == 0:
        return False
    else:
        return True


@buffer
def check_reflectivity(infile: str) -> bool:
    """
    Check for the presence of the Uncorrected Reflectivity fields in the ODIM
    h5 dataset. By convention the field name is TH.

    Parameter:
    ==========
    infile: str
        Input ODIM H5 file.

    Returns:
    ========
    True/False presence of the uncorrected reflectivity.
    """
    with netCDF4.Dataset(infile) as ncid:
        groups = ncid["/dataset1"].groups.keys()
        var = []
        for group in groups:
            if "data" not in group:
                continue
            name = ncid[f"/dataset1/{group}/what"].getncattr("quantity")
            var.append(name)

    if "TH" in var:
        return True
    else:
        return False


def driver(infile: str) -> pd.DataFrame:
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


def mkdir(path: str) -> None:
    """
    Make directory if it does not already exist.
    """
    try:
        os.mkdir(path)
    except FileExistsError:
        pass
    return None


def main() -> None:
    """
    Structure:
    1/ Create output directories (if does not exists)
    2/ Check if ouput exists (doing nothing if it does).
    3/ Check if input directories exists
    4/ Processing solar calibration
    5/ Saving output data.
    """
    rid, date = RID, DATE

    # Create output directories and check if output file exists
    outpath = os.path.join(OUTPUT_DATA_PATH, str(rid))
    mkdir(outpath)
    outfilename = os.path.join(outpath, f"suncal.{rid}.{date}.csv")
    if os.path.isfile(outfilename):
        print("Output file already exists. Doing nothing.")
        return None

    # Input directory checks.
    input_dir = os.path.join(VOLS_ROOT_PATH, str(rid))
    if not os.path.exists(input_dir):
        print(f"RAPIC ID: {RID} not found in {VOLS_ROOT_PATH}.")
        return None

    input_dir = os.path.join(input_dir, date)
    if not os.path.exists(input_dir):
        print(f"Date: {DATE} not found in {VOLS_ROOT_PATH} for radar {RID}.")
        return None

    input_dir = os.path.join(input_dir, "*.h5")
    flist = sorted(glob.glob(input_dir))
    flist = [f for f in flist if check_file(f)]
    if len(flist) == 0:
        print(f"No file (or all files empty) found for radar {RID} at {DATE}.")
        return None

    goodfiles = [*map(check_reflectivity, flist)]
    if not any(goodfiles):
        print(f"The uncorrected reflectivity field is not present for radar {RID}.")
        return None
    flist = [f for f, g in zip(flist, goodfiles) if g is True]
    print(f"Found {len(flist)} files with the uncorrected reflectivity for radar {RID} for date {DATE}.")

    # Processing - It uses multiprocessing.
    bag = db.from_sequence(flist).map(driver)
    rslt = bag.compute()
    dataframe_list = [r for r in rslt if r is not None]

    if len(dataframe_list) == 0:
        print(f"No results for date {date}.")
        return None
    else:
        # Save the output data into a CSV file
        df = pd.concat(dataframe_list, ignore_index=True)
        df.to_csv(outfilename, float_format="%g")
        print(f"Results saved in {outfilename}.")

    return None


if __name__ == "__main__":
    VOLS_ROOT_PATH: str = "/srv/data/s3car-server/vols"

    parser_description = "Quality control of antenna alignment and receiver calibration using the sun."
    parser = argparse.ArgumentParser(description=parser_description)
    parser.add_argument(
        "-r", "--rid", dest="rid", type=int, required=True, help="Radar RAPIC ID number.",
    )
    parser.add_argument(
        "-d", "--date", dest="date", type=str, help="Value to be converted to Timestamp (str).", required=True,
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output",
        default="/srv/data/s3car-server/solar/data",
        type=str,
        help="Directory for output data.",
    )

    args = parser.parse_args()
    RID = args.rid
    DATE = args.date
    OUTPUT_DATA_PATH = args.output
    try:
        # 2 advantages: check if provided dtime is valid and turns it into a timestamp object.
        DTIME = pd.Timestamp(DATE)
    except Exception:
        traceback.print_exc()
        sys.exit()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        main()
