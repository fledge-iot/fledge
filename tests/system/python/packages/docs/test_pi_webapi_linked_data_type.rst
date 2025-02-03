Test PIWebAPI Linked Data Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to verify that data ingested into Fledge using the `fledge-south-sinusoid` and `fledge-south-randomwalk` plugins is successfully sent to the PI Server in linked data type format using the `fledge-north-OMF` plugin.

This test consists of *Test_linked_data_PIWebAPI* class, which contains multiple test cases functions:

1. **test_linked_data**: Verifies that data is ingested into Fledge using fledge-south-sinusoid and fledge-south-randomwalk plugins and then sent to the PI Server in linked data format using the fledge-north-OMF plugin. It also checks that the data sent and received counts match, the required asset is created, and the data successfully reaches the PI Server.  
2. **test_linked_data_with_filter**: Verifies that data is ingested into Fledge using fledge-south-sinusoid and fledge-south-randomwalk plugins, with fledge-filter-expression applied, and sent to PI via the fledge-north-OMF plugin. It ensures that data sent and received counts match, the required asset is created, and the data successfully reaches the PI Server.
3. **test_linked_data_with_onoff_filter**: Verifies that data is ingested into Fledge using fledge-south-sinusoid and fledge-south-randomwalk plugins, with fledge-filter-expression applied. The test ensures data is sent to PI via the fledge-north-OMF plugin in linked data format when filters are disabled and enabled multiple times. It confirms data sent and received counts match, the required asset is created, and the data successfully reaches the PI Server.


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
  $ python3 -m pytest -s -vv packages/test_pi_webapi_linked_data_type.py --package-build-version="<PACKAGE_BUILD_VERSION>" --pi-host="<PI_SYSTEM_HOST>" \
      --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>"  --wait-time="<WAIT_TIME>" \
      --junit-xml="<JUNIT_XML>"
