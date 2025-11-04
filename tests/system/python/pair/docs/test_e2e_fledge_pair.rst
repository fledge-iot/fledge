E2E Fledge Pair Test
~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed for end-to-end validation between two Fledge instances, Fledge(A) and Fledge(B). Fledge(A) uses the fledge-south-sinusoid, fledge-south-expression, and fledge-south-playback south services to ingest data. This data is then transferred to Fledge(B) using the fledge-north-http-north plugin. Fledge(B) processes the data through the fledge-south-http plugin and forwards it to the PI Server via the fledge-north-OMF plugin.

This test consists *TestE2eFogPairPi* class, which contains a single test case function:

1. **test_end_to_end**: Verifies that data is ingested into Fledge(A) using the mentioned south plugins, sent to Fledge(B) via north-http plugin, Then Fledge(B) receive this data via http south and send to PI. Checks data integrity, asset creation, and ensures that data reaches the PI Server.

Prerequisite
++++++++++++

1. Fledge must be installed by `make` command
2. The FLEDGE_ROOT environment variable should be exported to the directory where Fledge is installed.
3. Install the prerequisites to run a test:

.. code-block:: console

  $ cd fledge/python
  $ python3 -m pip install -r requirements-test.txt --user

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
  $ export FLEDGE_ROOT=<path_to_fledge_installation> 
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ python3 -m pytest -s -vv pair/test_e2e_fledge_pair.py --remote-user="<FLEDGE(B)_USER>" --remote-ip="<FLEDGE(B)_IP>" --key-path="<KEY_PATH>" \
        --pi-host="<PI_SYSTEM_HOST>" --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>" \
        --wait-time="<WAIT_TIME>" --retries="<RETIRES>" --junit-xml="<JUNIT_XML>"
