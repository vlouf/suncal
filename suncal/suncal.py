"""
Radar calibration code using the Sun as reference for position and power.

@title: suncal
@creator: Valentin Louf
@creator_email: valentin.louf@bom.gov.au
@creation: 21/02/2020
@date: 03/08/2022

.. autosummary::
    :toctree: generated/

    SunNotFoundError
    correct_refractivity
    sunpos_reflectivity
"""
import datetime
import warnings

import pyodim
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
        4/3 earth's radius model.

    Returns:
    ========
    refra: float
        Refraction angle in deg.
    """
    θ = np.deg2rad(elevation)
    refra = (k - 1) * np.cos(θ) * (np.sqrt(np.sin(θ) ** 2 + 2 / (k - 1) * (n0 - 1)) - np.sin(θ))
    return np.rad2deg(refra)


def check_sun_in_scope(infile, zenith_threshold):
    """
    To save computing time, we check the first timestep only to determine
    if it's worth to look into the dataset or we can skip it.

    Parameters:
    -----------
    infile: str
        Input radar file. Must be compatible with Py-ART.
    zenith_threshold: float
        Maximum elevation angle for to look for the Sun.

    Returns:
    ========
    True/False: bool

    """
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
        return False
    else:
        return True


def sunpos_reflectivity(
    infile: str,
    refl_name: str = "TH",
    corr_refl_name: str = "DBZH",
    zdr_name: str = "ZDR",
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

    output_keys = [
        "time",
        "range",
        "sun_azimuth",
        "sun_elevation",
        "radar_elevation",
        "radar_azimuth",
        "fmin",
        "reflectivity"
    ]

    if not check_sun_in_scope(infile, zenith_threshold):
        raise SunNotFoundError("Sun not within scope.")

    # Potential hit from the Sun. Read more.
    nradar = pyodim.read_odim(infile, lazy_load=True)
    radar = nradar[0].compute()

    lat = radar.attrs["latitude"]
    lon = radar.attrs["longitude"]
    height = radar.attrs["height"]    

    try:
        zdr = radar[zdr_name].values
        output_keys.append("differential_reflectivity")
        is_zdr = True
    except KeyError:
        is_zdr = False

    data_dict = dict()
    for k in output_keys:
        data_dict[k] = np.array([])
    data_dict['time'] = []  # Not a numpy array

    nradar = [r.compute() for r in nradar]

    # Correct ground-radar elevation from the refraction:
    # Truth = Apparant - refraction angle cf. Holleman (2013)
    count = 0
    for radar in nradar:
        elevation = radar.elevation.values[0]
        elevation = elevation - correct_refractivity(elevation)
        if elevation < 0.9:
            continue
            
        dtime = pd.to_datetime(radar.time).to_pydatetime().tolist()  # Convert to list of datetime
        sun_azimuth, zenith, _, _, _ = sunpos(dtime, lat, lon, height).T
        zenith = 90 - zenith  # Change coordinates from zenith angle to elevation angle
        if all(zenith > zenith_threshold) or all(zenith < 0):
            continue 
            
        if all(np.abs(elevation - zenith) > 5):
            continue

        reflectivity = radar[refl_name].values
        zh = radar[corr_refl_name].values
        if is_zdr:
            zdr = radar[zdr_name].values

        # Ray filling ratio, i.e. number of non-NA gate in ray
        fmin = 1 - np.sum(np.isnan(reflectivity), axis=1) / reflectivity.shape[1]

        # Radar coordinates.
        r = radar.range.values
        azi = radar.azimuth.values % 360  # Corr. for neg azi in case of wrapping.
        dtime = radar.time.values

        R, azi2d = np.meshgrid(r, azi)
        _, time2d = np.meshgrid(r, dtime)
        _, sunazi2d = np.meshgrid(r, sun_azimuth)
        _, zenith2d = np.meshgrid(r, zenith)
        _, fmin2d = np.meshgrid(r, fmin)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pos = (
                (np.abs(azi2d - sunazi2d) < 5)
                & (R > 50e3)
                & (~np.isnan(reflectivity))
                & (reflectivity < 15)
                & (np.isnan(zh) | (zh < 10))
            )

        if np.sum(pos) == 0:
            continue

        count += np.sum(pos)
        elev2d = np.array([elevation] * np.sum(pos))

        [data_dict['time'].append(t) for t in time2d[pos]]
        data_dict['range'] = np.append(data_dict['range'], R[pos])
        data_dict['sun_azimuth'] = np.append(data_dict['sun_azimuth'], sunazi2d[pos])
        data_dict['sun_elevation'] = np.append(data_dict['sun_elevation'], zenith2d[pos])
        data_dict['radar_elevation'] = np.append(data_dict['radar_elevation'], elev2d)
        data_dict['radar_azimuth'] = np.append(data_dict['radar_azimuth'], azi2d[pos])
        data_dict['fmin'] = np.append(data_dict['fmin'], fmin2d[pos])
        data_dict['reflectivity'] = np.append(data_dict['reflectivity'], reflectivity[pos])
        if is_zdr:
            data_dict['differential_reflectivity'] = np.append(data_dict['differential_reflectivity'], zdr[pos])

    if count == 0:
        raise SunNotFoundError("No solar hit found.")

    return pd.DataFrame(data_dict)
