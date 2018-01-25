*************************
FogLAMP Integration Tests
*************************

Integration tests are the second category of test in FogLAMP. These test ensures that two or more FogLAMP units when
integrated works good as a single component.

For example, testing of purge process. To purge any data in FogLAMP, it is required that we have asset data in FogLAMP
database. Other scenarios can be that we want to test the purge process with different set of configurations. This
requires integration of different components like Storage, configuration manager and purge task to work as
component that we are interested to test.
This kind of testing requires that all the different units work as a single sub-system.

Since these kinds of tests interacts between two or more heterogeneous systems, these are often slow in nature.

**NOTE:** *It is necessary to run FogLAMP for integration tests to work*

Currently integration tests can be executed only once at a time, going forward it will be possible to run integration
tests as a suite. To run any integration test, you need to replace the _core_management_port in the code. The core
management port is exposed by the FogLAMP Core service when FogLAMP starts.

Start FogLAMP
::
    $FOGLAMP_ROOT/scripts/start

Check for core management port from /var/log/syslog, e.g:
::
    Management port received is 41347

or it can be found out from running the foglamp status command which displays a common port ``--port=99999`` for any service.

Replace the value of core_mgmt_port in conftest.py, e.g:
::
    {'test_env': {'address': '0.0.0.0', 'core_mgmt_port': 41347}}

Run the test., e.g:
::
    ~/FogLAMP $ pytest tests/integration/foglamp/common/test_microservice.py

