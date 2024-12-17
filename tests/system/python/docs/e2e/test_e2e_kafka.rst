Test Kafka
~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing of Fledge by ingesting data into Fledge using the `fledge-south-coap` plugin and sending it to the Kafka Server using the `fledge-north-kafka` plugin.


This test comprises *TestE2EKafka* class having only one test cases functions:

1. **test_end_to_end**: Test that data is ingested into Fledge via south service of `fledge-south-coap` plugin and sent to Kafka Server via `fledge-north-kafka` plugin, also verifies the data sent and received counts, checks whether the required asset is created, and ensures that the data sent from Fledge via the `fledge-north-kafka` plugin reaches the Kafka Server.


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

    --kafka-host=KAFKA_HOST
                        IP Address of Kafka Server
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
  $ python3 -m pytest -s -vv e2e/test_e2e_kafka.py --kafka-host="KAFKA_HOST" --wait-time="WAIT_TIME" --retries="RETIRES" --junit-xml="JUNIT_XML"