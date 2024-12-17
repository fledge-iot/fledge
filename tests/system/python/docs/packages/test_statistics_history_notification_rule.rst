Test Rule Data Availability
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed for basic testing notification rule of the `fledge-rule-dataavailability` plugin. It incorporates the use of `fledge-south-sinusoid` for ingesting data into Fledge and `fledge-north-OMF` at north side for sending data to PI.


This test comprises following Test classes having multiple test cases functions:

1. **TestStatisticsHistoryBasedNotificationRuleOnIngress**: 
    a. **test_stats_readings_south**: Test NTFSN triggered or not with source as statistics history and name as READINGS in threshold rule.
    b. **test_stats_south_asset_ingest**: Test NTFSN triggered or not with source as statistics history and name as ingested south asset in threshold rule.
    c. **test_stats_south_asset**: Test NTFSN triggered or not with source as statistics history and name as south asset name in threshold rule.

2. **TestStatisticsHistoryBasedNotificationRuleOnEgress**:
    a. **test_stats_readings_north**: Test NTFSN triggered or not with source as statistics history and name as READINGS in threshold rule.

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
    --wait-time=WAIT_TIME
                        Generic wait time between processes to run
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_statistics_history_notification_rule.py --package-build-version="PACKAGE_BUILD_VERSION" --pi-host="PI_SYSTEM_HOST" \
        --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB" --wait-time="WAIT_TIME" \
        --junit-xml="JUNIT_XML"