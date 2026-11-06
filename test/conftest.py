"""
Shared fixtures for the suncal test suite.

Test data:
    2_20261105_081500.pvol.h5: Melbourne (AU02) S-band volume, Rainbow ODIM H5,
        with a solar interference in the 7.8 deg sweep at 255-256 deg azimuth.
    suncal.50.20240215.csv.gz: one day of solar hits from radar 50.
"""
import shutil
from pathlib import Path

import h5py
import numpy as np
import pytest
import suncal

DATA_DIR = Path(__file__).parent
ODIM_FILE = DATA_DIR / "2_20261105_081500.pvol.h5"
SOLAR_CSV = DATA_DIR / "suncal.50.20240215.csv.gz"


@pytest.fixture(scope="session")
def odim_file():
    """Path to the real ODIM volume. Treat as read-only: use odim_copy to modify it."""
    return str(ODIM_FILE)


@pytest.fixture(scope="session")
def solar_csv():
    return str(SOLAR_CSV)


@pytest.fixture(scope="session")
def hits(odim_file):
    """Solar hits from the real volume. Computed once: copy before modifying."""
    return suncal.sunpos_reflectivity(odim_file)


@pytest.fixture
def odim_copy(tmp_path):
    """Temporary copy of the real volume that a test can modify."""
    path = tmp_path / ODIM_FILE.name
    shutil.copy(ODIM_FILE, path)
    return str(path)


@pytest.fixture
def fill_quantity():
    """Return a function setting one quantity to a constant in every sweep of a file."""

    def _fill(path, quantity, value=None):
        """value is in physical units; None writes the nodata flag, read back as NaN."""
        with h5py.File(path, "r+") as odim:
            for name in odim:
                if not name.startswith("dataset"):
                    continue
                for group in odim[name]:
                    if not group.startswith("data"):
                        continue
                    what = odim[f"{name}/{group}/what"].attrs
                    if what["quantity"].decode() != quantity:
                        continue
                    raw = what["nodata"] if value is None else (value - what["offset"]) / what["gain"]
                    data = odim[f"{name}/{group}/data"]
                    data[...] = np.full(data.shape, raw, dtype=data.dtype)

    return _fill
