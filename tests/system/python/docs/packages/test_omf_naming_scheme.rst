Test OMF Naming Scheme
~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed for basic testing north task of the `fledge-north-OMF` plugin. It incorporates the use of `fledge-south-coap` for ingesting data into Fledge and then sending it to the PI Server using north task of `fledge-north-OMF`.


This test comprises `TestOMFNamingScheme` Test class having multiple test cases functions:

1. **test_omf_with_concise_naming**: Test that ingest data into Fledge and check if north task is able to send it to PI Server when naming scheme is "concise".
2. **test_omf_with_type_suffix_naming**: Test that ingest data into Fledge and check if north task is able to send it to PI Server when naming scheme is "Use Type Suffix".
3. **test_omf_with_attribute_hash_naming**: Test that ingest data into Fledge and check if north task is able to send it to PI Server when naming scheme is "Use Attribute Hash".
4. **test_omf_with_backward_compatibility_naming**: Test that ingest data into Fledge and check if north task is able to send it to PI Server when naming scheme is "backward compatible".


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
  $ python3 -m pytest -s -vv packages/test_omf_naming_scheme.py --package-build-version="PACKAGE_BUILD_VERSION" --pi-host="PI_SYSTEM_HOST" \
        --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB"  --wait-time="WAIT_TIME" \
        --junit-xml="JUNIT_XML"
