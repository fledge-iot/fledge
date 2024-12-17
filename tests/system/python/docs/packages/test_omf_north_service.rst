Test OMF North Service
~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed for basic testing north service of the `fledge-north-OMF` plugin. It incorporates the use of `fledge-south-sinusoid` for ingesting data into Fledge and `fledge-filter-scale` & `fledge-filter-metadata` to verify Fledge's ability to handle multiple filters at north service of `fledge-north-OMF`.


This test comprises following Test classes having multiple test cases functions:

1. **TestOMFNorthService**: 
    a. **test_omf_service_with_restart**: Test that checks whether north service of OMF is able to send data to PI, ingested by south service of sinuoid into Fledge, both before and after restarting Fledge.
    b. **test_omf_service_with_enable_disable**: Test that checks whether north service of OMF is able to send data to PI, ingested by south service of sinuoid into Fledge, when it is disblaed and then enabled.
    c. **test_omf_service_with_delete_add**: Test that checks whether north service of OMF is able to send data to PI, ingested by south service of sinuoid into Fledge, when its service is deleted and re-add.
    d. **test_omf_service_with_reconfig**: Test that checks whether north service of OMF is able to send data to PI, ingested by south service of sinuoid into Fledge, its service reconfigured to invalid credentials.

2. **TestOMFNorthServicewithFilters**:
    a. **test_omf_service_with_filter**: Test that checks whether north service of OMF is able to send data to PI, ingested by south service of sinuoid into Fledge, when filter of `fledge-filter-scale` is added to north service.
    b. **test_omf_service_with_disable_enable_filter**: Test that checks whether north service of OMF is able to send data to PI, ingested by south service of sinuoid into Fledge, when filter of `fledge-filter-scale` is added to north service is disbled then enabled.
    c. **test_omf_service_with_filter_reconfig**: Test that checks whether north service of OMF is able to send data to PI, ingested by south service of sinuoid into Fledge, when filter of `fledge-filter-scale` is added to north service is reconfigured.
    d. **test_omf_service_with_delete_add**: Test that checks whether north service of OMF having filter of `fledge-filter-scale`, is able to send data to PI, ingested by south service of sinuoid into Fledge, when its service is deleted then re-add.
    e. **test_omf_service_with_delete_add_filter**: Test that checks whether north service of OMF having filter of `fledge-filter-scale`, is able to send data to PI, ingested by south service of sinuoid into Fledge, when its filter is being deleted then re-add.
    f. **test_omf_service_with_filter_reorder**: Test that checks whether north service of OMF having filters of `fledge-filter-scale` and `fledge-filter-metadata`, is able to send data to PI, ingested by south service of sinuoid into Fledge, when its filters are being reorder in pipeline.


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
    --wait-fix="WAIT_FIX"
                        Extra wait time required for process to run
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_omf_north_service.py --package-build-version="PACKAGE_BUILD_VERSION" --pi-host="PI_SYSTEM_HOST" \
        --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB"  --wait-time="WAIT_TIME" \
        --wait-fix="WAIT_FIX" --junit-xml="JUNIT_XML"