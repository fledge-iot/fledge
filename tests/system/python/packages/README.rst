Script to automate FogLAMP Packages
-----------------------------------

1. Install git i.e. `sudo apt install git`

2. Clone FogLAMP repo and `cd tests/system/python/packages/`

3. Make sure FOGLAMP_ROOT to be set where you have cloned FogLAMP

Execute `python3 -m pytest -s -vv test_available_and_install_api.py` to run test once. Default build version is nightly,
and default build list set to p0. So you can pass an argument to override these values e.g. `--package-build-version=1.7.0RC` or `--package-build-list=p0,p1`

TODO Items
----------

1. Script should run on CentOS 7 & RHEL 7 platforms
2. We need to think for those plugins their discovery totally depend upon on the sensor attached like foglamp-south-sensehat etc
3. Provide facility to install each plugin as per category defined in json file `--package-build-list=all`
