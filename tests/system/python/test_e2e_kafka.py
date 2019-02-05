# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test system/python/test_e2e_kafka.py

"""
import os
import subprocess
import http.client
import json
import time
import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


FOGBENCH_TEMPLATE = "fogbench-template.json"
SENSOR_VALUE = 20
SOUTH_PLUGIN_NAME = "coap"
NORTH_PLUGIN_NAME = "Kafka"
ASSET_NAME = "{}_to_{}".format(SOUTH_PLUGIN_NAME, NORTH_PLUGIN_NAME.lower())
CONSUMER_GROUP = "foglamp_consumer"
CONSUMER_INSTANCE = "foglamp_instance"
HEADER = {'Content-Type': 'application/vnd.kafka.v2+json', 'Accept': 'application/vnd.kafka.json.v2+json'}


class TestE2EKafka:

    def _prepare_template_reading_from_fogbench(self):
        """ Define the template file for fogbench readings """

        fogbench_template_path = os.path.join(
            os.path.expandvars('${FOGLAMP_ROOT}'), 'data/{}'.format(FOGBENCH_TEMPLATE))
        f = open(fogbench_template_path, "w")
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "sensor", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                ASSET_NAME, SENSOR_VALUE, SENSOR_VALUE))
        f.close()
        return fogbench_template_path

    def _configure_and_start_north_kafka(self, north_branch, foglamp_url, host, port, topic, task_name="NorthReadingsTo{}"
                                         .format(NORTH_PLUGIN_NAME)):
        """ Configure and Start north kafka task """

        try:
            subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/install_c_plugin {} north {}"
                           .format(north_branch, NORTH_PLUGIN_NAME)], shell=True, check=True)
        except subprocess.CalledProcessError:
            assert False, "kafka plugin installation failed"

        conn = http.client.HTTPConnection(foglamp_url)
        data = {"name": task_name,
                "plugin": "{}".format(NORTH_PLUGIN_NAME),
                "type": "north",
                "schedule_type": 3,
                "schedule_day": 0,
                "schedule_time": 0,
                "schedule_repeat": 0,
                "schedule_enabled": "true",
                "config": {"topic": {"value": topic},
                           "brokers": {"value": "{}:{}".format(host, port)}}
                }
        conn.request("POST", '/foglamp/scheduled/task', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 2 == len(val)
        assert task_name == val['name']

    @pytest.fixture
    def start_south_north(self, reset_and_start_foglamp, start_south, remove_data_file,
                          remove_directories, south_branch, foglamp_url, north_branch, kafka_host, kafka_port, kafka_topic):
        """ This fixture clone a south and north repo and starts both south and north instance
            reset_and_start_foglamp: Fixture that resets and starts foglamp, no explicit invocation, called at start
            start_south: Fixture that starts any south service with given configuration
            remove_data_file: Fixture that remove data file created during the tests
            remove_directories: Fixture that remove directories created during the tests """

        fogbench_template_path = self._prepare_template_reading_from_fogbench()

        start_south(SOUTH_PLUGIN_NAME, south_branch, foglamp_url, service_name=SOUTH_PLUGIN_NAME)

        self._configure_and_start_north_kafka(north_branch, foglamp_url, kafka_host, kafka_port, kafka_topic)

        yield self.start_south_north

        # Cleanup code that runs after the test is over
        remove_data_file(fogbench_template_path)
        remove_directories("/tmp/foglamp-south-{}".format(SOUTH_PLUGIN_NAME))
        remove_directories("/tmp/foglamp-north-{}".format(NORTH_PLUGIN_NAME.lower()))

    def test_end_to_end(self, start_south_north, foglamp_url, wait_time, kafka_host, kafka_rest_port, kafka_topic):
        """ Test that data is inserted in FogLAMP and sent to Kafka
            start_south_north: Fixture that starts FogLAMP with south and north instance
            Assertions:
                on endpoint GET /foglamp/asset
                on endpoint GET /foglamp/asset/<asset_name>
                data received from Kafka is same as data sent"""

        conn = http.client.HTTPConnection(foglamp_url)
        time.sleep(wait_time)
        subprocess.run(["cd $FOGLAMP_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -"
                       .format(FOGBENCH_TEMPLATE)], shell=True, check=True)
        time.sleep(wait_time)
        conn.request("GET", '/foglamp/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 1 == len(val)
        assert ASSET_NAME == val[0]["assetCode"]
        assert 1 == val[0]["count"]

        conn.request("GET", '/foglamp/asset/{}'.format(ASSET_NAME))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 1 == len(val)
        assert {'sensor': SENSOR_VALUE} == val[0]["reading"]

        self._read_from_kafka(kafka_host, kafka_rest_port, kafka_topic)

    def _read_from_kafka(self, host, rest_port, topic):
        conn = http.client.HTTPConnection("{}:{}".format(host, rest_port))

        # Close the consumer (DELETE) to make it leave the group and clean up its resources
        self._close_consumer(host, rest_port)

        # Assertions on Kafka topic, consumer and subscription
        self._verify_kafka_topic(conn, topic)

        self._verify_kafka_topic_by_name(conn, topic)

        # Create a consumer group and instance
        self._verify_kafka_consumer_group_and_instance(conn)

        self._verify_consumer_subscription_to_topic(conn, topic)

        self._verify_consumer_data_from_topic(conn)

    def _verify_kafka_topic(self, conn, topic):
        conn.request("GET", '/topics')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert topic in jdoc

    def _verify_kafka_topic_by_name(self, conn, topic):
        conn.request("GET", '/topics/{}'.format(topic))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert topic == jdoc["name"]

    def _verify_kafka_consumer_group_and_instance(self, conn):
        data = {"name": CONSUMER_INSTANCE, "format": "json", "auto.offset.reset": "earliest"}
        conn.request("POST", '/consumers/{}'.format(CONSUMER_GROUP), json.dumps(data), headers=HEADER)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert CONSUMER_INSTANCE == jdoc["instance_id"]

    def _verify_consumer_subscription_to_topic(self, conn, topic):
        data = {"topics": [topic]}
        conn.request("POST", '/consumers/{}/instances/{}/subscription'.format(CONSUMER_GROUP, CONSUMER_INSTANCE),
                     json.dumps(data), headers=HEADER)
        r = conn.getresponse()
        r.read()
        # No content response
        assert 204 == r.status

    def _verify_consumer_data_from_topic(self, conn):
        conn.request("GET", '/consumers/{}/instances/{}/records'.format(CONSUMER_GROUP, CONSUMER_INSTANCE), headers=HEADER)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert ASSET_NAME == jdoc[0]['value']['asset']
        assert SENSOR_VALUE == int(jdoc[0]['value']['sensor'])

    def _close_consumer(self, kafka_host, kafka_rest_port):
        conn = http.client.HTTPConnection("{}:{}".format(kafka_host, kafka_rest_port))
        conn.request("DELETE", '/consumers/{}/instances/{}'.format(CONSUMER_GROUP, CONSUMER_INSTANCE),
                     headers=HEADER)
        r = conn.getresponse()
        # No content response
        r.read()
