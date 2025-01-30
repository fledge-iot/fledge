Test Kafka
~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing of Fledge by ingesting data into Fledge using the `fledge-south-coap` plugin and sending it to the Kafka Server using the `fledge-north-kafka` plugin.


This test consists of *TestE2EKafka* class, which contains a single test case function:

1. **test_end_to_end**: Verifies that data is ingested into Fledge through the south service of the fledge-south-coap plugin and sent to the Kafka Server via the fledge-north-kafka plugin. It also checks the data sent and received counts, ensures the required asset is created, and confirms that the data sent from Fledge via the fledge-north-kafka plugin reaches the Kafka Server.


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

    --kafka-host=KAFKA_HOST
                        IP Address of Kafka Server
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
  $ python3 -m pytest -s -vv e2e/test_e2e_kafka.py --kafka-host="<KAFKA_HOST>" --wait-time="<WAIT_TIME>" --retries="<RETIRES>" --junit-xml="<JUNIT_XML>"
