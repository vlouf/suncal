import datetime

import pyart
import netCDF4
import numpy as np
import pandas as pd
import xarray as xr

from .spa import sunpos


class SunNotFoundError(Exception):
    pass


def corr_elev_refra(theta, n0=1.0004, k=4/3):
    '''
    Atmospheric refraction correction.

    Parameters:
    ===========
    theta: float
        Elevation angle
    n0: float
        Reflective index of air.
    k: float
        4/3 earth’s radius model (Doviak and Zrnic)

    Returns:
    ========
    refra: float
        Refraction corrected elevation angle.
    '''
    refra = ((k - 1) / (2 * k - 1) * np.cos(theta)
            * (np.sqrt(np.sin(theta) ** 2 + (4 * k - 2) / (k - 1) * (n0 - 1))
            - np.sin(theta)))
    return refra


def get_solar_reflectivity(infile, 
                           refl_name='total_power', 
                           corr_refl_name='reflectivity', 
                           zdr_name='differential_reflectivity', 
                           zenith_threshold=10, 
                           min_gate_altitude=1500, 
                           max_gate_altitude=20000):
    '''
    Extract Sun's reflectivity and radar azimuth/elevation angles of the solar hit.

    Parameters:
    -----------
    infile: str
        Input radar file. Must be compatible with Py-ART.
    zenith_threshold: int
        Maximum elevation angle for to look for the Sun.
    min_gate_altitude: int
        Minimum altitude in meters for radar gate. Too small maybe contaminated with ground clutter.

    Returns:
    --------
    data_sun: pandas.core.frame.DataFrame
        Columns -> [sun_azimuth, sun_elevation, radar_elevation, radar_azimuth, reflectivity]
    '''
    if zenith_threshold <= 0:
        raise ValueError('Can not see the Sun at night.')
    if zenith_threshold > 90:
        raise ValueError('Living in Uranus?')

    # To save computing time, we check the first timestep only to determine 
    # if it's worth to look into the dataset or we can skip it.
    with netCDF4.Dataset(infile) as ncid:
        lon = ncid['where'].lon
        lat = ncid['where'].lat
        try:
            height = ncid['where'].height
        except Exception:
            height = 0

        strtime = ncid['dataset1']['what'].startdate + ncid['dataset1']['what'].starttime
        dtime = datetime.datetime.strptime(strtime, '%Y%m%d%H%M%S')

    # Compute Sun's position for given lat/lon and time.
    sun_azimuth, zenith, _, _, _ = sunpos(dtime, lat, lon, height).T
    if (90 - zenith) > (zenith_threshold + 2) or (90 - zenith) < -2:
        raise SunNotFoundError('Sun not within scope.')

    # Potential hit from the Sun. Read the whole volume now.
    radar = pyart.aux_io.read_odim_h5(infile, delay_field_loading='True')
    dtime = netCDF4.num2date(radar.time['data'], radar.time['units'])
    lat = radar.latitude['data']
    lon = radar.longitude['data']
    if height == 0:
        try:
            height = radar.altitude_agl['data']
        except TypeError:
            height = 0

    sun_azimuth, zenith, _, _, _ = sunpos(dtime, lat, lon, height).T
    zenith = 90 - zenith  # Change coordinates from zenith angle to elevation angle
    if all(zenith > zenith_threshold) or all(zenith < 0):
        raise SunNotFoundError('Sun not within scope.')

    # Radar Elevation.
    theta = np.deg2rad(radar.elevation['data'])
    refra_angle = corr_elev_refra(theta)        
    elevation = radar.elevation['data'] + np.rad2deg(refra_angle)
    # Radar coordinates.
    r = radar.range['data']         
    radar_azimuth_total = radar.azimuth['data'] % 360  # Corr. for neg azi in case of wrapping.
    R, azi2d = np.meshgrid(r, radar_azimuth_total)
    _, time2d = np.meshgrid(r, dtime)
    _, elev2d = np.meshgrid(r, elevation)
    _, zenith2d = np.meshgrid(r, zenith)
    _, sunazi2d = np.meshgrid(r, sun_azimuth)
    altitude = radar.gate_z['data']
    
    reflectivity = radar.fields[refl_name]['data'].filled(np.NaN)
    zh = radar.fields[corr_refl_name]['data']
    try:
        zdr = radar.fields[zdr_name]['data']
        is_zdr = True
    except KeyError:
        is_zdr = False

    pos = ((np.abs(azi2d - sunazi2d) < 5) & 
           (np.abs(elev2d - zenith2d) < 5) &    
           (R > 75e3) &
           (elev2d > 0.5) &
           (~np.isnan(reflectivity)) &
           (reflectivity < 15) & 
           (zh < 10))
    
    if np.sum(pos) == 0:
        raise SunNotFoundError('No solar hit found.')
    
    data_dict = {'time': time2d[pos],
                 'range': R[pos],
                 'sun_azimuth': sunazi2d[pos],
                 'sun_elevation': zenith2d[pos],
                 'radar_elevation': elev2d[pos],
                 'radar_azimuth': azi2d[pos],
                 'reflectivity': reflectivity[pos]}    
    if is_zdr:
        data_dict.update({'differential_reflectivity': zdr[pos]})    

    return pd.DataFrame(data_dict)