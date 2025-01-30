Test OMF North Service
~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to verify the basic functionality of the `fledge-north-OMF` plugin's north service, incorporating the use of `fledge-south-sinusoid` for ingesting data into Fledge, and `fledge-filter-scale` & `fledge-filter-metadata` filters to validate the handling of multiple filters at the north service.

This test consists of two classes, each contains multiple test cases functions:

1. **TestOMFNorthService**: 
    a. **test_omf_service_with_restart**: Verify that the north service of OMF is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, both before and after restarting Fledge.
    b. **test_omf_service_with_enable_disable**: Verify that the north service of OMF is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, when the service is disabled and then re-enabled.
    c. **test_omf_service_with_delete_add**: Verify that the north service of OMF is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, when its service is deleted and then re-added.
    d. **test_omf_service_with_reconfig**: Verify that the north service of OMF is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, after the service is reconfigured to invalid credentials.

2. **TestOMFNorthServicewithFilters**:
    a. **test_omf_service_with_filter**: Verify that the north service of OMF is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, when a fledge-filter-scale filter is added.
    b. **test_omf_service_with_disable_enable_filter**: Verify that the north service of OMF is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, when the fledge-filter-scale filter is disabled and then re-enabled.
    c. **test_omf_service_with_filter_reconfig**: Verify that the north service of OMF is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, when the fledge-filter-scale filter is reconfigured.
    d. **test_omf_service_with_delete_add**: Verify that the north service of OMF, with the fledge-filter-scale filter, is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, when its service is deleted and then re-added.
    e. **test_omf_service_with_delete_add_filter**: Verify that the north service of OMF, with the fledge-filter-scale filter, is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, when the filter is deleted and then re-added.
    f. **test_omf_service_with_filter_reorder**: Verify that the north service of OMF, with the fledge-filter-scale and fledge-filter-metadata filters, is able to send data to PI, ingested by the fledge-south-sinusoid service in Fledge, when the filters are reordered in the pipeline.


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
    --wait-fix=WAIT_FIX
                        Extra wait time (in seconds) required for process to run
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_omf_north_service.py --package-build-version="<PACKAGE_BUILD_VERSION>" --pi-host="<PI_SYSTEM_HOST>" \
      --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>"  --wait-time="<WAIT_TIME>" \
      --wait-fix="<WAIT_FIX>" --junit-xml="<JUNIT_XML>"
