"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path
from io import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='suncal',
    version='0.5.0',
    description='Ground radar monitoring of calibration using the Sun as reference.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/vlouf/suncal',
    author='Valentin Louf',
    author_email='valentin.louf@bom.gov.au',
    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Atmospheric Science',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='radar weather meteorology calibration',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['numpy', 'arm_pyart', 'pandas', 'netCDF4', 'dask', 'crayons'],
    project_urls={
        'Bug Reports': 'https://github.com/vlouf/suncal/issues',
        'Source': 'https://github.com/vlouf/suncal/',
    },
)
