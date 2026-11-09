"""
Radar calibration code using the Sun as reference for position and power.

@title: suncal
@creator: Valentin Louf
@creator_email: valentin.louf@bom.gov.au
@creation: 21/02/2020
@date: 09/11/2026

.. autosummary::
    :toctree: generated/

    SunNotFoundError
    correct_refractivity
    check_sun_in_scope
    get_sunpos_for_location
    sunpos_reflectivity
"""
import itertools
from typing import List, Tuple, Union
import warnings

import h5py
import pyodim
import numpy as np
import pandas as pd
import xarray as xr

from .spa import sunpos

# xarray.DataTree, used by xradar, exists from xarray 2024.10, which needs Python 3.10 or
# later. With older xarray (Python 3.9) it is None, and only ODIM file input is available.
DataTree = getattr(xr, "DataTree", None)


class SunNotFoundError(Exception):
    pass


def _is_datatree(radar) -> bool:
    return DataTree is not None and isinstance(radar, DataTree)


def _reject_unsupported_tree(radar) -> None:
    """Give a clear error for a DataTree this xarray cannot handle (e.g. xarray-datatree on Python 3.9)."""
    if type(radar).__name__ == "DataTree" and not _is_datatree(radar):
        raise TypeError(
            "xradar input needs xarray.DataTree (xarray 2024.10 or later, Python 3.10 or later). "
            f"Got {type(radar).__module__}.{type(radar).__name__}. Pass the ODIM file path instead."
        )


def _sweep_nodes(radar) -> list:
    """Sweep groups of an xradar DataTree, in file order (sweep_0, sweep_1, ...)."""
    nodes = [node for name, node in radar.children.items() if name.startswith("sweep_")]
    if len(nodes) == 0:
        raise ValueError("The DataTree has no sweep_* group.")
    return sorted(nodes, key=lambda node: int(node.name.split("_")[1]))


def _site_from_datatree(radar) -> Tuple[float, float, float]:
    """Radar latitude, longitude and altitude (m) from the root of an xradar DataTree."""
    root = radar.to_dataset()
    site = []
    for name in ("latitude", "longitude", "altitude"):
        if name not in root:
            raise KeyError(f"The DataTree root has no '{name}' variable.")
        site.append(float(root[name].values))
    return tuple(site)


def _sweeps_from_datatree(radar) -> List[Tuple[float, xr.Dataset]]:
    """
    (elevation, sweep) pairs from an xradar DataTree, sorted by elevation like pyodim.

    The elevation is the nominal angle of the sweep (sweep_fixed_angle), which is what
    pyodim gives for ODIM files (where/elangle).
    """
    sweeps = []
    for node in _sweep_nodes(radar):
        sweep = node.to_dataset()
        if "sweep_fixed_angle" in sweep:
            elevation = float(sweep["sweep_fixed_angle"].values)
        else:
            elevation = float(np.nanmedian(sweep["elevation"].values))
        sweeps.append((elevation, sweep))
    return sorted(sweeps, key=lambda pair: pair[0])


def _get_field(sweep: xr.Dataset, name: str) -> np.ndarray:
    if name not in sweep:
        raise KeyError(
            f"No field '{name}' in the radar data. Available fields: {sorted(sweep.data_vars)}. "
            "Note that xradar 0.13 and later name the ODIM quantity TH as DBTH."
        )
    return sweep[name].values


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


def _attr_to_str(value) -> str:
    """ODIM string attributes are read as bytes or str, depending on how the file was written."""
    return value.decode() if isinstance(value, bytes) else str(value)


