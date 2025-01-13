Test PIWebAPI Network Throttle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to verify the functionality of Fledge when ingesting data using the `fledge-south-sinusoid` plugin and sending it to the PI Server through the `fledge-north-OMF` plugin under a distorted network condition.

This test consists of *TestPackagesSinusoid_PI_WebAPI* class, which contains only one test case functions:

1. **test_omf_task**: Verifies that data is ingested into Fledge using the fledge-south-sinusoid plugin and sent to the PI Server using the fledge-north-OMF plugin, while simulating an impaired network scenario.


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
    --throttled-network-config=THROTTLED_NETWORK_CFG
                        Give config '{'rate_limit': '100','packet_delay': '50','interface': 'eth0'}' 
                        for causing a delay of 50 milliseconds and rate restriction of 100 kbps on interface eth0.
    --south-service-wait-time=SOUTH_SVC_WAIT_TIME
                        The time in seconds before which the south service should keep  on
                        sending data. After this time the south service will shutdown
    --north-catch-up-time=NORTH_CATCHUP_TIME
                        Time (in seconds) for which the north task/service will keep on running 
                        after switching off the south service.
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ export FLEDGE_ROOT=/usr/local/fledge
  $ export PYTHONPATH=$FLEDGE_ROOT/python 
  $ python3 -m pytest -s -v test_north_pi_webapi_nw_throttle.py --package-build-version="<PACKAGE_BUILD_VERSION>" --pi-host="<PI_SYSTEM_HOST>" \
      --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>" \
      --throttled-network-config="<THROTTLED_NETWORK_CFG>" --south-service-wait-time="<SOUTH_SVC_WAIT_TIME>" --north-catch-up-time="<NORTH_CATCHUP_TIME>" \
      --junit-xml="<JUNIT_XML>" 
