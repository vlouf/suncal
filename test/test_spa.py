"""
Sun position tests.

The reference is the worked example in Reda & Andreas (2004), table A5.1:
2003-10-17 19:30:30 UTC at 39.742476 N, 105.1786 W, 1830.14 m, delta_t = 67 s.
spa.py disables the refraction correction on purpose (commit b91f9d0), so the
matching zenith is the published one without refraction: 90 - e0.
"""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
import suncal
from suncal import spa
from suncal.spa import _sp

NREL_TIME = datetime(2003, 10, 17, 19, 30, 30)
NREL_SITE = {"latitude": 39.742476, "longitude": -105.1786, "elevation": 1830.14, "delta_t": 67}
NREL_JD = 2452930.3128472222  # Published rounded to 2452930.312847.
NREL_JME = (NREL_JD + 67 / 86400 - 2451545) / 36525 / 10
NREL_JCE = NREL_JME * 10
NREL_HOUR_ANGLE = 11.106271  # From pvlib.


def test_julian_day():
    assert spa.julian_day(NREL_TIME) == pytest.approx(NREL_JD, abs=1e-6)


def test_julian_day_in_january_uses_previous_year():
    # Calendar rule from the paper: months 1 and 2 count as months 13 and 14.
    assert spa.julian_day(datetime(2000, 1, 1, 12)) == pytest.approx(2451545.0)


# Distant dates give the small high-order terms enough weight to expose a wrong
# coefficient in the tables. References: the paper, then pvlib heliocentric functions.
@pytest.mark.parametrize(
    "jme, longitude, latitude, radius",
    [
        (NREL_JME, 24.0182616917, -0.0001011219, 0.9965422974),
        (-0.5, 96.70165821895353, -0.00011721223349416789, 0.9830809153684166),
        (0.1, 101.11778837033489, -4.6567354305626535e-05, 0.9833514232031083),
        (1.0, 107.8016352939303, 4.83123723449195e-05, 0.9840770596364686),
    ],
    ids=["published-example", "year-1500", "year-2100", "year-3000"],
)
def test_heliocentric_position(jme, longitude, latitude, radius):
    result = _sp.heliocentric_position(jme)
    assert result[0] == pytest.approx(longitude, abs=1e-9)
    assert (result[1] + 180) % 360 - 180 == pytest.approx(latitude, abs=1e-9)
    assert result[2] == pytest.approx(radius, abs=1e-9)


def test_nutation_and_obliquity():
    delta_psi, epsilon = _sp.nutation_obliquity(NREL_JCE)
    assert delta_psi == pytest.approx(-0.00399840, abs=1e-6)
    assert epsilon == pytest.approx(23.440465, abs=1e-5)


def test_sunpos_matches_published_example():
    azimuth, zenith, right_ascension, declination, hour_angle = spa.sunpos(NREL_TIME, **NREL_SITE)
    assert azimuth == pytest.approx(194.340241, abs=1e-5)
    assert zenith == pytest.approx(50.127954, abs=1e-5)
    assert right_ascension == pytest.approx(202.22704, abs=1e-5)
    assert declination == pytest.approx(-9.316179, abs=1e-5)
    assert hour_angle % 360 == pytest.approx(NREL_HOUR_ANGLE, abs=1e-5)


def test_topocentric_sunpos_matches_published_example():
    right_ascension, declination, hour_angle = spa.topocentric_sunpos(NREL_TIME, **NREL_SITE)
    assert right_ascension == pytest.approx(202.22704, abs=1e-5)
    assert declination == pytest.approx(-9.316179, abs=1e-5)
    assert hour_angle % 360 == pytest.approx(NREL_HOUR_ANGLE, abs=1e-5)


# Independent reference: pvlib spa_python, delta_t = 0, without refraction.
@pytest.mark.parametrize(
    "when, latitude, longitude, height, azimuth, elevation",
    [
        ("2026-11-05 08:17:03", -37.85200119018555, 144.75199890136722, 44.0, 255.641360, 7.170232),
    ],
    ids=["melbourne"],
)
def test_sunpos_matches_pvlib(when, latitude, longitude, height, azimuth, elevation):
    result = spa.sunpos(pd.Timestamp(when), latitude, longitude, height)
    assert result[0] == pytest.approx(azimuth, abs=1e-4)
    assert 90 - result[1] == pytest.approx(elevation, abs=1e-4)


def test_sunpos_broadcasts_times():
    times = [datetime(2026, 11, 5, hour) for hour in (2, 8)]
    positions = spa.sunpos(times, -37.85, 144.75, 44.0)
    assert positions.shape == (2, 5)
    np.testing.assert_allclose(positions[1], spa.sunpos(times[1], -37.85, 144.75, 44.0))


def test_sunpos_accepts_timestamps():
    moment = datetime(2026, 11, 5, 8, 17, 3)
    timestamp = moment.replace(tzinfo=timezone.utc).timestamp()
    np.testing.assert_allclose(spa.sunpos(timestamp, -37.85, 144.75, 44.0), spa.sunpos(moment, -37.85, 144.75, 44.0))


@pytest.mark.parametrize(
    "when, is_daytime",
    [("2026-11-05 02:00", True), ("2026-11-05 14:00", False)],
    ids=["melbourne-midday", "melbourne-midnight"],
)
def test_sun_is_above_the_horizon_only_during_the_day(when, is_daytime):
    _, zenith, *_ = spa.sunpos(pd.Timestamp(when), -37.85, 144.75, 44.0)
    assert bool(zenith < 90) is is_daytime


def test_get_sunpos_for_location_returns_elevation():
    # Named "zenith" in the code, but the value returned is the elevation angle.
    when = pd.Timestamp("2026-11-05 08:17:03")
    azimuth, elevation = suncal.get_sunpos_for_location(when, 144.75199890136722, -37.85200119018555, 44.0)
    # Independent reference: pvlib spa_python (azimuth 255.6414, elevation 7.1702).
    assert azimuth == pytest.approx(255.6414, abs=1e-3)
    assert elevation == pytest.approx(7.1702, abs=1e-3)


@pytest.mark.parametrize(
    "p0, p1, expected",
    [((0, 45), (0, 45), 0), ((0, 0), (0, 90), 90), ((0, 90), (90, 90), 90), ((0, 90), (180, 90), 180), ((90, 0), (0, 0), 0)],
    ids=["same-point", "zenith-to-horizon", "quarter-of-horizon", "opposite-on-horizon", "azimuth-is-moot-at-zenith"],
)
def test_arcdist(p0, p1, expected):
    # Points are (azimuth, zenith angle), in degrees.
    assert spa.arcdist(p0, p1) == pytest.approx(expected)
