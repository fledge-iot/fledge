
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

- **remove**: apt removes all fledge packages; deletes /usr/local/fledge;

- **install**: apt update; install fledge; install gui; install other fledge packages

- **test**: curl commands to simulate all gui actions in the lab (except game)

- **reset**: Reset script is to stop fledge; reset the db and delete any python scripts.


**`test.config` contains following variables that are used by `test` scripts in its execution:**

- **FLEDGE_IP**: IP Address of the system on which fledge is running.

- **PI_IP**: IP Address of PI Web API.

- **PI_USER**: Username used for accessing PI Web API.

- **PI_PASSWORD**: Password used for PI Web API.

- **PI_PORT**: Port number of PI Web API on which fledge will connect.

- **PI_DB**: Database in wihch PI Point is to be stored.

- **MAX_RETRIES**: Retries to check data and info via API before declaring it failed to see the expected.

- **SLEEP_FIX**: Time to sleep to fix bugs. This should be zero.

- **EXIT_EARLY**: It is a Boolean variable, if contains value '1' then test will stop execution as soon as any error occur.

- **ADD_NORTH_AS_SERVICE**: This variable defines whether North(OMF) is created as a task or a service.

- **VERIFY_EGRESS_TO_PI**: It is a Boolean variable, if contains value '1' then North(OMF) is created and data sent to PI Web API will be verified.

- **STORAGE**: This variable defines the storage plugin for configuration used by fledge, i.e. sqlite, sqlitelb, postgres.

- **READING_PLUGIN_DB**: This variable by default contains "Use main plugin" that mean READING_PLUGIN_DB will be the same that used in `STORAGE` variable. Apart of "Use main plugin", it may also contain sqlite, sqlitelb, sqlite-in-memory, postgres values.
