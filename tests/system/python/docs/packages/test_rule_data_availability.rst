Data Availability Rule Test
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test verifies the basic functionality of the notification rule for the `fledge-rule-DataAvailability` (inbuilt) plugin. It involves using `fledge-south-sinusoid` for data ingestion into Fledge and `fledge-north-OMF` for sending data to the PI server.

This test consists of three classes, each containing multiple test case functions:

1. **TestDataAvailabilityAuditBasedNotificationRuleOnIngress**: 
    a. **test_data_availability_multiple_audit**: Verifies if NTFSN is triggered with CONAD and SCHAD in Fledge.
    b. **test_data_availability_single_audit**: Verifies if NTFSN is triggered with CONCH in the sinusoid plugin.
    c. **test_data_availability_all_audit**: Verifies if NTFSN is triggered with all audit changes, referring to JIRA FOGL-7712.

2. **TestDataAvailabilityAssetBasedNotificationRuleOnIngress**:
    a. **test_data_availability_asset**: Verifies if the north service of OMF can send data to PI, ingested by the south service of sinusoid into Fledge, when a fledge-filter-scale filter is added to the north service.

3. **TestDataAvailabilityBasedNotificationRuleOnEgress**:
    a. **test_data_availability_north**: Verifies if NTFSN is triggered with configuration changes in the north EDS plugin. Please check FOGL-9355.


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
    --wait-time=WAIT_TIME
                        Generic wait time (in seconds) between processes
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_rule_data_availability.py --package-build-version="<PACKAGE_BUILD_VERSION>" --wait-time="<WAIT_TIME>" \
        --junit-xml="<JUNIT_XML>"
