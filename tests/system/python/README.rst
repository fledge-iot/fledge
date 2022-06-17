
.. |pytest| raw:: html

   <a href="https://docs.pytest.org/en/latest/#" target="_blank">pytest</a>

.. |installed| raw:: html

   <a href="https://github.com/fledge-iot/fledge#build-prerequisites" target="_blank">installed</a>

.. |build| raw:: html

   <a href="https://github.com/fledge-iot/fledge#build" target="_blank">build</a>

.. |set| raw:: html

   <a href="https://github.com/fledge-iot/fledge#testing-fledge-from-your-development-environment" target="_blank">set</a>

.. |kafka-build| raw:: html

   <a href="https://github.com/fledge-iot/fledge-north-kafka#build" target="_blank">kafka-build</a>

.. |confluent| raw:: html

   <a href="https://www.confluent.io/download/" target="_blank">confluent</a>

.. |Confluent CLI| raw:: html

   <a href="https://docs.confluent.io/current/cli/command-reference/index.html" target="_blank">Confluent CLI</a>

.. |REST Proxy| raw:: html

   <a href="https://docs.confluent.io/current/kafka-rest/docs/quickstart.html" target="_blank">REST Proxy QuickStart</a>

.. =============================================

*******************************************
Fledge System Tests using pytest framework
*******************************************

System tests are the third category of test in Fledge. These test ensures that end to end flow of a Fledge system is
working as expected.

A typical example can be ingesting asset data in Fledge database, and sending to a cloud system with different set of
configuration rules.

Since these kinds of tests interacts between two or more heterogeneous systems, these are often slow in nature.

Fledge uses python |pytest| framework to execute the system tests. To contribute to system test, a developer should
be comfortable in writing tests in pytest.

Running Fledge System tests
============================

Test Prerequisites
------------------

Install the following prerequisites to run a System test ::

   pip3 install pytest

Also, Fledge must have:

   1. All dependencies |installed|
   2. |build|
   3. and Fledge_ROOT must be |set|


Test Execution
--------------

Some tests, like ``test_e2e_coap_PI.py`` , requires some information to be provided
for example the PI-Server or the OCS account that should be used. This information can be passed though command
like during test execution. For e.g., ::

    /Fledge/tests/system/python/e2e/ $ pytest test_e2e_coap_PI.py
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
    --storage-plugin=STORAGE_PLUGIN
                        Database plugin to use for tests
    --south-branch=SOUTH_BRANCH
                        south branch name
    --north-branch=NORTH_BRANCH
                        north branch name
    --fledge-url=FLEDGE_URL
                        Fledge client api url
    --use-pip-cache=USE_PIP_CACHE
                        use pip cache is requirement is available

    --pi-host=PI_HOST
                        PI Server Host Name/IP
    --pi-port=PI_PORT
                        PI Server Port
    --pi-db=PI_DB
                        PI Server database
    --pi-admin=PI_ADMIN
                        PI Server user login
    --pi-passwd=PI_PASSWD
                        PI Server user login password
    --pi-token=PI_TOKEN
                        OMF Producer Token

    --ocs-tenant=OCS_TENANT
                        Tenant id of OCS
    --ocs-client-id=OCS_CLIENT_ID
                        Client id of OCS account
    --ocs-client-secret=OCS_CLIENT_SECRET
                        Client Secret of OCS account
    --ocs-namespace=OCS_NAMESPACE
                        OCS namespace where the information are stored
    --ocs-token=OCS_TOKEN
                        Token of OCS account


    --south-service-name=SOUTH_SERVICE_NAME
                        Name of the South Service
    --asset-name=ASSET_NAME
                        Name of asset

    --wait-time=WAIT_TIME
                        Generic wait time between processes to run
    --retries=RETRIES
                        Number of tries for polling

    --kafka-host=KAFKA_HOST
                        Kafka Server Host Name/IP
    --kafka-port=KAFKA_PORT
                        Kafka Server Port
    --kafka-topic=KAFKA_TOPIC
                        Kafka topic
    --kafka-rest-port=KAFKA_REST_PORT
                        Kafka REST Proxy Port

