from math import erf

import numpy as np
from scipy.optimize import brentq as uniroot
from sklearn import linear_model
from sklearn.metrics import r2_score


def mad(x):
    xmed = np.median(x)
    umad = np.abs(x - xmed)
    mad = np.median(umad)
    umad[umad >= 1.48 * mad] = np.NaN
    return umad


def solar_widths_scan(beamwidth_h, beamwidth_v, dr):
    a = np.sqrt(4 * np.log(2)) / beamwidth_h
    b = a * (dr / 2)

    # Trascendental equation for estimation of azimuthal width
    rootf = lambda x: erf(a * x + b) - erf(a * x - b) - (2 / np.exp(1)) * erf(b)

    root = uniroot(rootf, 0, 10)
    dx_eff = np.sqrt(4 * np.log(2)) * root
    dy_eff = beamwidth_v

    return dx_eff, dy_eff


def sun_fit_3P(df, beamwidth=1, dr=0.25)    :
    if len(df) <= 3:
        return None
    dx_eff, dy_eff = solar_widths_scan(beamwidth, beamwidth, dr)
    a1 = - 40 * np.log10(2) * (1 / (dx_eff ** 2))
    a2 = - 40 * np.log10(2) * (1 / (dy_eff ** 2))

    x = df.delta_azi
    y = df.delta_elev
    z = df.sun_power
    z = z - a1 * x ** 2 - a2 * y ** 2

    inx = np.array([x.T, y.T, np.ones_like(x).T]).T
    reg = linear_model.LinearRegression()
    reg.fit(inx, z)
    b1, b2, c = reg.coef_
    r_sq = reg.score(inx, z)

    x0 = -b1 / (2 * a1)
    y0 = -b2 / (2 * a2)
    p0 = c - (b1 ** 2)/(4*a1) - (b2 ** 2)/(4*a2)

    return x0, y0, p0, r_sq


def sun_fit_5P(df, beamwidth=1, dr=0.25)    :
    if len(df) <= 5:
        return None

    x = df.delta_azi
    y = df.delta_elev
    z = df.sun_power

    inx = np.array([x.T ** 2, y.T ** 2, x.T, y.T, np.ones_like(x).T]).T
    reg = linear_model.LinearRegression()
    reg.fit(inx, z)
    a1, a2, b1, b2, c = np.transpose(reg.coef_)
    r_sq = reg.score(inx, z)

    x0 = -b1 / (2 * a1)
    y0 = -b2 / (2 * a2)
    p0 = c - (b1 ** 2)/(4*a1) - (b2 ** 2)/(4*a2)

    return x0, y0, p0, r_sq