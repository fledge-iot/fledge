
.. |pytest| raw:: html

   <a href="https://docs.pytest.org/en/latest/#" target="_blank">pytest</a>

.. |installed| raw:: html

   <a href="https://github.com/foglamp/FogLAMP#build-prerequisites" target="_blank">installed</a>

.. |build| raw:: html

   <a href="https://github.com/foglamp/FogLAMP#build" target="_blank">build</a>

.. |set| raw:: html

   <a href="https://github.com/foglamp/FogLAMP#testing-foglamp-from-your-development-environment" target="_blank">set</a>

.. |kafka-build| raw:: html

   <a href="https://github.com/foglamp/foglamp-north-kafka#build" target="_blank">kafka-build</a>

.. |confluent| raw:: html

   <a href="https://www.confluent.io/download/" target="_blank">confluent</a>

.. |Confluent CLI| raw:: html

   <a href="https://docs.confluent.io/current/cli/command-reference/index.html" target="_blank">Confluent CLI</a>

.. |REST Proxy| raw:: html

   <a href="https://docs.confluent.io/current/kafka-rest/docs/quickstart.html" target="_blank">REST Proxy QuickStart</a>

.. =============================================

*******************************************
FogLAMP System Tests using pytest framework
*******************************************

System tests are the third category of test in FogLAMP. These test ensures that end to end flow of a FogLAMP system is
working as expected.

A typical example can be ingesting asset data in FogLAMP database, and sending to a cloud system with different set of
configuration rules.

Since these kinds of tests interacts between two or more heterogeneous systems, these are often slow in nature.

FogLAMP uses python |pytest| framework to execute the system tests. To contribute to system test, a developer should
be comfortable in writing tests in pytest.

Running FogLAMP System tests
============================

Test Prerequisites
------------------

Install the following prerequisites to run a System test ::

   pip3 install pytest

Also, FogLAMP must have:

   1. All dependencies |installed|
   2. |build|
   3. and FogLAMP_ROOT must be |set|


Test Execution
--------------

Some tests, like ``test_e2e_coap_PI.py`` , requires some information to be provided
for example the PI-Server or the OCS account that should be used. This information can be passed though command
like during test execution. For e.g., ::

    /FogLAMP/tests/system/python $ pytest test_e2e_coap_PI.py
    --pi-db=<PI DB name>
    --pi-host=<Hostname/IP of PI Server>
    --pi-admin=<Login of PI Machine>
    --pi-passwd=<Password of PI Machine>
    --pi-token="<PI Producer token>"

These command line arguments and their help can be seen typing ``pytest --help`` from console, refer section
custom options ::

    $ pytest --help
    ...
    custom options:
    --south-branch=SOUTH_BRANCH
                        south branch name
    --north-branch=NORTH_BRANCH
                        north branch name
    --foglamp-url=FOGLAMP_URL
                        FogLAMP client api url
    --use-pip-cache=USE_PIP_CACHE
                        use pip cache is requirement is available
    --pi-host=PI_HOST     PI Server Host Name/IP
    --pi-port=PI_PORT     PI Server Port
    --pi-db=PI_DB         PI Server database
    --pi-admin=PI_ADMIN   PI Server user login
    --pi-passwd=PI_PASSWD PI Server user login password
    --pi-token=PI_TOKEN   OMF Producer Token
    --south-plugin=SOUTH_PLUGIN
                        Name of the South Plugin
    --south-service-name=SOUTH_SERVICE_NAME
                        Name of the South Service
    --north-plugin=NORTH_PLUGIN
                        Name of the North Plugin
    --asset-name=ASSET_NAME
                        Name of asset
    --wait-time=WAIT_TIME
                        Generic wait time between processes to run
    --retries=RETRIES     Number of tries to make to fetch data from PI web api
    --kafka-host=KAFKA_HOST
                        Kafka Server Host Name/IP
    --kafka-port=KAFKA_PORT
                        Kafka Server Port
    --kafka-topic=KAFKA_TOPIC
                        Kafka topic
    --kafka-rest-port=KAFKA_REST_PORT
                        Kafka Rest Proxy Port


Test test_e2e_coap_PI and test_e2e_csv_PI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The minimum required parameters to run these tests are ::

    --pi-db=<PI DB name>
    --pi-host=<Hostname/IP of PI Server>
    --pi-port=<PI Server Port>
    --pi-admin=<Login of PI Machine>
    --pi-passwd=<Password of PI Machine>
    --pi-token="<PI Producer token>"


Test test_e2e_kafka
~~~~~~~~~~~~~~~~~~~

Prerequisite
++++++++++++

Install the following prerequisites to run a test,

  1. Kafka is built from |kafka-build|
  2. Download Confluent Community Edition from |confluent|. You can use the |Confluent CLI| installation methods to quickly get a single-node Confluent Platform development environment up and running; Start by running the |REST Proxy| and the services it depends on: ZooKeeper, Kafka

  Below are the minimal services required for the test ::

    $ /opt/confluent-5.1.0/bin/confluent start zookeeper
    $ /opt/confluent-5.1.0/bin/confluent start kafka
    $ /opt/confluent-5.1.0/bin/confluent start kafka-rest

  NOTE: By default Listen Ports are 2181, 9092, 8082, If any conflicts with your environment setup. You may change port properties from ::

          /opt/confluent-5.1.0/etc
          kafka/server.properties
          kafka/zookeeper.properties
          kafka-rest/kafka-rest.properties

The minimum required parameters to run ::

    --kafka-host=<Hostname/IP of Kafka Server>
    --kafka-port=<Kafka Server Port>
    --kafka-topic=<Kafka topic>
    --kafka-rest-port=<Kafka Rest Port>


Execute all the System tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to execute all the system tests in one go by navigating to the python system test directory
and running pytest without the test name::

    /FogLAMP/tests/system/python $ pytest
    --pi-db=<PI DB name>
    --pi-host=<Hostname/IP of PI Server>
    --pi-admin=<Login of PI Machine>
    --pi-passwd=<Password of PI Machine>
    --pi-token=<PI Producer token>

Console output
++++++++++++++

Console displays the docstring of the test that tells a user what test is running and what are the assertion points, for e.g., ::

    $ pytest test_smoke.py
    ================= test session starts =================
    platform linux -- Python 3.5.3+, pytest-3.6.0, py-1.6.0, pluggy-0.6.0
    rootdir: /FogLAMP/tests/system/python, inifile: pytest.ini
    plugins:
    collected 1 item

    Test system/python/test_smoke.py Test that data is inserted in FogLAMP
        start_south_coap: Fixture that starts FogLAMP with south coap plugin
        Assertions:
            on endpoint GET /foglamp/asset
            on endpoint GET /foglamp/asset/<asset_name>


Running tests on raspberry pi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The system tests can be also executed on a raspberry pi (Raspbian OS). Test Prerequisites remains the same as above.
The only difference is you run the test using ``python3 -m pytest`` instead of ``pytest``.