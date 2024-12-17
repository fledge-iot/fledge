Test PIWebAPI
~~~~~~~~~~~~~

Objective
+++++++++
This test is designed for the specific purpose to perform testing with two Fledge instances running as a pair. Fledge(A) with the south service of `fledge-south-sinusoid`, which ingest data. This data is then sent to Fledge(B) using the `fledge-north-http-north` (python) plugin. Fledge(B) runs the `fledge-south-http` (Python) plugin to receive data from Fledge(A) and forwards it to the PI Server using the `fledge-north-OMF` plugin.


This test comprises *TestPythonNorthService* class having only one test cases functions:

1. **test_north_python_service_with_restart**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly before and after a Fledge restart.
2. **test_north_python_service_with_enable_disable**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly when disbling and then enabling its service.
3. **test_north_python_service_with_delete_add**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly when deleting and then adding its service.
4. **test_north_python_service_with_reconfig**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly when reconfiguring its service.
5. **test_north_python_service_with_filter**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly when adding `fledge-filter-scale` to its service.
6. **test_north_python_service_with_filter_enable_disable**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly when filter of `fledge-filter-scale` added to its service is disbaled then enabled.
7. **test_north_python_service_with_filter_reconfig**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly when filter of `fledge-filter-scale` added to its service is reconfigured.
8. **test_north_python_service_with_delete_add_filter**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly when filter of `fledge-filter-scale` added to its service is being first deleted then added again.
9. **test_north_python_service_with_filter_reorder**: This test verifies that Fledge(A) ingests data via the `south-sinusoid` plugin, sends it to Fledge(B) using the `north-httpc` plugin, and Fledge(B) forwards it to the PI Server. It ensures the `north-httpc` plugin sends data correctly when filters of `fledge-filter-scale` and `fledge-filter-metadata` added to its service is being reordered.


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
                        Generic wait time between processes to run
    --retries=RETIRES
                        Number of tries for polling
    --junit-xml=JUNIT_XML
                        Pytest XML report 
    --wait-fix="WAIT_FIX"
                        Extra wait time required for process to run

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python
  $ python3 -m pytest -s -vv pair/test_pyton_north_service_pair.py --package-build-version="PACKAGE_BUILD_VERSION" --remote-user="FLEDGE(B)_USER" \ 
      --remote-ip="FLEDGE(B)_IP" --key-path="KEY_PATH" --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD" --pi-host="PI_SYSTEM_HOST" \
      --pi-port="PI_SYSTEM_PORT" --pi-db="PI_SYSTEM_DB"  --wait-time="WAIT_TIME" --retries="RETIRES" --junit-xml="JUNIT_XML" --wait-fix="WAIT_FIX"