Test E2E CSV Multi Filter PI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing of Fledge by ingesting data into Fledge using the `fledge-south-playback` plugin from a csv, haiving a filters of `fledge-filter-scale`, `fledge-filter-asset`, `fledge-filter-rate`, `fledge-filter-delta`, `fledge-filter-rms` plugins attached to it and then sending data to the PI Server using the service of `fledge-north-OMF` plugin, having filter of `fledge-filter-threshold` plugin.


This test comprises *TestE2eCsvMultiFltrPi* class having only one test cases functions:

1. **test_end_to_end**: Test that checks data is inserted in Fledge using playback south plugin having filters of Delta, RMS, Rate, Scale, Asset & Metadata and sent to PI or not. It also verifies the data sent and received counts, checks whether the required asset is created, and ensures that the data sent from Fledge via the OMF plugin reaches the PI Server.


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
  $ python3 -m pytest -s -vv e2e/test_e2e_filter_fft_threshold.py --pi-host="PI_SYSTEM_HOST" --pi-port="PI_SYSTEM_PORT" --pi-admin="PI_SYSTEM_ADMIN" \
        --pi-passwd="PI_SYSTEM_PWD" --pi-db="PI_SYSTEM_DB" --wait-time="WAIT_TIME" --retries="RETIRES" --junit-xml="JUNIT_XML"