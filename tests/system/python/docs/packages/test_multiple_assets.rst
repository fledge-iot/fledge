Test Multiple Assets
~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to validate Fledge's ability to handle the creation of a large number of assets using the fledge-south-benchmark plugin while ensuring the stability of Fledge and its components.

This test consists of *TestMultiAssets* class, which contains multiple test case functions:

1. **test_multiple_assets_with_restart**: Verifies that Fledge can create multiple fledge-south-benchmark services with a large number of assets, ensures the assets are correctly created, and checks the stability of Fledge after a restart.
2. **test_add_multiple_assets_before_after_restart**: Ensures Fledge's ability to create a large number of assets both before and after restarting, using multiple fledge-south-benchmark services.
3. **test_multiple_assets_with_reconfig**: Tests the creation of a large number of assets through the reconfiguration of fledge-south-benchmark services and confirms Fledge's stability during and after the reconfiguration .


Prerequisite
++++++++++++

Install the prerequisites to run a test:

.. code-block:: console

  $ cd fledge/python
  $ python3 -m pip install -r requirements-test.txt


The minimum required parameters to run,

.. code-block:: console

    --package-build-version=PACKAGE_BUILD_VERSION
                        Package build version for http://archives.fledge-iot.org/
    --pi-host=PI_SYSTEM_HOST
                        PI Server HostName/IP
    --pi-port=PI_SYSTEM_PORT
                        PI Server port
    --pi-admin=PI_SYSTEM_ADMIN
                        PI Server user login
    --pi-passwd=PI_SYSTEM_PWD
                        PI Server user login password
    --pi-db=PI_SYSTEM_DB
                        PI Server Database
    --num-assets=NUM_OF_ASSETS
                        Total No. of Assets to be created
    --wait-time=WAIT_TIME
                        Generic wait time (in seconds) between processes
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/
  $ python3 -m pytest -s -vv packages/test_multiple_assets.py --package-build-version="<PACKAGE_BUILD_VERSION>" --pi-host="<PI_SYSTEM_HOST>" \
      --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>"  --pi-db="<PI_SYSTEM_DB>" --num-assets="<NUM_OF_ASSETS>" \
      --wait-time="<WAIT_TIME>" --junit-xml="<JUNIT_XML>"
