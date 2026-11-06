# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

The package installs as `solarcal` and imports as `suncal`. The `suncal` project on
PyPI is unrelated. Only 1.1.3, 1.1.5 and later versions were published on PyPI.

Entries before 1.1.3 were reconstructed from the git history, so their contents and
dates are approximate.

## [1.2.0] - 2026-11-06

**This release changes results.** Pointing values computed with 1.2.0 cannot be
compared directly with earlier values: expect a date-dependent shift of up to about
0.15° in the Sun position. See [Upgrading to 1.2.0](#upgrading-to-120).

### Fixed

- **Sun position:** corrected errors in `spa.py`, all but possibly one inherited from
  the 2018 version of [sun-position](https://github.com/s-bear/sun-position). The
  results now reproduce the worked example in Reda & Andreas (2004) and agree with
  `pvlib`.
  - Removed a duplicate radian-to-degree conversion of the nutation terms. This was
    the main error, up to about 0.15° in Sun position, varying with date.
  - Converted latitude to radians in the parallax terms (very small effect).
  - Used the correct term in the topocentric declination (about 5e-5°).
  - Corrected five mistyped coefficients in the Earth position tables (about 2e-6° at
    the reference date).
- **`topocentric_sunpos`:** no longer crashes.
- **`p0` and `p0_5P`:** the 3P and 5P fits ignored the regression intercept, so the
  reported power was close to 0 whatever the data. Pointing offsets, `r_sq` and `sun`
  are not affected by this fix.
- **`solar_statistics(do_5P=True)`:** no longer crashes when exactly 5 hits remain
  after filtering. The `*_5P` values are NaN and the 3P results are still returned.
- **Azimuth wrap:** azimuth differences now wrap at 360° in `sunpos_reflectivity` and
  `solar_statistics`. This only matters when the Sun is near north at low elevation,
  which is expected only at high latitudes.
- **`check_sun_in_scope`:** accepts ODIM files that store attributes as normal strings
  as well as bytes.

### Added

- Test suite covering the Sun position, refraction, solar hit extraction and model
  inversion, including a real ODIM volume from the Melbourne radar.

### Changed

- Licence metadata is now `Apache-2.0 AND MIT`. `suncal/spa.py` stays under the MIT
  licence of the code it derives from: its copyright notice was restored in that file
  and added as `LICENSES/MIT-sun-position.txt`. The rest of the package remains under
  Apache 2.0.
- `CITATION.cff` now has the current version, licence and repository.

### Known issues

- `p0` can still be unreliable on real data. `solar_statistics` fits all hits selected
  within ±5° of the Sun, far beyond where the beam model applies. On one day of data
  from one radar this gave `p0` = +37 with R² = 0.003, and restricting the hits also
  moved `azi` and `elev` by up to about 0.2°. This has not been investigated further:
  `sun` and the medians (`azi_med`, `elev_med`) are the safer values for now.

### Upgrading to 1.2.0

Example from the included Melbourne volume (2026-11-05 08:17 UTC):

| Value           | 1.1.5    | 1.2.0    |
| --------------- | -------- | -------- |
| Sun azimuth     | 255.536° | 255.641° |
| Sun elevation   | 7.228°   | 7.169°   |
| `azi_med`       | 0.530°   | 0.634°   |
| `elev_med`      | −0.445°  | −0.504°  |

The number of solar hits and `sun` do not change for this volume.

Existing solar hit CSV files store the Sun position calculated when they were created.
Running `solar_statistics` on them with 1.2.0 fixes `p0` but not the Sun position. To
correct older data, run `sunpos_reflectivity` on the volumes again, or recompute the
Sun columns from each row's time and the radar's location.

## [1.1.5] - 2026-11-06

### Fixed

- PyPI publishing: the release workflow now uses trusted publishing directly, and
  stops if the release tag does not match the package version.

## [1.1.4] - 2026-11-06

Tagged on GitHub, but not published on PyPI: the tag still carried version 1.1.3.

### Changed

- Compatibility with `pyodim` 0.7 and later, now the minimum version. Files are no
  longer read through the deprecated lazy loader, so `dask` is not needed.
- Packaging moved from `setup.py` to `pyproject.toml`.
- Python 3.9 is now the minimum supported version, with CI on Python 3.9 to 3.14.

### Added

- Automated tests and CI workflow.
- `CITATION.cff`.

### Fixed

- Licence metadata declared MIT, while the project's licence is Apache 2.0.

## [1.1.3] - 2024-08-15

First version published on PyPI.

### Changed

- The distribution was renamed `solarcal`, because `suncal` on PyPI is an unrelated
  project. The import name is still `suncal`.

## [1.1.2] - 2024-08-15

### Fixed

- Permissions of the release workflow. Not published on PyPI.

## [1.1.1] - 2024-08-15

### Changed

- Updated the release workflow. Not published on PyPI.

## [1.1.0] - 2024-08-15

Merged the `pyodim` branch into `master`. Not published on PyPI.

### Added

- `get_sunpos_for_location`: Sun azimuth and elevation for a time and location.
- Workflow for releases to PyPI.

### Changed

- Updated the code for `numpy` and `pandas` deprecations.

### Removed

- The `s3car_suncal.py` and `national_archive.py` scripts.

## [1.0.20] - 2024-06-11

### Added

- `check_sun_in_scope` is now public.

### Changed

- `netCDF4` replaced by `h5py` for reading ODIM files.
- Sweeps below 1° elevation, instead of 0.9°, are now skipped.

## 1.0 - 2020-10-09 to 2023

The version number stayed at 1.0 during this period, and there are no separate releases
of these changes.

### Added

- `solar_statistics` reads gzip-compressed CSV files (2023).
- `band` argument to `solar_statistics`, with separate gaseous attenuation for S and C
  bands (2021).
- `check_sun_in_scope`, an early check on whether the Sun can be in view (2022).

### Changed

- `pyodim` replaced Py-ART for reading radar data, so input must be ODIM H5. Default
  field names became `TH`, `DBZH` and `ZDR` (2022).
- **Sign convention:** offsets are now Sun minus radar, not radar minus Sun (2020).
- The solar position no longer applies its own atmospheric refraction correction.
  Radar elevation is corrected with the 5/4 Earth model instead (2020).

## 0.9.0 - 2020-08-13

### Added

- `sunstats` module with `solar_statistics`: model inversion for pointing offsets and
  solar power.
- Ray filling ratio (`fmin`) in the solar hit output.

### Changed

- Refraction correction now follows Holleman & Huuskonen (2013).

## 0.5.0 - 2020-02-22

First version.

### Added

- `sunpos_reflectivity`: extracts solar hits from a radar volume.
- `spa.py`: Sun position algorithm, derived from
  [sun-position](https://github.com/s-bear/sun-position).

[1.2.0]: https://github.com/vlouf/suncal/compare/v1.1.5...v1.2.0
[1.1.5]: https://github.com/vlouf/suncal/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/vlouf/suncal/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/vlouf/suncal/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/vlouf/suncal/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/vlouf/suncal/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/vlouf/suncal/compare/v1.0.20...v1.1.0
[1.0.20]: https://github.com/vlouf/suncal/releases/tag/v1.0.20
