"""
End-to-end tests of the solar hit extraction, using a real ODIM volume.

The expected sun position comes from pvlib spa_python (azimuth 255.6414, elevation
7.1702 at 08:17:03 UTC).
"""
import h5py
import numpy as np
import pandas as pd
import pytest
import suncal
from suncal.suncal import correct_refractivity

SUN_AZIMUTH = 255.6414
SUN_ELEVATION = 7.1702
SUN_TOLERANCE = 0.01


# Refraction: Holleman and Huuskonen (2013) eq. 9-10, values worked out by hand.
@pytest.mark.parametrize("elevation, expected", [(0, 0.716769), (45, 0.017908), (90, 0)])
def test_correct_refractivity_values(elevation, expected):
    assert correct_refractivity(elevation) == pytest.approx(expected, abs=1e-4)


def test_correct_refractivity_decreases_with_elevation():
    assert np.all(np.diff(correct_refractivity(np.linspace(0, 90, 91))) < 0)


def test_correct_refractivity_is_zero_in_a_vacuum():
    assert correct_refractivity(10, n0=1.0) == pytest.approx(0, abs=1e-12)


def test_correct_refractivity_uses_earth_radius_factor():
    assert correct_refractivity(5, k=4 / 3) != pytest.approx(correct_refractivity(5, k=5 / 4), abs=1e-3)


# Sun in scope.
@pytest.mark.parametrize("threshold, expected", [(10, True), (6, True), (1, False)])
def test_check_sun_in_scope_threshold(odim_file, threshold, expected):
    assert suncal.check_sun_in_scope(odim_file, threshold) is expected


def test_check_sun_in_scope_is_false_at_night(odim_copy):
    with h5py.File(odim_copy, "r+") as odim:
        odim["where"].attrs["lon"] = odim["where"].attrs["lon"] - 180
    assert suncal.check_sun_in_scope(odim_copy, 10) is False


def test_check_sun_in_scope_falls_back_on_volume_time(odim_copy):
    with h5py.File(odim_copy, "r+") as odim:
        for name in [name for name in odim if name.startswith("dataset")]:
            del odim[name]
    assert suncal.check_sun_in_scope(odim_copy, 10) is True


@pytest.mark.parametrize("remove_datasets", [False, True], ids=["sweep-times", "volume-time"])
def test_check_sun_in_scope_accepts_string_attributes(odim_copy, remove_datasets):
    # Files written with variable-length strings read back as str, not bytes.
    with h5py.File(odim_copy, "r+") as odim:
        for key in ("date", "time"):
            odim["what"].attrs[key] = odim["what"].attrs[key].decode()
        for name in [name for name in odim if name.startswith("dataset")]:
            if remove_datasets:
                del odim[name]
                continue
            what = odim[f"{name}/what"].attrs
            what["enddate"] = what["enddate"].decode()
            what["endtime"] = what["endtime"].decode()
    assert suncal.check_sun_in_scope(odim_copy, 10) is True


# Solar hits from the real volume.
def test_hits_output_columns(hits):
    assert list(hits.columns) == [
        "time",
        "range",
        "sun_azimuth",
        "sun_elevation",
        "radar_elevation",
        "radar_azimuth",
        "fmin",
        "reflectivity",
        "differential_reflectivity",
    ]


def test_hits_are_the_known_interference(hits):
    assert len(hits) == 406
    assert hits.reflectivity.sum() == pytest.approx(4648.5)
    assert sorted(hits.radar_azimuth.round(2).unique()) == [255.01, 256.0]
    assert hits.fmin.between(0.486, 0.49).all()


def test_hits_come_from_the_expected_sweep_and_time(hits):
    assert hits.radar_elevation.unique() == pytest.approx(7.8 - correct_refractivity(7.8), abs=1e-3)
    # The file records the 7.8 deg sweep between 08:16:55 and 08:17:10.
    assert hits.time.between(pd.Timestamp("2026-11-05 08:16:55"), pd.Timestamp("2026-11-05 08:17:10")).all()


def test_hits_sun_position_matches_independent_reference(hits):
    assert hits.sun_azimuth.to_numpy() == pytest.approx(SUN_AZIMUTH, abs=SUN_TOLERANCE)
    assert hits.sun_elevation.to_numpy() == pytest.approx(SUN_ELEVATION, abs=SUN_TOLERANCE)


