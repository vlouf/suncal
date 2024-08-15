# ☀️ Suncal

Suncal is a software package for solar calibration of radar data. It utilizes radio noise from the Sun to check the quality of dual-polarization weather radar receivers for the S-band and C-band.

## Dependencies

Suncal requires the following dependencies:

- [h5py](https://www.h5py.org)
- [numpy](https://www.numpy.org/)
- [pandas](https://pandas.pydata.org/)

These dependencies will be automatically installed by pip.

In addition, you will need to install the `suncal` and `pyodim` libraries from Github:
```
pip install git+https://github.com/vlouf/suncal.git
pip install git+https://github.com/vlouf/pyodim.git`
```

## Bibliography

The Suncal algorithm is a Python implementation *inspired* by these works:

Huuskonen, A., & Holleman, I. (2007). Determining Weather Radar Antenna Pointing Using Signals Detected from the Sun at Low Antenna Elevations. Journal of Atmospheric and Oceanic Technology, 24(3), 476–483. [10.1175/JTECH1978.1](https://doi.org/10.1175/JTECH1978.1)

Holleman, I., & Huuskonen, A. (2013). Analytical formulas for refraction of radiowaves from exoatmospheric sources. Radio Science, 48(3), 226–231. [10.1002/rds.20030](https://doi.org/10.1002/rds.20030)

Altube, P., Bech, J., Argemí, O., & Rigo, T. (2015). Quality control of antenna alignment and receiver calibration using the sun: Adaptation to midrange weather radar observations at low elevation angles. Journal of Atmospheric and Oceanic Technology. [10.1175/jtech-d-14-00116.1](https://doi.org/10.1175/jtech-d-14-00116.1)

Huuskonen, A., Kurri, M., & Holleman, I. (2016). Improved analysis of solar signals for differential reflectivity monitoring. Atmospheric Measurement Techniques, 9(7), 3183–3192. [10.5194/amt-9-3183-2016](https://doi.org/10.5194/amt-9-3183-2016)


## About

Suncal utilizes a Sun position algorithm developed developped by: [https://github.com/s-bear/sun-position] under MIT licence which is based on the algorithm referenced in:

Reda, I., & Andreas, A. (2004). Solar position algorithm for solar radiation applications. Solar Energy, 76(5), 577–589. [10.1016/j.solener.2003.12.003](https://doi.org/10.1016/j.solener.2003.12.003)

