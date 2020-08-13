"""
Model inversions of the daily solar interferences detected.

@title: sunstats
@creator: Valentin Louf
@creator_email: valentin.louf@bom.gov.au
@date: 13/08/2020
"""
import traceback
from math import erf

import numpy as np
import pandas as pd
from scipy.optimize import brentq as uniroot
from sklearn import linear_model
from sklearn.metrics import r2_score


def mad_filter(x, sigma=1.48):
    """
    Filter data using the median absolute deviation (MAD).

    Parameters:
    ==========
    x: ndarray
        Estimator
    sigma: float
        Threshold

    Returns:
    ========
    umad: ndarray
        Median absolute deviation of the estimator x with outliers set to NaN.
    """
    xmed = np.median(x)
    umad = np.abs(x - xmed)
    mad = np.median(umad)
    umad[umad >= sigma * mad] = np.NaN
    return umad


def solar_widths_scan(beamwidth_h, beamwidth_v, dr):
    """
    Calculate the beam effective width. The effective scanning sun image width
    in reception may be estimated from the solution of the transcendental
    equation (cf. section 7.8 in Doviak and Zrnic - 2006):

    Parameters:
    ===========
    beamwidth_h: float
        Azimuthal beamwidth (degree).
    beamwidth_v: float
        Elevation beamwidth (degree).
    dr: float
        Gate spacing in *km*!

    Returns:
    ========
    dx_eff: float
        Effective azimuthal width of the sun
    dy_eff: float
        Effective elevation width of the sun
    """
    a = np.sqrt(4 * np.log(2)) / beamwidth_h
    b = a * (dr / 2)

    # Trascendental equation for estimation of azimuthal width
    rootf = lambda x: erf(a * x + b) - erf(a * x - b) - (2 / np.exp(1)) * erf(b)

    root = uniroot(rootf, 0, 10)
    dx_eff = np.sqrt(4 * np.log(2)) * root
    dy_eff = beamwidth_v

    return dx_eff, dy_eff


def sun_fit_3P(x, y, z, beamwidth=1, dr=0.25):
    """
    Retrieval using the inversion of a theoretical model of the solar power at
    the top of the atmosphere and of the systematic antenna pointing biases in
    azimuth and elevation (x0, y0). The model herein is a three parameters
    linear function. The difference with the 5P function is that the
    sun-antenna convolution width is constant here.

    Parameters:
    ===========
    x: ndarray
        Relative position of the azimuth with respect to the radar as reference
        (Az radar - Az Sun).
    y: ndarray
        Relative position of the elevation with respect to the radar as
        reference (El radar - El Sun).
    z: ndarray
        Measured power of the Sun.
    beamwidth: float
        Angular beamwidth (degree).
    dr: float
        Gate spacing in km.

    Returns:
    ========
    x0: float
        Original target azimuth after model inversion.
    y0: float
        Original target elevation after model inversion.
    p0: float
        Sun interference power after model inversion.
    """
    if len(x) <= 3:
        return None

    dx_eff, dy_eff = solar_widths_scan(beamwidth, beamwidth, dr)
    a1 = -40 * np.log10(2) * (1 / (dx_eff ** 2))
    a2 = -40 * np.log10(2) * (1 / (dy_eff ** 2))

    z = z - a1 * x ** 2 - a2 * y ** 2

    inx = np.array([x.T, y.T, np.ones_like(x).T]).T
    reg = linear_model.LinearRegression()
    reg.fit(inx, z)
    b1, b2, c = reg.coef_
    r_sq = reg.score(inx, z)

    x0 = -b1 / (2 * a1)
    y0 = -b2 / (2 * a2)
    p0 = c - (b1 ** 2) / (4 * a1) - (b2 ** 2) / (4 * a2)

    return x0, y0, p0, r_sq


def sun_fit_5P(x, y, z, beamwidth=1, dr=0.25):
    """
    Retrieval using the inversion of a theoretical model of the solar power at
    the top of the atmosphere and of the systematic antenna pointing biases in
    azimuth and elevation (x0, y0). The model herein is a five parameters
    quadratic function.  The difference with the 3P function is that the
    sun-antenna convolution width is not constant here.

    Parameters:
    ===========
    x: ndarray
        Relative position of the azimuth with respect to the radar as reference
        (Az radar - Az Sun).
    y: ndarray
        Relative position of the elevation with respect to the radar as
        reference (El radar - El Sun).
    z: ndarray
        Measured power of the Sun.
    beamwidth: float
        Angular beamwidth (degree).
    dr: float
        Gate spacing in km.

    Returns:
    ========
    x0: float
        Original target azimuth after model inversion.
    y0: float
        Original target elevation after model inversion.
    p0: float
        Sun interference power after model inversion.
    """
    if len(x) <= 5:
        return None

    inx = np.array([x.T ** 2, y.T ** 2, x.T, y.T, np.ones_like(x).T]).T
    reg = linear_model.LinearRegression()
    reg.fit(inx, z)
    a1, a2, b1, b2, c = np.transpose(reg.coef_)
    r_sq = reg.score(inx, z)

    x0 = -b1 / (2 * a1)
    y0 = -b2 / (2 * a2)
    p0 = c - (b1 ** 2) / (4 * a1) - (b2 ** 2) / (4 * a2)

    return x0, y0, p0, r_sq


def solar_statistics(solar_file, beamwidth=1, dr=0.25, fmin_thld=0.3, do_5P=False):
    try:
        df = pd.read_csv(
            solar_file, 
            parse_dates=['time'], 
            index_col=['time'], 
            usecols=[
                'range',
                'time',
                'sun_azimuth',
                'sun_elevation',
                'radar_elevation',
                'radar_azimuth',
                'fmin',
                'reflectivity',
            ]
        )
    except Exception:
        traceback.print_exc()
        return None
    
    df = df[df.fmin > fmin_thld]
    df['sun_power'] = df.reflectivity - 20 * np.log10(df.range) - 10 * np.log10(0.5) - 2 * 0.017 * df.range / 1e3
    
    # Remove outliers
    mad_val = mad_filter(df['sun_power'])
    df['sun_power'][np.isnan(mad_val)] = np.NaN
    df = df.dropna()

    df['delta_elev'] = df['radar_elevation'] - df['sun_elevation']
    df['delta_azi'] = df['radar_azimuth'] - df['sun_azimuth']    
        
    rslt = {"azi": np.NaN,
            "elev": np.NaN,
            "sun": np.NaN}
    
    if len(df) < 5:
        return None
    
    x = df.delta_azi
    y = df.delta_elev
    z = df.sun_power
    if do_5P:
        rslt['azi_5P'], rslt['elev_5P'], rslt['p0_5P'], rslt['r_sq_5P'] = sun_fit_5P(x, y, z, beamwidth=beamwidth, dr=dr)
        
    rslt['azi'], rslt['elev'], rslt['p0'], rslt['r_sq'] = sun_fit_3P(x, y, z, beamwidth=beamwidth, dr=dr)
    rslt['sun'] = df.sun_power.median()
    rslt['azi_med'] = df.delta_azi.median()
    rslt['elev_med'] = df.delta_elev.median()
    
    return pd.DataFrame(rslt, index=[df.index[0].date()])