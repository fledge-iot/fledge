
.. |System Test Utility and Suites| raw:: html

   <a href="https://foglamp.readthedocs.io/en/master/08_developer/03_systemtest.html#foglamp-system-test-principles" target="_blank">System Test Utility and Suites</a>

.. |installed| raw:: html

   <a href="https://github.com/foglamp/FogLAMP#build-prerequisites" target="_blank">installed</a>

.. |build| raw:: html

   <a href="https://github.com/foglamp/FogLAMP#build" target="_blank">build</a>

.. |set| raw:: html

   <a href="https://github.com/foglamp/FogLAMP#testing-foglamp-from-your-development-environment" target="_blank">set</a>

.. =============================================

********************
FogLAMP System Tests
********************

System tests are the third category of test in FogLAMP. These test ensures that end to end flow of a FogLAMP system is
working as expected.

A typical example can be ingesting asset data in FogLAMP database, and sending to a cloud system with different set of
configuration rules.

Since these kinds of tests interacts between two or more heterogeneous systems, these are often slow in nature.

Running FogLAMP System tests
==============================

Test Prerequisites
------------------

Install the following prerequisites to run a System tests suite ::

   apt-get install jq

Also, foglamp must have:

   1. All dependencies |installed|
   2. |build|
   3. and FogLAMP_ROOT must be |set|


Test Execution
--------------

The complete documentation on the System test suite is available as this page |System Test Utility and Suites|.

Some tests suite, ``end_to_end_PI`` and ``end_to_end_OCS``, requires some information to be executed
like for example the PI-Server or the OCS account that should be used.

The configuration file ``suite.cfg``, available in each tests suite directory, should be edited proving
the information related to the specific environment.

Tests suite end_to_end_PI
+++++++++++++++++++++++++

The following variables should be properly updated ::

    export PI_SERVER=pi-server
    export PI_SERVER_PORT=5460
    export PI_SERVER_UID=pi-server-uid
    export PI_SERVER_PWD=pi-server-pwd
    export PI_SERVER_DATABASE=pi-server-db
    export CONNECTOR_RELAY_VERSION=x.x

    export OMF_PRODUCER_TOKEN=xxx

Tests suite end_to_end_OCS
++++++++++++++++++++++++++

The following variables should be properly update ::

    export OCS_TENANT="ocs_tenant_id"
    export OCS_CLIENT_ID="ocs_client_id"
    export OCS_CLIENT_SECRET="ocs_client_secret"

    export OCS_NAMESPACE="ocs_namespace_0001"

    export OCS_TOKEN="ocs_north_0001"



Samples execution
+++++++++++++++++

List the tests available in the ``smoke`` tests suite ::

    cd ${FOGLAMP_ROOT}/tests/system/suites
    ./foglamp-test smoke -l

Execute all the tests of the ``smoke`` tests suite ::

    cd ${FOGLAMP_ROOT}/tests/system/suites
    ./foglamp-test smoke

