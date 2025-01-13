Test Rule Data Availability
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test verifies the basic functionality of the statistics history notification using `fledge-rule-Threshold` plugin, which utilizes `fledge-south-sinusoid` for data ingestion into Fledge and `fledge-north-OMF` for sending data to the PI server.

This test consists of two classes, each containing multiple test case functions:

1. **TestStatisticsHistoryBasedNotificationRuleOnIngress**: 
    a. **test_stats_readings_south**: Verifies if NTFSN is triggered with source as statistics history and name as READINGS in threshold rule.
    b. **test_stats_south_asset_ingest**: Verifies if NTFSN is triggered with source as statistics history and name as "ingested south asset>" in the threshold rule.
    c. **test_stats_south_asset**: Verifies if NTFSN is triggered with source as statistics history and name as the south asset name in the threshold rule.

2. **TestStatisticsHistoryBasedNotificationRuleOnEgress**:
    a. **test_stats_readings_north**: Verifies if NTFSN is triggered with source as statistics history and name as READINGS in the threshold rule


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
                        Generic wait time (in seconds) between processes
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_statistics_history_notification_rule.py --package-build-version="<PACKAGE_BUILD_VERSION>" --pi-host="<PI_SYSTEM_HOST>" \
        --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>" --wait-time="<WAIT_TIME>" \
        --junit-xml="<JUNIT_XML>"
