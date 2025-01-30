C Based North Service Pair Test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed to validate data ingestion in Fledge(A) using the fledge-south-sinusoid plugin and its subsequent transfer to Fledge(B) via the fledge-north-httpc plugin. Fledge(B) processes this data through the fledge-south-http (Python) plugin and forwards it to the PI Server using the fledge-north-OMF plugin.
This test verifies the basic functionality and reliability of the fledge-north-httpc plugin, focusing on scenarios such as restarts, reconfigurations, and filter manipulations.

This test consists of *TestCNorthService* class, which contains multiple test case functions:

1. **test_north_C_service_with_restart**: Verifies that data ingested into Fledge(A) using fledge-south-sinusoid, sent to Fledge(B) using the fledge-north-httpc plugin, and that Fledge(B) forwards the data to the PI Server correctly, even after restarting Fledge(A).
2. **test_north_C_service_with_enable_disable**: Ensures that the fledge-north-httpc plugin sends data to Fledge(B) and the PI Server correctly after being disabled and then re-enabled in Fledge(A).
3. **test_north_C_service_with_delete_add**: Confirms that the fledge-north-httpc plugin continues to function correctly after being deleted and re-added in Fledge(A), with data successfully flowing to Fledge(B) and the PI Server.
4. **test_north_C_service_with_reconfig**: Validates that reconfiguring the fledge-north-httpc plugin in Fledge(A) does not disrupt the data flow to Fledge(B) and the PI Server. 
5. **test_north_C_service_with_filter**: Verifies that adding the fledge-filter-scale to the fledge-north-httpc plugin in Fledge(A) applies the filter correctly before forwarding the data to Fledge(B) and the PI Server.
6. **test_north_C_service_with_filter_enable_disable**: Ensures that disabling and re-enabling the fledge-filter-scale filter on the fledge-north-httpc plugin in Fledge(A) does not disrupt data transformation or flow to Fledge(B) and the PI Server.
7. **test_north_C_service_with_filter_reconfig**: Confirms that reconfiguring the fledge-filter-scale filter on the fledge-north-httpc plugin applies the updated configuration correctly while maintaining data flow to Fledge(B) and the PI Server.
8. **test_north_C_service_with_delete_add_filter**: Ensures that deleting and re-adding the fledge-filter-scale filter to the fledge-north-httpc plugin in Fledge(A) does not affect the data flow or transformation, with data reaching Fledge(B) and the PI Server as expected.
9. **test_north_C_service_with_filter_reorder**: Verifies that reordering filters (e.g., fledge-filter-scale and fledge-filter-metadata) applied to the fledge-north-httpc plugin updates the processing sequence correctly, with data accurately processed and forwarded to Fledge(B) and the PI Server.


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
    --remote-user=FLEDGE(B)_USER
                        Username of remote machine on which Fledge(B) is running
    --remote-ip=FLEDGE(B)_IP
                        IP of remote machine on which Fledge(B) is running
    --key-path=KEY_PATH
                        Path of the key required to access remote machine on which Fledge(B) is running
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
    --retries=RETIRES
                        Number of tries for polling
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.
    --wait-fix="<WAIT_FIX"
                        Extra wait time (in seconds) required for process to run

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv pair/test_c_north_service_pair.py --package-build-version="<PACKAGE_BUILD_VERSION>" --remote-user="<FLEDGE(B)_USER>" \ 
      --remote-ip="<FLEDGE(B)_IP>" --key-path="<KEY_PATH>" --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>" --pi-host="<PI_SYSTEM_HOST>" \
      --pi-port="<PI_SYSTEM_PORT>" --pi-db="<PI_SYSTEM_DB>"  --wait-time="<WAIT_TIME>" --retries="<RETIRES>" --junit-xml="<JUNIT_XML>"  --wait-fix="<WAIT_FIX>"
