Script to automate FogLAMP Packages
-----------------------------------

1. Install git i.e. `sudo apt install git`

2. Clone FogLAMP repo and `cd tests/system/python/package/`

3. Make sure FOGLAMP_ROOT to be set where you have cloned FogLAMP

Execute `python3 -m pytest -s -vv test_packages.py` to run test once. Default build version is nightly, you can pass an argument e.g. `--build-version=1.7.0RC`

Todo Items
----------

1. Script should run on CentOs/Rhel platforms
2. We need to think for those plugins their discovery totally depend upon on the sensor attached like foglamp-south-sensehat etc
