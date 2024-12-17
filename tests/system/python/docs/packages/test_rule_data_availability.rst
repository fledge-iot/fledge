Test Rule Data Availability
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed for basic testing notification rule of the `fledge-rule-dataavailability` plugin. It incorporates the use of `fledge-south-sinusoid` for ingesting data into Fledge and `fledge-north-OMF` at north side for sending data to PI.


This test comprises following Test classes having multiple test cases functions:

1. **TestDataAvailabilityAuditBasedNotificationRuleOnIngress**: 
    a. **test_data_availability_multiple_audit**: Test that checks NTFSN triggered or not with CONAD, SCHAD in fledge.
    b. **test_data_availability_single_audit**: Test that checks NTFSN triggered or not with CONCH in sinusoid plugin.
    c. **test_data_availability_all_audit**: Test NTFSN triggered or not with all audit changes. Please check JIRA FOGL-7712.

2. **TestDataAvailabilityAssetBasedNotificationRuleOnIngress**:
    a. **test_data_availability_asset**: Test that checks whether north service of OMF is able to send data to PI, ingested by south service of sinuoid into Fledge, when filter of `fledge-filter-scale` is added to north service.

3. **TestDataAvailabilityBasedNotificationRuleOnEgress**:
    a. **test_data_availability_north**: Test NTFSN triggered or not with configuration change in north EDS plugin. Please check FOGL-9355.

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
    --wait-time=WAIT_TIME
                        Generic wait time between processes to run
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_rule_data_availability.py --package-build-version="PACKAGE_BUILD_VERSION" --wait-time="WAIT_TIME" \
        --junit-xml="JUNIT_XML"