def test_interference_is_seen_where_the_sun_is(hits):
    # The real check of the chain: the rays with the signal point at the computed Sun.
    assert hits.radar_azimuth.mean() == pytest.approx(SUN_AZIMUTH, abs=1)
    assert hits.radar_elevation.mean() == pytest.approx(SUN_ELEVATION, abs=1)


def test_hits_respect_the_selection_criteria(hits):
    assert (hits.range > 50e3).all()
    assert (hits.reflectivity < 15).all()
    assert hits.reflectivity.notna().all()
    assert ((hits.radar_azimuth - hits.sun_azimuth).abs() < 5).all()


def test_hits_can_go_through_solar_statistics(hits, tmp_path):
    path = tmp_path / "hits.csv"
    hits.to_csv(path, index=False)
    stats = suncal.solar_statistics(str(path), beamwidth=0.913)
    assert stats.index[0] == pd.Timestamp("2026-11-05").date()
    assert stats["sun"].iloc[0] == pytest.approx(-86.127304, abs=1e-4)
    assert stats["azi_med"].iloc[0] == pytest.approx(0.6343, abs=SUN_TOLERANCE)
    assert stats["elev_med"].iloc[0] == pytest.approx(-0.5037, abs=SUN_TOLERANCE)


# Selection logic, on modified copies of the volume.
def test_all_candidate_gates_are_kept_when_data_is_clean(odim_copy, fill_quantity):
    fill_quantity(odim_copy, "TH", 0.0)
    fill_quantity(odim_copy, "DBZH")
    hits = suncal.sunpos_reflectivity(odim_copy)

    assert hits.radar_elevation.nunique() > 1
    assert (hits.radar_elevation >= 1).all()
    assert ((hits.radar_elevation - hits.sun_elevation).abs() <= 5).all()
    assert ((hits.radar_azimuth - hits.sun_azimuth).abs() < 5).all()
    assert (hits.range > 50e3).all()


@pytest.mark.parametrize(
    "quantity, value",
    [("TH", None), ("TH", 20.0)],
    ids=["reflectivity-missing", "reflectivity-too-high"],
)
def test_no_solar_hit_raises(odim_copy, fill_quantity, quantity, value):
    fill_quantity(odim_copy, quantity, value)
    with pytest.raises(suncal.SunNotFoundError, match="No solar hit"):
        suncal.sunpos_reflectivity(odim_copy)


def test_precipitation_is_not_taken_for_the_sun(odim_copy, fill_quantity):
    fill_quantity(odim_copy, "TH", 0.0)
    fill_quantity(odim_copy, "DBZH", 20.0)
    with pytest.raises(suncal.SunNotFoundError, match="No solar hit"):
        suncal.sunpos_reflectivity(odim_copy)


def test_sun_out_of_scope_raises(odim_file):
    with pytest.raises(suncal.SunNotFoundError, match="not within scope"):
        suncal.sunpos_reflectivity(odim_file, zenith_threshold=1)


@pytest.mark.parametrize("threshold", [0, -1, 91])
def test_invalid_zenith_threshold_raises(odim_file, threshold):
    with pytest.raises(ValueError):
        suncal.sunpos_reflectivity(odim_file, zenith_threshold=threshold)


def test_missing_zdr_is_optional(odim_file):
    hits = suncal.sunpos_reflectivity(odim_file, zdr_name="NOT_A_FIELD")
    assert "differential_reflectivity" not in hits.columns
    assert len(hits) == 406


def test_missing_reflectivity_field_raises(odim_file):
    with pytest.raises(KeyError):
        suncal.sunpos_reflectivity(odim_file, corr_refl_name="NOT_A_FIELD")


def test_input_file_is_released_after_reading(odim_copy):
    suncal.sunpos_reflectivity(odim_copy)
    with h5py.File(odim_copy, "r+"):  # Raises if a handle was left open.
        pass


def test_hits_wrap_around_north(odim_copy, fill_quantity, monkeypatch):
    fill_quantity(odim_copy, "TH", 0.0)
    fill_quantity(odim_copy, "DBZH")
    real_sunpos = suncal.suncal.sunpos

    def sun_due_north(*args, **kwargs):
        positions = np.array(real_sunpos(*args, **kwargs))
        positions[..., 0] = 359.5
        return positions

    monkeypatch.setattr(suncal.suncal, "sunpos", sun_due_north)
    hits = suncal.sunpos_reflectivity(odim_copy)
    assert (hits.radar_azimuth > 355).any()
    assert (hits.radar_azimuth < 5).any()
