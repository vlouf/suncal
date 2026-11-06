"""
Tests of the solar model inversion. Synthetic data with a known answer test that the
retrieval is correct; the real daily file guards against unintended changes.
"""
from math import erf, exp, log, sqrt

import numpy as np
import pandas as pd
import pytest
import suncal
from suncal import sunstats

BEAMWIDTH = 1.0
DR = 0.25
RANGE_M = 100e3
TRUE_AZI = 0.3
TRUE_ELEV = -0.2
TRUE_POWER = -85.0


def solar_power(x, y):
    """Power of the Sun in the 3P model, peaking at (TRUE_AZI, TRUE_ELEV)."""
    dx_eff, dy_eff = sunstats.solar_widths_scan(BEAMWIDTH, BEAMWIDTH, DR)
    a1 = -40 * np.log10(2) / dx_eff ** 2
    a2 = -40 * np.log10(2) / dy_eff ** 2
    return TRUE_POWER + a1 * (x - TRUE_AZI) ** 2 + a2 * (y - TRUE_ELEV) ** 2


@pytest.fixture
def scan():
    x, y = np.meshgrid(np.linspace(-1.5, 1.5, 13), np.linspace(-1.2, 1.2, 11))
    x, y = x.ravel(), y.ravel()
    return x, y, solar_power(x, y)


def write_hits(path, x, y, power, band_attenuation=0.019, fmin=0.9):
    """Write the CSV sunpos_reflectivity would produce for this power at the Sun."""
    reflectivity = power + 20 * np.log10(RANGE_M) + 10 * np.log10(0.5) + 2 * band_attenuation * RANGE_M / 1e3
    pd.DataFrame(
        {
            "time": pd.date_range("2024-02-15", periods=len(x), freq="min"),
            "range": RANGE_M,
            "sun_azimuth": 100.0,
            "sun_elevation": 5.0,
            "radar_elevation": 5.0 - y,
            "radar_azimuth": 100.0 - x,
            "fmin": fmin,
            "reflectivity": reflectivity,
        }
    ).to_csv(path, index=False)
    return str(path)


@pytest.fixture
def hits_csv(tmp_path, scan):
    return write_hits(tmp_path / "hits.csv", *scan)


def test_mad_filter():
    # median 3, deviations [2, 1, 0, 1, 97], MAD 1, threshold 1.48.
    result = sunstats.mad_filter(np.array([1.0, 2.0, 3.0, 4.0, 100.0]))
    np.testing.assert_array_equal(result, [np.nan, 1, 0, 1, np.nan])


def test_solar_widths_scan_solves_the_transcendental_equation():
    dx_eff, dy_eff = sunstats.solar_widths_scan(BEAMWIDTH, 0.9, DR)
    a = sqrt(4 * log(2)) / BEAMWIDTH
    b = a * DR / 2
    root = dx_eff / sqrt(4 * log(2))
    assert erf(a * root + b) - erf(a * root - b) == pytest.approx(2 / exp(1) * erf(b))
    assert dy_eff == 0.9


@pytest.mark.parametrize("fit", [sunstats.sun_fit_3P, sunstats.sun_fit_5P], ids=["3P", "5P"])
def test_fit_recovers_pointing_offset(fit, scan):
    x0, y0, _, r_sq = fit(*scan, beamwidth=BEAMWIDTH, dr=DR)
    assert x0 == pytest.approx(TRUE_AZI)
    assert y0 == pytest.approx(TRUE_ELEV)
    assert r_sq == pytest.approx(1)


@pytest.mark.parametrize("fit", [sunstats.sun_fit_3P, sunstats.sun_fit_5P], ids=["3P", "5P"])
def test_fit_recovers_sun_power(fit, scan):
    _, _, p0, _ = fit(*scan, beamwidth=BEAMWIDTH, dr=DR)
    assert p0 == pytest.approx(TRUE_POWER)


def test_solar_statistics_recovers_sun_power(hits_csv):
    stats = suncal.solar_statistics(hits_csv, BEAMWIDTH, DR, do_5P=True).iloc[0]
    assert stats["p0"] == pytest.approx(TRUE_POWER)
    assert stats["p0_5P"] == pytest.approx(TRUE_POWER)


@pytest.mark.parametrize("fit, size", [(sunstats.sun_fit_3P, 3), (sunstats.sun_fit_5P, 5)], ids=["3P", "5P"])
def test_fit_needs_enough_points(fit, size):
    assert fit(np.ones(size), np.ones(size), np.ones(size)) is None


def test_solar_statistics_recovers_pointing_offset(hits_csv):
    stats = suncal.solar_statistics(hits_csv, BEAMWIDTH, DR)
    assert stats["azi"].iloc[0] == pytest.approx(TRUE_AZI)
    assert stats["elev"].iloc[0] == pytest.approx(TRUE_ELEV)
    assert stats["r_sq"].iloc[0] == pytest.approx(1)
    assert stats.index[0] == pd.Timestamp("2024-02-15").date()


