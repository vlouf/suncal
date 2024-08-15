from setuptools import setup, find_packages
from os import path
from io import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='suncal',
    version='1.1.3',
    description='Ground radar monitoring of calibration using the Sun as reference.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/vlouf/suncal',
    author='Valentin Louf',
    author_email='valentin.louf@bom.gov.au',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Atmospheric Science',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='radar weather meteorology calibration',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['numpy', 'pyodim', 'pandas', 'h5py', 'scipy', 'scikit-learn'],
    project_urls={
        'Bug Reports': 'https://github.com/vlouf/suncal/issues',
        'Source': 'https://github.com/vlouf/suncal/',
    },
)
