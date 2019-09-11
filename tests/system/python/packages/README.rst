Script to automate FogLAMP Packages
-----------------------------------

1. Install git i.e. `sudo apt install git`

2. Clone FogLAMP repo and `cd tests/system/python/packages/`

3. Make sure FOGLAMP_ROOT to be set where you have cloned FogLAMP

Execute `python3 -m pytest -s -vv test_available_and_install_api.py` to run test once. Default build version is nightly, you can pass an argument e.g. `--package-build-version=1.7.0RC`

TODO Items
----------

1. Script should run on CentOS 7 & RHEL 7 platforms
2. We need to think for those plugins their discovery totally depend upon on the sensor attached like foglamp-south-sensehat etc
3. `--package-build-list=["p0", "p1"]` is not working by default p0 is set

