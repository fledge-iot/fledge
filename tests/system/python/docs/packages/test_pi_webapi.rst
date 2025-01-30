Test PIWebAPI
~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to verify that data ingested into Fledge using the `fledge-south-coap` plugin is successfully sent to the PI Server in complex(legacy) data type format using the `fledge-north-OMF` plugin.

This test consists of *TestPackagesCoAP_PI_WebAPI* class, which contains following test case functions:

1. **test_omf_task**: Verifies that data is ingested into Fledge using the fledge-south-coap service and sent to the PI Server via the fledge-north-OMF task. It checks that the data sent and received counts match, the required asset is created, and that the data sent from Fledge through the OMF plugin successfully reaches the PI Server.
2. **test_omf_task_with_reconfig**: Verifies that data is ingested into Fledge using the fledge-south-coap service and sent to the PI Server via the fledge-north-OMF task. Then, it reconfigures the OMF task with an invalid user ID to verify whether data transmission to the PI Server stops.


Prerequisite
++++++++++++

Install the prerequisites to run a test:

.. code-block:: console

  $ cd fledge/python
  $ python3 -m pip install -r requirements-test.txt --user


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
                        Generic wait time (in seconds) between processes
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_pi_webapi.py --package-build-version="<PACKAGE_BUILD_VERSION>" --pi-host="<PI_SYSTEM_HOST>" --pi-port="<PI_SYSTEM_PORT>" \
     --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>"  --wait-time="<WAIT_TIME>" --junit-xml="<JUNIT_XML>"
