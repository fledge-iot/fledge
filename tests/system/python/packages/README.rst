Script to automate Fledge Packages
-----------------------------------

1. Install git i.e. `sudo apt install git`

2. Clone Fledge repo and `cd tests/system/python/packages/`

3. Make sure FLEDGE_ROOT to be set where you have cloned Fledge

Execute `python3 -m pytest -s -vv test_available_and_install_api.py` to run test once.
Default build-version is nightly, build-list set to p0, build-source-list set to false.
So you can pass an argument to override these values e.g. `--package-build-version=1.7.0RC` || (`--package-build-list=p0,p1` or `--package-build-list=all`) || `--package-build-source-list=true`

TODO Items
----------

1. Script should run on CentOS 7 & RHEL 7 platforms
2. We need to think for those plugins their discovery totally depend upon on the sensor attached like fledge-south-sensehat etc
3. Coral specific plugins handling for other platforms in script
4. Better reporting probably in csv format for the status of plugin
