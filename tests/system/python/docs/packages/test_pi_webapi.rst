Test PIWebAPI
~~~~~~~~~~~~~

Objective
+++++++++
This test is designed for the specific purpose of testing of Fledge by ingesting data into Fledge using the `fledge-south-coap` plugin and sending it to the PI Server using the `fledge-north-OMF` plugin.


This test comprises *TestPackagesCoAP_PI_WebAPI* class having following test cases functions:

1. **test_omf_task**: Test that data is ingested into Fledge using service of `fledge-south-coap` and sent to PI using `fledgee-north-OMF` task, also verifies the data sent and received counts, checks whether the required asset is created, and ensures that the data sent from Fledge via the OMF plugin reaches the PI Server.
2. **test_omf_task_with_reconfig**: Test whether data is ingested into Fledge using the `fledge-south-coap` service and sent to the PI Server using the `fledge-north-OMF` task. Then, reconfigure the OMF task with an invalid user ID and verify if data transmission to the PI Server stops.


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
    --wait-time=WAIT_TIME
                        Generic wait time between processes to run
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_pi_webapi.py --package-build-version="PACKAGE_BUILD_VERSION" --pi-host="PI_SYSTEM_HOST" --pi-port="PI_SYSTEM_PORT" \
        --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB"  --wait-time="WAIT_TIME" --junit-xml="JUNIT_XML"