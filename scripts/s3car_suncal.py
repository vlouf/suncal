# Python Standard Library
import os
import sys
import glob
import argparse
import datetime
import traceback

# Other libraries.
import dask.bag as db
import suncal
from suncal import SunNotFoundError


def driver(str: infile):
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


def main():
    rid, date = RID, DATE

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
    if len(flist) == 0:
        print(f"No file found for radar {RID} at {DATE}.")
        return None

    print(f"Found {len(flist)} for radar {RID} at {DATE}.")

    bag = db.from_sequence(flist).map(driver)
    rslt = bag.compute()
    rslt = [r for r in rslt if r is not None]
    if len(rslt) == 0:
        print(f"No results for date {date}.")
    else:
        savedata(rslt, path=OUTPUT_DATA_PATH)

    return None


if __name__ == "__main__":
    VOLS_ROOT_PATH = "/srv/data/s3car-server/vols"
    OUTPUT_DATA_PATH = "/srv/data/s3car-server/solar/data"

    parser_description = (
        "Quality control of antenna alignment and receiver calibration using the sun."
    )
    parser = argparse.ArgumentParser(description=parser_description)
    parser.add_argument(
        "-r",
        "--rid",
        dest="rid",
        type=int,
        required=True,
        help="Radar RAPIC ID number."
    )
    parser.add_argument(
        "-d",
        "--date",
        dest="date",
        default=None,
        type=str,
        help="Processing date format YYYYMMDD.",
        required=True,
    )

    args = parser.parse_args()
    RID = args.rid
    DATE = args.date
    try:
        # Check if Date is valid.
        DTIME = datetime.datetime.strptime(DATE, "%Y%m%d")
    except Exception:
        traceback.print_exc()
        sys.exit()

    main()
