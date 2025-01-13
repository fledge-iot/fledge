Test E2E Fledge Pair
~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed to perform end-to-end testing with two Fledge instances running as a pair. Fledge(A) having south services of fledge-south-sinusoid, fledge-south-expression, and fledge-south-playback, which ingest data. This data is then sent to Fledge(B) using the fledge-north-http-north plugin. Fledge(B) runs the fledge-south-http (Python) plugin to receive data from Fledge(A) and forwards it to the PI Server using the fledge-north-OMF plugin.
This test is specifically designed to perform end-to-end testing with two Fledge instances running as a pair. Fledge(A) has south services (fledge-south-sinusoid, fledge-south-expression, fledge-south-playback) to ingest data. This data is then sent to Fledge(B) using the fledge-north-http-north plugin. Fledge(B) receives data via the fledge-south-http plugin and forwards it to the PI Server using the fledge-north-OMF plugin.

This test consists *TestE2eExprPi* class, which contains only one test cases functions:

1. **test_end_to_end**: Verifies that data is ingested into Fledge(A) using the mentioned south plugins, sent to Fledge(B) via north-http plugin, Then Fledge(B) receive this data via http south and send to PI. Checks data integrity, asset creation, and ensures that data reaches the PI Server.

Prerequisite
++++++++++++

1. Fledge must be installed by `make` command
2. FLEDGE_ROOT environment variable should be exported to location where Fledge is installed.
3. Install the prerequisites to run a test:

.. code-block:: console

  $ cd fledge/python
  $ python3 -m pip install -r requirements-test.txt

The minimum required parameters to run,

.. code-block:: console

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

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/; 
  $ export FLEDGE_ROOT=FLEDGE_ROOT_PATH 
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ python3 -m pytest -s -vv pair/test_e2e_fledge_pair.py --remote-user="<FLEDGE(B)_USER>" --remote-ip="<FLEDGE(B)_IP>" --key-path="<KEY_PATH>" \
        --pi-host="<PI_SYSTEM_HOST>" --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>" \
        --wait-time="<WAIT_TIME>" --retries="<RETIRES>" --junit-xml="<JUNIT_XML>"
