Test E2E Fledge Pair
~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing with two Fledge instances running as a pair. Fledge(A) having south services of fledge-south-sinusoid, fledge-south-expression, and fledge-south-playback, which ingest data. This data is then sent to Fledge(B) using the fledge-north-http-north plugin. Fledge(B) runs the fledge-south-http (Python) plugin to receive data from Fledge(A) and forwards it to the PI Server using the fledge-north-OMF plugin.


This test comprises *TestE2eExprPi* class having only one test cases functions:

1. **test_end_to_end**: Test that data is ingested in Fledge(A) using playback, sinusoid, and expression south plugin and sent to Fledge(B) via http-north (filter only playback data). Then Fledge(B) receive this data via http south and send to PI, also verifies the data sent and received counts, checks whether the required asset is created, and ensures that the data sent from Fledge via the `fledge-north-OMF` plugin reaches the Kafka Server.


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
                        Generic wait time between processes to run
    --retries=RETIRES
                        Number of tries for polling
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/; 
  $ export FLEDGE_ROOT=FLEDGE_ROOT_PATH 
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ python3 -m pytest -s -vv pair/test_e2e_fledge_pair.py --remote-user="FLEDGE(B)_USER" --remote-ip="FLEDGE(B)_IP" --key-path="KEY_PATH" \
        --pi-host="PI_SYSTEM_HOST" --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB" \
        --wait-time="WAIT_TIME" --retries="RETIRES" --junit-xml="JUNIT_XML"
