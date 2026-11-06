Here's the note, in rough priority order. Nothing below has been done unless it says so, and all the packaging work so far is still uncommitted.

## suncal: to do

### Packaging and CI
- [ ] Commit the current changes: `pyproject.toml`, the `setup.py` removal and the CI workflow.
- [ ] Check that the first GitHub Actions run passes. Python 3.12 and 3.13 haven't been run yet, and neither has the workflow itself.
- [ ] Decide whether to keep `requires-python = ">=3.11"`, which drops 3.8–3.10.
- [ ] Decide whether to update `release_to_pypi.yml`, which has old action versions and a manual token step that's probably no longer needed.

### Code
- [ ] Resolve the `lazy_load` deprecation at [suncal.py:174](suncal/suncal.py#L174) (your GitHub issue).
- [ ] If that fix drops lazy loading, replace `pyodim[dask]` with `pyodim` in [pyproject.toml](pyproject.toml). If it keeps lazy loading with `lazy=True`, keep the dask extra.
- [ ] Update the docstring at [suncal.py:144](suncal/suncal.py#L144), which still says Py-ART instead of ODIM H5.

### Licence and docs
- [ ] Add the original MIT copyright notice to [spa.py](suncal/spa.py).
- [ ] Update `version` and `date-released` in [CITATION.cff](CITATION.cff), which still say 0.1.0 and 2023.
- [ ] Add a README note that the Sandia `suncal` package on PyPI is unrelated, and to install with `pip install solarcal`.
- [ ] Fix the README typos: "developed developped" and "is a Python implementation is based on".

### Test suite
- [ ] Find a small real ODIM volume to commit, ideally with a known solar hit.
- [ ] Test `sunpos_reflectivity` and `check_sun_in_scope` end to end. This also covers `read_odim` and the dask dependency, which CI doesn't currently exercise.
- [ ] Test `spa.py` and `get_sunpos_for_location` against published reference values, such as Reda & Andreas (2004).
- [ ] Test `correct_refractivity` against known values.
- [ ] Make `solar_statistics` tests check retrieved values, for example by recovering a known pointing bias from synthetic data.
- [ ] Clean up [test_suncal.py](test/test_suncal.py): remove the placeholder comments and stop relying on a path that only works from the repo root.

### Next release
- [ ] Bump the version, since 1.1.3 is already on PyPI as `solarcal`.
- [ ] Do this after the `lazy_load` fix and the licence notice, so both ship in the release.

I can save this as a `TODO.md` in the repo or format it for a GitHub issue if you'd like it tracked there.


Please update the README, I have added 3 plots in the docs/ directory, choose the ones that you find helpfull, no need to put everything, these are the plots we get operationnaly after using suncal in s3car-server to monitor the antenna pointing of the radar network. We can see that is perfectly aligned with melbourne but not good for the two other sites. It doesn't have to be a full RE