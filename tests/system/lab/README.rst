
Script to automate FogLAMP Lab
------------------------------

1. Install git i.e. `sudo apt install git`

2. Clone FogLAMP repo and `cd tests/system/lab/`

Execute `./run` to run test once. Default version it will use is nightly, you can pass an argument e.g. `./run 1.7.0RC`
To run the test for required (say 10) iterations or until it fails - execute `./run_until_fails 10 1.7.0RC`


**`run` and `run_until_fails` use the following scripts in its execution:**

**remove**: apt removes all foglamp packages; deletes /usr/local/foglamp; reboots

**install**: apt update; install foglamp; install gui; install other foglamp packages

**test**: curl commands to simulate all gui actions in the lab (except game)

**reset**: Reset script is to stop foglamp; reset the db and delete any python scripts.