def test_solar_statistics_5p_adds_its_own_results(hits_csv):
    stats = suncal.solar_statistics(hits_csv, BEAMWIDTH, DR, do_5P=True)
    assert stats["azi_5P"].iloc[0] == pytest.approx(TRUE_AZI)
    assert stats["elev_5P"].iloc[0] == pytest.approx(TRUE_ELEV)


def test_solar_statistics_power_removes_range_and_attenuation(tmp_path):
    # A small symmetric spread around the power, so the median must be that power.
    # Exactly constant would give a MAD of 0, which the filter treats as all outliers.
    x, y = np.meshgrid(np.linspace(-1, 1, 5), np.linspace(-1, 1, 5))
    power = TRUE_POWER + np.linspace(-0.01, 0.01, x.size)
    path = write_hits(tmp_path / "flat.csv", x.ravel(), y.ravel(), power)
    assert suncal.solar_statistics(path, band="C")["sun"].iloc[0] == pytest.approx(TRUE_POWER, abs=0.01)


def test_solar_statistics_band_sets_attenuation(hits_csv):
    # 2 * (0.019 - 0.016) dB/km * 100 km of difference in the two-way path correction.
    c_band = suncal.solar_statistics(hits_csv, band="C")["sun"].iloc[0]
    s_band = suncal.solar_statistics(hits_csv, band="S")["sun"].iloc[0]
    assert s_band - c_band == pytest.approx(0.6)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")  # Median of the emptied data.
def test_solar_statistics_removes_rays_below_fmin(tmp_path, scan):
    path = write_hits(tmp_path / "low.csv", *scan, fmin=0.2)
    assert suncal.solar_statistics(path, fmin_thld=0.3) is None
    assert suncal.solar_statistics(path, fmin_thld=0.1) is not None


def test_solar_statistics_needs_enough_hits(tmp_path, scan):
    x, y, power = scan
    path = write_hits(tmp_path / "few.csv", x[:4], y[:4], power[:4])
    assert suncal.solar_statistics(path) is None


def test_solar_statistics_reads_plain_and_gzipped_csv(tmp_path, solar_csv):
    plain = tmp_path / "hits.csv"
    pd.read_csv(solar_csv).to_csv(plain, index=False)
    pd.testing.assert_frame_equal(suncal.solar_statistics(str(plain), fmin_thld=0.1), suncal.solar_statistics(solar_csv, fmin_thld=0.1))


def test_solar_statistics_returns_none_for_a_missing_file(tmp_path, capsys):
    assert suncal.solar_statistics(str(tmp_path / "missing.csv")) is None
    assert "FileNotFoundError" in capsys.readouterr().err


def test_solar_statistics_regression_on_real_data(solar_csv):
    stats = suncal.solar_statistics(solar_csv, 0.98, fmin_thld=0.1, band="S").iloc[0]
    assert stats["azi"] == pytest.approx(-0.116790, abs=1e-4)
    assert stats["elev"] == pytest.approx(-0.041515, abs=1e-4)
    assert stats["sun"] == pytest.approx(-93.765711, abs=1e-4)
    assert stats["azi_med"] == pytest.approx(-0.153, abs=1e-4)
    assert stats["elev_med"] == pytest.approx(-0.06006, abs=1e-4)


def test_solar_statistics_5p_with_few_hits_gives_nan(tmp_path):
    # 7 rows leave exactly 5 after the MAD filter: enough for 3P, too few for 5P.
    size = 7
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2024-02-15", periods=size, freq="min"),
            "range": 100e3,
            "sun_azimuth": 100.0,
            "sun_elevation": 5.0,
            "radar_elevation": 5.0 + np.arange(size) * 0.1,
            "radar_azimuth": 100.0 + np.arange(size) * 0.1,
            "fmin": 0.9,
            "reflectivity": 5 + np.arange(size) * 0.01,
        }
    )
    path = tmp_path / "few.csv"
    frame.to_csv(path, index=False)
    stats = suncal.solar_statistics(str(path), do_5P=True).iloc[0]
    assert np.isnan(stats[["azi_5P", "elev_5P", "p0_5P", "r_sq_5P"]].astype(float)).all()
    assert np.isfinite(stats[["azi", "elev"]].astype(float)).all()


def test_solar_statistics_wraps_azimuth_around_north(tmp_path):
    rng = np.random.default_rng(0)
    size = 60
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2024-06-21", periods=size, freq="min"),
            "range": 100e3,
            "sun_azimuth": 0.2,
            "sun_elevation": 5.0,
            "radar_elevation": 5.0 + rng.uniform(-1, 1, size),
            "radar_azimuth": rng.uniform(-2, 2, size) % 360,
            "fmin": 0.9,
            "reflectivity": 5 + rng.normal(0, 0.3, size),
        }
    )
    path = tmp_path / "north.csv"
    frame.to_csv(path, index=False)
    stats = suncal.solar_statistics(str(path)).iloc[0]
    assert abs(stats["azi"]) < 5
    assert abs(stats["azi_med"]) < 5
