E2E Filter with FFT Threshold Test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing of Fledge by ingesting data from a CSV file into Fledge using the `fledge-south-playback` plugin, with the `fledge-filter-fft` plugin attached. The data is then sent to the PI Server using the `fledge-north-OMF` plugin, with the `fledge-filter-threshold` plugin applied.

This test consists of *TestE2eFilterFFTThreshold* class, which contains a single test case function:

1. **test_e2e_csv_pi**: Verifies that data is ingested into Fledge using the playback south plugin with an FFT filter, then sent to PI after passing through the threshold filter. It checks the data sent and received counts, ensures the required asset is created, and confirms that the data sent from Fledge via the OMF plugin reaches the PI Server.


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
  $ export FLEDGE_ROOT=<path_to_fledge_installation> 
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ python3 -m pytest -s -vv e2e/test_e2e_filter_fft_threshold.py --pi-host="<PI_SYSTEM_HOST>" --pi-port="<PI_SYSTEM_PORT>" --pi-admin="<PI_SYSTEM_ADMIN>" \
      --pi-passwd="<PI_SYSTEM_PWD>" --pi-db="<PI_SYSTEM_DB>" --wait-time="<WAIT_TIME>" --retries="<RETIRES>" --junit-xml="<JUNIT_XML>"
