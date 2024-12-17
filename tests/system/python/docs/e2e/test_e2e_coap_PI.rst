Test E2E CoAP to PI Server
~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing of Fledge by ingesting data into Fledge using the `fledge-south-coap` plugin and sending it to the PI Server using the `fledge-north-OMF` plugin.


This test comprises *TestE2E_CoAP_PI* class having only one test cases functions:

1. **test_end_to_end**: Test that data is inserted in Fledge and sent to PI, also verifies the data sent and received counts, checks whether the required asset is created, and ensures that the data sent from Fledge via the OMF plugin reaches the PI Server.


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

  $ cd fledge/tests/system/python/ ; 
  $ export FLEDGE_ROOT=FLEDGE_ROOT_PATH 
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ python3 -m pytest -s -vv e2e/test_e2e_coap_PI.py --pi-host="PI_SYSTEM_HOST" --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" \
        --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB" --wait-time="WAIT_TIME" --retries="RETIRES" --junit-xml="JUNIT_XML"