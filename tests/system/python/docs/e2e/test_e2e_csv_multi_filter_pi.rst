Test E2E CSV Multi Filter PI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing of Fledge by ingesting data into Fledge using the `fledge-south-playback` plugin from a CSV file, with filters of the `fledge-filter-scale`, `fledge-filter-asset`, `fledge-filter-rate`, `fledge-filter-delta`, and `fledge-filter-rms` plugins attached. The data is then sent to the PI Server using the service of the `fledge-north-OMF` plugin, which has the `fledge-filter-threshold` plugin attached.

This test consists of *TestE2eCsvMultiFltrPi* class, which contains only one test cases functions:

1. **test_end_to_end**: Verifies that data is inserted into Fledge using the playback south plugin with filters for Delta, RMS, Rate, Scale, Asset, and Metadata, and then sent to PI. It also checks the data sent and received counts, verifies the creation of the required asset, and ensures that the data sent from Fledge via the OMF plugin reaches the PI Server.


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
                        Generic wait time (in seconds) between processes
    --retries=RETIRES
                        Number of tries for polling
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/ ; 
  $ export FLEDGE_ROOT=FLEDGE_ROOT_PATH 
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ python3 -m pytest -s -vv e2e/test_e2e_filter_fft_threshold.py --pi-host="<PI_SYSTEM_HOST>" --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" \
      --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>" --wait-time="<WAIT_TIME>" --retries="<RETIRES>" --junit-xml="<JUNIT_XML>"
