# ☀️ Suncal

Suncal is a software package for solar calibration of radar data. It utilizes radio noise from the Sun to check the quality of dual-polarization weather radar receivers for the S-band and C-band.

## Dependencies

Suncal requires the following dependencies:

- [netCDF4](https://github.com/Unidata/netcdf4-python)
- [numpy](https://www.numpy.org/)
- [pandas](https://pandas.pydata.org/)
- [Py-ART](https://github.com/ARM-DOE/pyart)
- [dask](https://dask.org/)
- Scikit-learn
- Scipy

These dependencies will be automatically installed by pip.

In addition, you will need to install the `suncal` and `pyodim` libraries from Github:
```
pip install git+https://github.com/vlouf/suncal.git
pip install git+https://github.com/vlouf/pyodim.git`
```

## Example Jupyter Notebook

An example Jupyter notebook is available in the `example` directory. This notebook demonstrates how to use the `gpmmatch` library to a volume matching of GPM data against radar data. The notebook provides step-by-step instructions for downloading a sample of radar data from the Australian weather radar network archive. Finally, the notebook uses Matplotlib to create a plot of the results of the GPMmatch technique.

## Bibliography

The Suncal algorithm is a Python implementation *inspired* by these works:

Huuskonen, A., & Holleman, I. (2007). Determining Weather Radar Antenna Pointing Using Signals Detected from the Sun at Low Antenna Elevations. Journal of Atmospheric and Oceanic Technology, 24(3), 476–483. [10.1175/JTECH1978.1](https://doi.org/10.1175/JTECH1978.1)

Holleman, I., & Huuskonen, A. (2013). Analytical formulas for refraction of radiowaves from exoatmospheric sources. Radio Science, 48(3), 226–231. [10.1002/rds.20030](https://doi.org/10.1002/rds.20030)

Altube, P., Bech, J., Argemí, O., & Rigo, T. (2015). Quality control of antenna alignment and receiver calibration using the sun: Adaptation to midrange weather radar observations at low elevation angles. Journal of Atmospheric and Oceanic Technology. [10.1175/jtech-d-14-00116.1](https://doi.org/10.1175/jtech-d-14-00116.1)

Huuskonen, A., Kurri, M., & Holleman, I. (2016). Improved analysis of solar signals for differential reflectivity monitoring. Atmospheric Measurement Techniques, 9(7), 3183–3192. [10.5194/amt-9-3183-2016](https://doi.org/10.5194/amt-9-3183-2016)


## About

Suncal utilizes a Sun position algorithm developed developped by: [https://github.com/s-bear/sun-position] under MIT licence which is based on the algorithm referenced in:

Reda, I., & Andreas, A. (2004). Solar position algorithm for solar radiation applications. Solar Energy, 76(5), 577–589. [10.1016/j.solener.2003.12.003](https://doi.org/10.1016/j.solener.2003.12.003)

## References

If you use gpmmatch for a scientific publication, please cite the following paper:

Louf, V., Protat, A., Warren, R. A., Collis, S. M., Wolff, D. B., Raunyiar, S., Jakob, C., & Petersen, W. A. (2019). An Integrated Approach to Weather Radar Calibration and Monitoring Using Ground Clutter and Satellite Comparisons. Journal of Atmospheric and Oceanic Technology, 36(1), 17–39. [10.1175/JTECH-D-18-0007.1](https://doi.org/10.1175/JTECH-D-18-0007.1)

## License

This library is open source and made freely available according to the below
text:

    Copyright 2020 Valentin Louf
    Copyright 2023 Commonwealth of Australia, Bureau of Meteorology

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

A copy of the license is also provided in the LICENSE file included with the
source distribution of the library.
