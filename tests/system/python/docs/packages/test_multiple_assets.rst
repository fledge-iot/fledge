Test Multiple Assets
~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed for the specific purpose of creating large number of assets in Fledge using the fledge-south-benchmark plugin and then checking the stability of Fledge and ots components.


This test comprises *TestMultiAssets* class having multiple test cases functions:

1. **test_multiple_assets_with_restart**: Test whether Fledge can create multiple fledge-south-benchmark services with a large number of assets, and verify the assets and the stability of Fledge after restarting it.
2. **test_add_multiple_assets_before_after_restart**: Test whether Fledge can create a large number of assets before and after restarting of it, through multiple fledge-south-benchmark services.
3. **test_multiple_assets_with_reconfig**: Test whether Fledge can create a large number of assets through reconfiguration of fledge-south-benchmark services and remain stable.


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
                        Generic wait time between processes to run
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/
  $ python3 -m pytest -s -vv packages/test_multiple_assets.py --package-build-version="PACKAGE_BUILD_VERSION" --pi-host="PI_SYSTEM_HOST" \
        --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD"  --pi-db="PI_SYSTEM_DB" --num-assets="NUM_OF_ASSETS" \
        --wait-time="WAIT_TIME" --junit-xml="JUNIT_XML"