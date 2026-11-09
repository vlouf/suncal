"""
Tests of the optional xradar input (xarray.DataTree), on the same ODIM volume as
test_suncal.py.

xradar support needs Python 3.10 or later. These tests are skipped on Python 3.9, where
xradar is not installed. They skip on the Python version, not on whether xradar imports,
so that a broken xradar install on Python 3.10+ fails instead of being skipped.
"""
import sys

import h5py
import numpy as np
import pandas as pd
import pytest
import suncal

needs_xradar = pytest.mark.skipif(sys.version_info < (3, 10), reason="xradar support requires Python 3.10+")

# Sorting key to compare hits from pyodim and xradar: the two readers order rays and
# sweeps differently.
HIT_KEY = ["radar_elevation", "radar_azimuth", "range"]


def open_tree(path):
    """Open an ODIM file with xradar, whatever its version."""
    import xarray as xr
    import xradar

    try:
        return xr.open_datatree(path, engine="odim")  # xradar 0.13 and later
    except NotImplementedError:
        return xradar.io.open_odim_datatree(path)


def th_name(tree):
    """xradar 0.13 and later rename the ODIM quantity TH to DBTH."""
    return "DBTH" if "DBTH" in tree["sweep_0"].to_dataset() else "TH"


@pytest.fixture(scope="module")
def tree(odim_file):
    return open_tree(odim_file)


@pytest.fixture(scope="module")
def tree_hits(tree):
    return suncal.sunpos_reflectivity(tree, refl_name=th_name(tree))


# Python 3.9: no xarray.DataTree.
def test_unsupported_datatree_class_raises():
    # E.g. datatree.DataTree from xarray-datatree, the only DataTree on Python 3.9.
    class DataTree:
        pass

    with pytest.raises(TypeError, match="Python 3.10"):
        suncal.sunpos_reflectivity(DataTree())
    with pytest.raises(TypeError, match="Python 3.10"):
        suncal.check_sun_in_scope(DataTree(), 10)


# Same result as the default pyodim input.
@needs_xradar
def test_xradar_hits_match_pyodim(hits, tree_hits):
    expected = hits.sort_values(HIT_KEY).reset_index(drop=True)
    result = tree_hits.sort_values(HIT_KEY).reset_index(drop=True)

    assert list(result.columns) == list(expected.columns)
    assert len(result) == len(expected) == 406
    # Same gates, same values.
    for column in ["range", "fmin", "reflectivity", "differential_reflectivity"]:
        np.testing.assert_array_equal(result[column], expected[column])
    # Ray azimuths agree to floating-point rounding.
    np.testing.assert_allclose(result.radar_azimuth, expected.radar_azimuth, atol=1e-9)
    # Nominal elevation: float32 in pyodim, float64 in xradar.
    np.testing.assert_allclose(result.radar_elevation, expected.radar_elevation, atol=1e-5)
    # The two readers compute ray times differently (a few ms apart), so the Sun
    # position differs by about 1e-5 deg.
    assert (result.time - expected.time).abs().max() < pd.Timedelta("50ms")
    np.testing.assert_allclose(result.sun_azimuth, expected.sun_azimuth, atol=1e-3)
    np.testing.assert_allclose(result.sun_elevation, expected.sun_elevation, atol=1e-3)


@needs_xradar
@pytest.mark.parametrize("threshold, expected", [(10, True), (6, True), (1, False)])
def test_xradar_check_sun_in_scope_matches_file(tree, odim_file, threshold, expected):
    assert suncal.check_sun_in_scope(tree, threshold) is expected
    assert suncal.check_sun_in_scope(odim_file, threshold) is expected


@needs_xradar
def test_xradar_check_sun_in_scope_is_false_at_night(odim_copy):
    with h5py.File(odim_copy, "r+") as odim:
        odim["where"].attrs["lon"] = odim["where"].attrs["lon"] - 180
    assert suncal.check_sun_in_scope(open_tree(odim_copy), 10) is False


@needs_xradar
def test_xradar_sun_out_of_scope_raises(tree):
    with pytest.raises(suncal.SunNotFoundError, match="not within scope"):
        suncal.sunpos_reflectivity(tree, refl_name=th_name(tree), zenith_threshold=1)


@needs_xradar
def test_xradar_no_solar_hit_raises(odim_copy, fill_quantity):
    fill_quantity(odim_copy, "TH", 20.0)
    tree = open_tree(odim_copy)
    with pytest.raises(suncal.SunNotFoundError, match="No solar hit"):
        suncal.sunpos_reflectivity(tree, refl_name=th_name(tree))


@needs_xradar
def test_xradar_clean_data_matches_pyodim(odim_copy, fill_quantity):
    # Many hits over several sweeps: checks that the sweeps are paired correctly.
    fill_quantity(odim_copy, "TH", 0.0)
    fill_quantity(odim_copy, "DBZH")
    expected = suncal.sunpos_reflectivity(odim_copy).sort_values(HIT_KEY).reset_index(drop=True)
    tree = open_tree(odim_copy)
    result = suncal.sunpos_reflectivity(tree, refl_name=th_name(tree)).sort_values(HIT_KEY).reset_index(drop=True)

    assert result.radar_elevation.nunique() > 1
    assert len(result) == len(expected)
    np.testing.assert_allclose(result.radar_azimuth, expected.radar_azimuth, atol=1e-9)
    np.testing.assert_allclose(result.radar_elevation, expected.radar_elevation, atol=1e-5)


@needs_xradar
def test_xradar_missing_zdr_is_optional(tree):
    result = suncal.sunpos_reflectivity(tree, refl_name=th_name(tree), zdr_name="NOT_A_FIELD")
    assert "differential_reflectivity" not in result.columns
    assert len(result) == 406


@needs_xradar
def test_xradar_missing_reflectivity_field_raises(tree):
    with pytest.raises(KeyError, match="DBTH"):
        suncal.sunpos_reflectivity(tree, refl_name="NOT_A_FIELD")


@needs_xradar
def test_xradar_tree_without_sweep_raises(tree):
    import xarray as xr

    with pytest.raises(ValueError, match="no sweep"):
        suncal.sunpos_reflectivity(xr.DataTree(tree.to_dataset()))
