Test North Azure
~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed for testing of the `fledge-north-azure` plugin. It incorporates the use of `fledge-south-systeminfo` for ingesting data into Fledge and add `fledge-filter-expression` to north side to verify Fledge's stability when service or task of `fledge-north-azure` is sending data to Azure-IoT-Hub.

This test comprises following Test classes having multiple test cases functions:

1. **TestNorthAzureIoTHubDevicePlugin**: 
    a. **test_send**: Test that check data is inserted in Fledge and sent to Azure-IoT Hub or not.
    b. **test_mqtt_over_websocket_reconfig**: Test that enable MQTT over websocket then check data inserted into Fledge and sent to Azure-IoT Hub or not.
    c. **test_disable_enable**: Test that enable and disable south and north service perioically then check data inserted into Fledge and sent to Azure-IoT Hub or not.
    d. **test_send_with_filter**: Test that attach filters to North service and enable and disable filter periodically then check data inserted into Fledge and sent to Azure-IoT Hub or not.

2. **TestNorthAzureIoTHubDevicePluginTask**:
    a. **test_send_as_a_task**: Test that creates south and north bound as task and check data is inserted in Fledge and sent to Azure-IoT Hub or not.
    b. **test_mqtt_over_websocket_reconfig_task**: Test that creates south and north bound as task as well as enable MQTT over websocket then check data inserted in Fledge and sent to Azure-IoT Hub or not.
    c. **test_disable_enable_task**: Test that creates south and north bound as task as enable and disable them periodically then check data inserted in Fledge and sent to Azure-IoT Hub or not.
    d. **test_send_with_filter_task**: Test that creates south and north bound as task and attach filters to North Bound as well as enable and disable filters periodically then check data inserted in Fledge and sent to Azure-IoT Hub or not.

3. **TestNorthAzureIoTHubDevicePluginInvalidConfig**:
    a. **test_invalid_connstr**: Test that checks connection string of north azure plugin is invalid or not.
    b. **test_invalid_connstr_sharedkey**: Test that checks shared key passed to connection string of north azure plugin is invalid or not.

4. **TestNorthAzureIoTHubDevicePluginLongRun**:
    a. **test_send_long_run**: Test that check data is inserted in Fledge and sent to Azure-IoT Hub for long duration based parameter passed.


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
    --azure-host=AZURE_HOST
                        Azure-IoT Host Name
    --azure-device=AZURE_DEVICE
                        Azure-IoT Device ID
    --azure-key=AZURE_KEY
                        Azure-IoT SharedAccess key
    --azure-storage-account-url=AZURE_STORAGE_URL
                        Azure Storage Account URL
    --azure-storage-account-key=AZURE_STORAGE_KEY
                        Azure Storage Account Access Key
    --azure-storage-container=AZURE_STORAGE_CONTAINER
                        Container Name in Azure where data is stored
    --wait-time=WAIT_TIME
                        Generic wait time between processes to run
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_north_azure.py --package-build-version="PACKAGE_BUILD_VERSION" --azure-host="AZURE_HOST" \
        --azure-device="AZURE_DEVICE" --azure-key="AZURE_KEY" --azure-storage-account-url="AZURE_STORAGE_URL" --azure-storage-account-key="AZURE_STORAGE_KEY" \
        --azure-storage-container="AZURE_STORAGE_CONTAINER" --wait-time="WAIT_TIME" --junit-xml="JUNIT_XML" 