Using different storage engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default system tests runs with sqlite database. If you want, you can use postgres storage plugin and tests will be
executed using postgres database and postgres storage engine::

    $ pytest test_smoke.py --storage-plugin=postgres

Test test_e2e_coap_PI and test_e2e_csv_PI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The minimum required parameters to run these tests are ::

    --pi-db=<PI DB name>
    --pi-host=<Hostname/IP of PI Server>
    --pi-port=<PI Server Port>
    --pi-admin=<Login of PI Machine>
    --pi-passwd=<Password of PI Machine>
    --pi-token="<PI Producer token>"


Test test_e2e_coap_OCS
~~~~~~~~~~~~~~~~~~~~~~

The minimum required parameters to run these tests are ::

    --ocs-tenant=<Tenant id of OCS>
    --ocs-client-id=<Client id of OCS account>
    --ocs-client-secret=<Client Secret of OCS account>
    --ocs-namespace=<OCS namespace where the information are stored>
    --ocs-token=<Token of OCS account>


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
    --kafka-rest-port=<Kafka REST Proxy Port>

Test test_e2e_fledge_pair.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The minimum required parameters to run this test is ::

    --remote-user=<Username of remote machine>
    --remote-ip=<IP of remote machine>
    --key-path=<Absolute path of key used for authentication>
    --remote-fledge-path=<Absolute path on remote machine where Fledge is cloned>
    --pi-db=<PI DB name>
    --pi-host=<Hostname/IP of PI Server>
    --pi-port=<PI Server Port>
    --pi-admin=<Login of PI Machine>
    --pi-passwd=<Password of PI Machine>
    --pi-token="<PI Producer token>"

Test test_north_pi_webapi_nw_throttle.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Example
python3 -m pytest -s -v test_north_pi_webapi_nw_throttle.py  --pi-db=<db_name>  \
--pi-host=<host_ip> --pi-port=<port> --pi-admin=<user>  \
--pi-passwd=<password>  --packet-delay=50  --rate-limit=100 \
--interface-for-impairment=eth0  --south-service-wait-time=20 \
--north-catch-up-time=180



Execute all the System tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to execute all the system tests in one go by navigating to the python system test directory
and running pytest without the test name::

    /Fledge/tests/system/python $ pytest
    --pi-db=<PI DB name>
    --pi-host=<Hostname/IP of PI Server>
    --pi-admin=<Login of PI Machine>
    --pi-passwd=<Password of PI Machine>
    --pi-token=<PI Producer token>

    --ocs-tenant=<Tenant id of OCS>
    --ocs-client-id=<Client id of OCS account>
    --ocs-client-secret=<Client Secret of OCS account>
    --ocs-namespace=<OCS namespace where the information are stored>
    --ocs-token=<Token of OCS account>

    --kafka-host=<Hostname/IP of Kafka Server>
    --kafka-port=<Kafka Server Port>
    --kafka-topic=<Kafka topic>
    --kafka-rest-port=<Kafka REST Proxy Port>

    --remote-user=REMOTE_USER
                        Username on remote machine where Fledge will run
    --remote-ip=REMOTE_IP
                        IP of remote machine where Fledge will run
    --key-path=KEY_PATH   Path of key file used for authentication to remote
                        machine
    --remote-fledge-path=REMOTE_FLEDGE_PATH
                        Path on the remote machine where Fledge is clone and
                        built


Console output
++++++++++++++

Console displays the docstring of the test that tells a user what test is running and what are the assertion points, for e.g., ::

    $ pytest test_smoke.py
    ================= test session starts =================
    platform linux -- Python 3.5.3+, pytest-3.6.0, py-1.6.0, pluggy-0.6.0
    rootdir: /Fledge/tests/system/python, inifile: pytest.ini
    plugins:
    collected 1 item

    Test system/python/smoke/test_smoke.py Test that data is inserted in Fledge
        start_south_coap: Fixture that starts Fledge with south coap plugin
        Assertions:
            on endpoint GET /fledge/asset
            on endpoint GET /fledge/asset/<asset_name>


Running tests on raspberry pi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The system tests can be also executed on a raspberry pi (Raspbian OS). Test Prerequisites remains the same as above.
The only difference is you run the test using ``python3 -m pytest`` instead of ``pytest``.