def check_sun_in_scope(odimfile: Union[str, "xr.DataTree"], zenith_threshold: float) -> bool:
    """
    To save computing time, we check the first timestep only to determine
    if it's worth to look into the dataset or we can skip it.

    Parameters:
    -----------
    odimfile: str or xarray.DataTree
        Input ODIM radar file, or a radar volume opened with xradar
        (Python 3.10 or later).
    zenith_threshold: float
        Maximum elevation angle for to look for the Sun.

    Returns:
    ========
    True/False: bool

    """
    _reject_unsupported_tree(odimfile)
    if _is_datatree(odimfile):
        lat, lon, height = _site_from_datatree(odimfile)
        # End time of each sweep, in file order, as for the ODIM datasets below.
        dates = [pd.Timestamp(pd.to_datetime(node["time"].values).max()) for node in _sweep_nodes(odimfile)]
        dtime = dates[len(dates) // 2]
        return _sun_in_scope(dtime, lat, lon, height, zenith_threshold)

    dates = []
    with h5py.File(odimfile) as odim:
        # Extract volume metadata date and time
        vol_date = _attr_to_str(odim["what"].attrs["date"])
        vol_time = _attr_to_str(odim["what"].attrs["time"])

        lon = odim["where"].attrs["lon"]
        lat = odim["where"].attrs["lat"]
        height = odim["where"].attrs["height"]

        for dt_idx in itertools.count(1):
            if not f"dataset{dt_idx}" in odim:
                break

            # Extract end date and time of each dataset
            dtmp = _attr_to_str(odim[f"dataset{dt_idx}/what"].attrs["enddate"])
            ttmp = _attr_to_str(odim[f"dataset{dt_idx}/what"].attrs["endtime"])
            dates.append(pd.Timestamp(dtmp + ttmp))

    if len(dates) == 0:
        # Time that "should be"
        dtime = pd.Timestamp(vol_date + vol_time)
    else:
        # Half time of the actual acquisition of obs.
        dtime = dates[len(dates) // 2]

    return _sun_in_scope(dtime, lat, lon, height, zenith_threshold)


def _sun_in_scope(dtime: pd.Timestamp, lat: float, lon: float, height: float, zenith_threshold: float) -> bool:
    # Compute Sun's position for given lat/lon and time.
    sun_azimuth, zenith, _, _, _ = sunpos(dtime, lat, lon, height).T
    if (90 - zenith) > (zenith_threshold + 2) or (90 - zenith) < -2:
        return False
    else:
        return True


def get_sunpos_for_location(date: pd.Timestamp, lon: float, lat: float, height: float = 0.) -> Tuple[float, float]:
    """
    Get the solar azimuth and elevation angle for a given datetime (UTC) and
    location (longitude, latitude, and altitude asl).

    Parameters:
    ===========
    date: pd.Timestamp
    lon: float
    lat: float
    height: float

    Returns:
    ========
    sun_azi: float
    zenith: float
    """
    sun_azimuth, obs_el, _, _, _ = sunpos(date, lat, lon, height).T
    zenith = 90 - obs_el
    return sun_azimuth, zenith


def sunpos_reflectivity(
    infile: Union[str, "xr.DataTree"],
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
    infile: str or xarray.DataTree
        Input ODIM radar file, read with pyodim. Or, with Python 3.10 or later,
        a radar volume already opened with xradar, e.g.
        ``xr.open_datatree(file, engine="odim")``. xradar 0.13 and later rename
        the ODIM quantity TH to DBTH: then pass ``refl_name="DBTH"``.
    refl_name: str
        Name of the reflectivity field in the radar file.
    corr_refl_name: str
        Name of the corrected reflectivity field in the radar file.
    zdr_name: str
        Name of the differential reflectivity field in the radar file.
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

    if not check_sun_in_scope(infile, zenith_threshold):
        raise SunNotFoundError("Sun not within scope.")

    # Potential hit from the Sun. Read more.
    if _is_datatree(infile):
        lat, lon, height = _site_from_datatree(infile)
        sweeps = _sweeps_from_datatree(infile)
    else:
        nradar = pyodim.read_odim(infile)
        lat = nradar[0].attrs["latitude"]
        lon = nradar[0].attrs["longitude"]
        height = nradar[0].attrs["height"]
        sweeps = [(radar.elevation.values[0], radar) for radar in nradar]

    return _extract_hits(sweeps, lat, lon, height, refl_name, corr_refl_name, zdr_name, zenith_threshold)


def _extract_hits(
    sweeps: List[Tuple[float, xr.Dataset]],
    lat: float,
    lon: float,
    height: float,
    refl_name: str,
    corr_refl_name: str,
    zdr_name: str,
    zenith_threshold: float,
) -> pd.DataFrame:
    """
    Solar hit selection, common to all input types.

    sweeps: list of (nominal elevation in deg, sweep), each sweep an xarray.Dataset
    with dimensions (azimuth, range) and coordinates azimuth, range (m) and time.
    """
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

    # ZDR is optional: look for it in the first sweep only.
    is_zdr = zdr_name in sweeps[0][1]
    if is_zdr:
        output_keys.append("differential_reflectivity")

    data_dict = dict()
    for k in output_keys:
        data_dict[k] = np.array([])
    data_dict['time'] = []  # Not a numpy array

    # Correct ground-radar elevation from the refraction:
    # Truth = Apparant - refraction angle cf. Holleman (2013)
    count = 0
    for elevation, radar in sweeps:
        elevation = elevation - correct_refractivity(elevation)
        if elevation < 1:
            continue

        dtime = pd.to_datetime(radar.time.values).to_pydatetime().tolist()  # Convert to list of datetime
        sun_azimuth, zenith, _, _, _ = sunpos(dtime, lat, lon, height).T
        zenith = 90 - zenith  # Change coordinates from zenith angle to elevation angle
        if all(zenith > zenith_threshold) or all(zenith < 0):
            continue

        if all(np.abs(elevation - zenith) > 5):
            continue

        reflectivity = _get_field(radar, refl_name)
        zh = _get_field(radar, corr_refl_name)
        if is_zdr:
            zdr = _get_field(radar, zdr_name)

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
                (np.abs((azi2d - sunazi2d + 180) % 360 - 180) < 5)  # Wrap at north.
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
