Test PIWebAPI Network Throttle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed for the specific purpose of testing of Fledge by ingesting data into Fledge using the `fledge-south-sinusoid` plugin and sending it to the PI Server using the `fledge-north-OMF` plugin under a distorted network.


This test comprises *TestPackagesSinusoid_PI_WebAPI* class having only one test cases functions:

1. **test_omf_task**: Test that checks data is inserted in Fledge using south service of `fledge-south-sinusoid` plugin and sent to PI using north service of `fledgee-north-OMF` plugiin under an impaired network.

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
    --throttled-network-config="THROTTLED_NETWORK_CFG"
                        Give config '{'rate_limit': '100','packet_delay': '50','interface': 'eth0'}' 
                        for causing a delay of 50 milliseconds and rate restriction of 100 kbps on interface eth0.
    --south-service-wait-time="SOUTH_SVC_WAIT_TIME" 
                        The time in seconds before which the south service should keep  on
                        sending data. After this time the south service will shutdown
    --north-catch-up-time="NORTH_CATCHUP_TIME"
                        The time in seconds we will allow the north task /service to keep on running 
                        after switching off the south service.
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ export FLEDGE_ROOT=/usr/local/fledge
  $ export PYTHONPATH=$FLEDGE_ROOT/python 
  $ python3 -m pytest -s -v test_north_pi_webapi_nw_throttle.py --package-build-version="PACKAGE_BUILD_VERSION" --pi-host="PI_SYSTEM_HOST" \
        --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB" \
        --throttled-network-config="THROTTLED_NETWORK_CFG" --south-service-wait-time="SOUTH_SVC_WAIT_TIME" --north-catch-up-time="NORTH_CATCHUP_TIME" \
        --junit-xml="JUNIT_XML" 