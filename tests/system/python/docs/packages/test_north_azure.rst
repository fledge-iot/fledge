Test North Azure
~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed to verify the functionality and stability of the `fledge-north-azure`` plugin. It uses the `fledge-south-systeminfo`` plugin for ingesting data into Fledge and applies the `fledge-filter-expression`` on the north side to validate that the data is sent to Azure IoT Hub successfully, while ensuring Fledge remains stable when the service or task of fledge-north-azure sends data.

This test consists of four classes, each contains multiple test case functions:

1. **TestNorthAzureIoTHubDevicePlugin**: 
    a. **test_send**: Verifies that data is successfully ingested into Fledge and sent to Azure IoT Hub.
    b. **test_mqtt_over_websocket_reconfig**: Enables MQTT over websocket then verify whether data ingested into Fledge, sent to Azure-IoT Hub.
    c. **test_disable_enable**: Verifies that enabling and disabling the south and north services periodically does not affect data transmission to Azure IoT Hub.
    d. **test_send_with_filter**: Verifies the impact of enabling and disabling fledge-filter-expression on the north service while ensuring data is still sent to Azure IoT Hub.

2. **TestNorthAzureIoTHubDevicePluginTask**:
    a. **test_send_as_a_task**: Creates south and north bound as task and check if data is ingested in Fledge and sent to Azure-IoT Hub.
    b. **test_mqtt_over_websocket_reconfig_task**: Verifies that data sent to Azure IoT Hub with MQTT over WebSocket enabled, when south and north services are configured as tasks.
    c. **test_disable_enable_task**: Verifies that enabling and disabling south and north services configured as tasks does not impact data transmission to Azure IoT Hub.
    d. **test_send_with_filter_task**: Ensures that applying and toggling filters on the north task does not affect data being sent to Azure IoT Hub.

3. **TestNorthAzureIoTHubDevicePluginInvalidConfig**:
    a. **test_invalid_connstr**: Checks if the connection string for the north Azure plugin is valid.
    b. **test_invalid_connstr_sharedkey**: Verifies if the shared key in the connection string for the north Azure plugin is valid.

4. **TestNorthAzureIoTHubDevicePluginLongRun**:
    a. **test_send_long_run**: Verifies that data is continuously sent to Azure IoT Hub over a long period, based on parameters passed.


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
                        Generic wait time (in seconds) between processes
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv packages/test_north_azure.py --package-build-version="<PACKAGE_BUILD_VERSION>" --azure-host="<AZURE_HOST>" \
        --azure-device="<AZURE_DEVICE>" --azure-key="<AZURE_KEY>" --azure-storage-account-url="<AZURE_STORAGE_URL>" --azure-storage-account-key="<AZURE_STORAGE_KEY>" \
        --azure-storage-container="<AZURE_STORAGE_CONTAINER>" --wait-time="<WAIT_TIME>" --junit-xml="<JUNIT_XML>"
