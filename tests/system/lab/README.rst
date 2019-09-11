
Script to automate Fledge Lab
------------------------------

1. Install git i.e. `sudo apt install git`

2. Clone Fledge repo and `cd tests/system/lab/`

3. Check and set the configuration in `test.config`

4. Make sure to enable I2C Interface for enviro-pHAT and reboot.

For CI or individual's setup, `test.config` should be replaced (altered) per the parameters.

Execute `./run` to run test once. Default version it will use is nightly, you can pass an argument e.g. `./run 1.7.0RC`
To run the test for required (say 10) iterations or until it fails - execute `./run_until_fails 10 1.7.0RC`


**`run` and `run_until_fails` use the following scripts in its execution:**

**remove**: apt removes all fledge packages; deletes /usr/local/fledge;

**install**: apt update; install fledge; install gui; install other fledge packages

**test**: curl commands to simulate all gui actions in the lab (except game)

**reset**: Reset script is to stop fledge; reset the db and delete any python scripts.