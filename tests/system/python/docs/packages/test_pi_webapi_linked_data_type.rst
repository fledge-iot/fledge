Test PIWebAPI Linked Data Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed for the specific purpose of testing of Fledge by ingesting data into Fledge using the `fledge-south-coap` plugin and sending data to the PI Server using the `fledge-north-OMF` plugin in linked data type format.


This test comprises *Test_linked_data_PIWebAPI* class having multiple test cases functions:

1. **test_linked_data**: Test that data is ingested into Fledge using south services of `fledge-south-sinusoid` & `fledge-south-randomwalk` plugins and then sent to PI using north service of `fledgee-north-OMF` plugin in linked data type format. Additionally, confirms that the data sent and received counts match, required asset is created, data sent from Fledge through the OMF plugin successfully reaches the PI Server.
2. **test_linked_data_with_filter**: Test which verify that data is ingested into Fledge using the south services `fledge-south-sinusoid` and `fledge-south-randomwalk` plugins, with the `fledge-filter-expression` plugin attached to both. Ensure the data is sent to PI via the north service `fledge-north-OMF` in linked data type format. Additionally, confirms that the data sent and received counts match, required asset is created, data sent from Fledge through the OMF plugin successfully reaches the PI Server.
3. **test_linked_data_with_onoff_filter**: Test in which data is ingested into Fledge using the south services `fledge-south-sinusoid` and `fledge-south-randomwalk` plugins, with the `fledge-filter-expression` plugin attached to both. It ensure that the data is sent to PI via the north service `fledge-north-OMF` plugin in linked data type format when filters are being disabled and enabled multiple times. Additionally, confirms that the data sent and received counts match, required asset is created, data sent from Fledge through the OMF plugin successfully reaches the PI Server.


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
  $ python3 -m pytest -s -vv packages/test_pi_webapi_linked_data_type.py --package-build-version="PACKAGE_BUILD_VERSION" --pi-host="PI_SYSTEM_HOST" \
        --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB"  --wait-time="WAIT_TIME" \
        --junit-xml="JUNIT_XML"