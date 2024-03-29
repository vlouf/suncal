"""
Radar calibration code using the Sun as reference for position and power.

@title: suncal
@creator: Valentin Louf
@creator_email: valentin.louf@bom.gov.au
@creation: 21/02/2020
@date: 09/10/2020

.. autosummary::
    :toctree: generated/

    SunNotFoundError
    correct_refractivity
    sunpos_reflectivity
"""
import datetime
import warnings
import traceback

import pyart
import cftime
import netCDF4
import numpy as np
import pandas as pd

from .spa import sunpos


class SunNotFoundError(Exception):
    pass


def correct_refractivity(elevation: float, n0: float = 1.000313, k: float = 5 / 4) -> float:
    """
    Atmospheric refraction correction. Eq. 9 and 10 from Holleman and Huuskonen
    (2013) 10.1002/rds.20030.

    Parameters:
    ===========
    elevation: float
        Elevation angle in deg.
    n0: float
        Reflective index of air.
    k: float
        4/3 earth’s radius model.

    Returns:
    ========
    refra: float
        Refraction angle in deg.
    """
    θ = np.deg2rad(elevation)
    refra = (k - 1) * np.cos(θ) * (np.sqrt(np.sin(θ) ** 2 + 2 / (k - 1) * (n0 - 1)) - np.sin(θ))
    return np.rad2deg(refra)


def sunpos_reflectivity(
    infile: str,
    refl_name: str = "total_power",
    corr_refl_name: str = "reflectivity",
    zdr_name: str = "differential_reflectivity",
    zenith_threshold: float = 10,
) -> pd.DataFrame:
    """
    Extract Sun's reflectivity and radar azimuth/elevation angles of the solar
    hit. Will try to extract differential reflectivity too if it exists.

    Parameters:
    -----------
    infile: str
        Input radar file. Must be compatible with Py-ART.
    zenith_threshold: float
        Maximum elevation angle for to look for the Sun.    

    Returns:
    --------
    data_sun: pandas.core.frame.DataFrame
        Columns -> [sun_azimuth, sun_elevation, radar_elevation, radar_azimuth,
        reflectivity]
    """
    if zenith_threshold <= 0:
        raise ValueError("Can not see the Sun at night.")
    if zenith_threshold > 90:
        raise ValueError("Living in Uranus?")

    # To save computing time, we check the first timestep only to determine
    # if it's worth to look into the dataset or we can skip it.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with netCDF4.Dataset(infile) as ncid:
            lon = ncid["where"].lon
            lat = ncid["where"].lat
            try:
                height = ncid["where"].height
            except Exception:
                height = 0

            strtime = ncid["dataset1"]["what"].startdate + ncid["dataset1"]["what"].starttime
            dtime = datetime.datetime.strptime(strtime, "%Y%m%d%H%M%S")

    # Compute Sun's position for given lat/lon and time.
    sun_azimuth, zenith, _, _, _ = sunpos(dtime, lat, lon, height).T
    if (90 - zenith) > (zenith_threshold + 2) or (90 - zenith) < -2:
        raise SunNotFoundError("Sun not within scope.")

    # Potential hit from the Sun. Read the whole volume now.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            radar = pyart.aux_io.read_odim_h5(infile)
        except Exception:
            traceback.print_exc()
            return None

    dtime = cftime.num2pydate(radar.time["data"], radar.time["units"])
    lat = radar.latitude["data"]
    lon = radar.longitude["data"]
    if height == 0:
        try:
            height = radar.altitude_agl["data"]
        except TypeError:
            height = 0

    sun_azimuth, zenith, _, _, _ = sunpos(dtime, lat, lon, height).T
    zenith = 90 - zenith  # Change coordinates from zenith angle to elevation angle
    if all(zenith > zenith_threshold) or all(zenith < 0):
        raise SunNotFoundError("Sun not within scope.")

    # Correct ground-radar elevation from the refraction:
    # Truth = Apparant - refraction angle cf. Holleman (2013)
    elevation = radar.elevation["data"] - correct_refractivity(radar.elevation["data"])

    reflectivity = radar.fields[refl_name]["data"].filled(np.NaN)
    zh = radar.fields[corr_refl_name]["data"].filled(np.NaN)
    try:
        zdr = radar.fields[zdr_name]["data"]
        is_zdr = True
    except KeyError:
        is_zdr = False

    # Ray filling ratio, i.e. number of non-NA gate in ray
    fmin = 1 - np.sum(np.isnan(reflectivity), axis=1) / reflectivity.shape[1]

    # Radar coordinates.
    r = radar.range["data"]
    radar_azimuth_total = radar.azimuth["data"] % 360  # Corr. for neg azi in case of wrapping.
    R, azi2d = np.meshgrid(r, radar_azimuth_total)
    _, time2d = np.meshgrid(r, dtime)
    _, elev2d = np.meshgrid(r, elevation)
    _, zenith2d = np.meshgrid(r, zenith)
    _, sunazi2d = np.meshgrid(r, sun_azimuth)
    _, fmin2d = np.meshgrid(r, fmin)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pos = (
            (np.abs(azi2d - sunazi2d) < 5)
            & (np.abs(elev2d - zenith2d) < 5)
            & (R > 50e3)
            & (elev2d > 0.9)
            & (~np.isnan(reflectivity))
            & (reflectivity < 15)
            & (np.isnan(zh) | (zh < 10))
        )

    if np.sum(pos) == 0:
        raise SunNotFoundError("No solar hit found.")

    data_dict = {
        "time": time2d[pos],
        "range": R[pos],
        "sun_azimuth": sunazi2d[pos],
        "sun_elevation": zenith2d[pos],
        "radar_elevation": elev2d[pos],
        "radar_azimuth": azi2d[pos],
        "fmin": fmin2d[pos],
        "reflectivity": reflectivity[pos],
    }
    if is_zdr:
        data_dict.update({"differential_reflectivity": zdr[pos]})

    return pd.DataFrame(data_dict)
