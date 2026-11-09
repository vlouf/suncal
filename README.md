[![Python package](https://github.com/vlouf/suncal/actions/workflows/python-package.yml/badge.svg)](https://github.com/vlouf/suncal/actions/workflows/python-package.yml)

# ☀️ Suncal

**Suncal** is a software package for solar calibration of radar data respecting the ODIM H5 convention.
It utilizes radio noise from the Sun to check the quality of dual-polarization weather radar receivers for the S-band and C-band.

## Installation

**Suncal** is published on PyPI as [`solarcal`](https://pypi.org/project/solarcal/):

```bash
pip install solarcal
```

Then import it as `suncal` in your Python scripts:

```python
import suncal
```

> **Note:** the [`suncal`](https://pypi.org/project/suncal/) package on PyPI is an unrelated project. `pip install suncal` does not install this software. Both packages import as `suncal`, so avoid installing them in the same environment.

### Requirements

- Python 3.9 or later
- Radar data in ODIM H5 format

`pip` installs the required packages automatically: `h5py`, `numpy`, `pandas`, `pyodim` (0.7 or later), `scikit-learn`, `scipy` and `xarray`.

### Optional: xradar input

With Python 3.10 or later, `sunpos_reflectivity` and `check_sun_in_scope` also accept a radar volume already opened with [xradar](https://github.com/openradar/xradar) (an `xarray.DataTree`). Install the extra:

```bash
pip install "solarcal[xradar]"
```

```python
import xarray as xr
import suncal

radar = xr.open_datatree("volume.pvol.h5", engine="odim")  # xradar 0.13 or later
hits = suncal.sunpos_reflectivity(radar, refl_name="DBTH")
```

xradar 0.13 and later rename the ODIM quantity `TH` to `DBTH`, so pass the field names as they appear in the DataTree. With older xradar versions, open the file with `xradar.io.open_odim_datatree` and keep `refl_name="TH"`. For an ODIM file, the solar hits are the same as with the default input, up to a few milliseconds in the ray times.

ODIM file paths are still read with `pyodim`, which remains the default. On Python 3.9, only file input is available.

### Upgrading

Version 1.2.0 corrects the Sun position calculation, which changes pointing results compared with earlier versions. See the [changelog](https://github.com/vlouf/suncal/blob/master/CHANGELOG.md) for details.

## Bibliography

If you use `suncal` in your research, please cite the following paper:

**Louf, Valentin, and Alain Protat**. *Real-Time Monitoring of Weather Radar Network Calibration and Antenna Pointing.* Journal of Atmospheric and Oceanic Technology, April 24, 2023. https://doi.org/10.1175/JTECH-D-22-0118.1.

BibTeX:
```bibtex
@article {Louf2023,
    author = "Valentin Louf and Alain Protat",
    title = "Real-Time Monitoring of Weather Radar Network Calibration and Antenna Pointing",
    journal = "Journal of Atmospheric and Oceanic Technology",
    year = "2023",
    publisher = "American Meteorological Society",
    volume = "40",
    number = "7",
    doi = "10.1175/JTECH-D-22-0118.1",
    pages=  "823 - 844",
}
```

The Suncal algorithm is a Python implementation based on:

- **Huuskonen, A., & Holleman, I.** (2007). *Determining Weather Radar Antenna Pointing Using Signals Detected from the Sun at Low Antenna Elevations*. Journal of Atmospheric and Oceanic Technology, 24(3), 476–483. [10.1175/JTECH1978.1](https://doi.org/10.1175/JTECH1978.1)
- **Holleman, I., & Huuskonen, A.** (2013). *Analytical formulas for refraction of radiowaves from exoatmospheric sources*. Radio Science, 48(3), 226–231. [10.1002/rds.20030](https://doi.org/10.1002/rds.20030)
- **Altube, P., Bech, J., Argemí, O., & Rigo, T.** (2015). *Quality control of antenna alignment and receiver calibration using the sun: Adaptation to midrange weather radar observations at low elevation angles*. Journal of Atmospheric and Oceanic Technology. [10.1175/jtech-d-14-00116.1](https://doi.org/10.1175/jtech-d-14-00116.1)
- **Huuskonen, A., Kurri, M., & Holleman, I.** (2016). *Improved analysis of solar signals for differential reflectivity monitoring*. Atmospheric Measurement Techniques, 9(7), 3183–3192. [10.5194/amt-9-3183-2016](https://doi.org/10.5194/amt-9-3183-2016)

## About

Suncal uses a Sun position algorithm derived from [sun-position](https://github.com/s-bear/sun-position), available under the MIT license, which is based on the algorithm in:

- **Reda, I., & Andreas, A.** (2004). *Solar position algorithm for solar radiation applications*. Solar Energy, 76(5), 577–589. [10.1016/j.solener.2003.12.003](https://doi.org/10.1016/j.solener.2003.12.003)

## License

Suncal is licensed under the [Apache License 2.0](https://github.com/vlouf/suncal/blob/master/LICENSE), except for `suncal/spa.py`, which is derived from [sun-position](https://github.com/s-bear/sun-position) and remains under the [MIT License](https://github.com/vlouf/suncal/blob/master/LICENSES/MIT-sun-position.txt).

