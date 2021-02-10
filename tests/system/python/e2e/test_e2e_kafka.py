# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test system/python/test_e2e_kafka.py

"""
import os
import subprocess
import http.client
import json
import time
import pytest
import utils


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


FOGBENCH_TEMPLATE = "fogbench-template.json"
SENSOR_VALUE = 20
SOUTH_PLUGIN_NAME = "coap"
NORTH_PLUGIN_NAME = "Kafka"
ASSET_NAME = "{}_to_{}".format(SOUTH_PLUGIN_NAME, NORTH_PLUGIN_NAME.lower())
CONSUMER_GROUP = "fledge_consumer"
CONSUMER_INSTANCE = "fledge_instance"
HEADER = {'Content-Type': 'application/vnd.kafka.v2+json', 'Accept': 'application/vnd.kafka.json.v2+json'}


class TestE2EKafka:
    def get_ping_status(self, fledge_url):
        _connection = http.client.HTTPConnection(fledge_url)
        _connection.request("GET", '/fledge/ping')
        r = _connection.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return jdoc

    def get_statistics_map(self, fledge_url):
        _connection = http.client.HTTPConnection(fledge_url)
        _connection.request("GET", '/fledge/statistics')
        r = _connection.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return utils.serialize_stats_map(jdoc)


    def _prepare_template_reading_from_fogbench(self):
        """ Define the template file for fogbench readings """

        fogbench_template_path = os.path.join(
            os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(FOGBENCH_TEMPLATE))
        with open(fogbench_template_path, "w") as f:
            f.write(
                '[{"name": "%s", "sensor_values": '
                '[{"name": "sensor", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                    ASSET_NAME, SENSOR_VALUE, SENSOR_VALUE))

        return fogbench_template_path

    def _configure_and_start_north_kafka(self, north_branch, fledge_url, host, port, topic, task_name="NorthReadingsTo{}"
                                         .format(NORTH_PLUGIN_NAME)):
        """ Configure and Start north kafka task """

        try:
            subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_plugin {} north {}"
                           .format(north_branch, NORTH_PLUGIN_NAME)], shell=True, check=True)
        except subprocess.CalledProcessError:
            assert False, "kafka plugin installation failed"

        conn = http.client.HTTPConnection(fledge_url)
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
        conn.request("POST", '/fledge/scheduled/task', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 2 == len(val)
        assert task_name == val['name']

    @pytest.fixture
    def start_south_north(self, reset_and_start_fledge, add_south, remove_data_file,
                          remove_directories, south_branch, fledge_url, north_branch, kafka_host, kafka_port, kafka_topic):
        """ This fixture clone a south and north repo and starts both south and north instance
            reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
            add_south: Fixture that starts any south service with given configuration
            remove_data_file: Fixture that remove data file created during the tests
            remove_directories: Fixture that remove directories created during the tests """

        fogbench_template_path = self._prepare_template_reading_from_fogbench()

        add_south(SOUTH_PLUGIN_NAME, south_branch, fledge_url, service_name=SOUTH_PLUGIN_NAME)

        self._configure_and_start_north_kafka(north_branch, fledge_url, kafka_host, kafka_port, kafka_topic)

        yield self.start_south_north

        # Cleanup code that runs after the test is over
        remove_data_file(fogbench_template_path)
        remove_directories("/tmp/fledge-south-{}".format(SOUTH_PLUGIN_NAME))
        remove_directories("/tmp/fledge-north-{}".format(NORTH_PLUGIN_NAME.lower()))

    def test_end_to_end(self, start_south_north, fledge_url, wait_time, kafka_host, kafka_rest_port, kafka_topic,
                        skip_verify_north_interface):
        """ Test that data is inserted in Fledge and sent to Kafka
            start_south_north: Fixture that starts Fledge with south and north instance
            skip_verify_north_interface: Flag for assertion of data from kafka rest
            Assertions:
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name>
                data received from Kafka is same as data sent"""

        conn = http.client.HTTPConnection(fledge_url)
        time.sleep(wait_time)
        subprocess.run(["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -"
                       .format(FOGBENCH_TEMPLATE)], shell=True, check=True)
        time.sleep(wait_time)

        ping_response = self.get_ping_status(fledge_url)
        assert 1 == ping_response["dataRead"]
        if not skip_verify_north_interface:
            assert 1 == ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        assert 1 == actual_stats_map[ASSET_NAME.upper()]
        assert 1 == actual_stats_map['READINGS']
        if not skip_verify_north_interface:
            assert 1 == actual_stats_map['Readings Sent']
            assert 1 == actual_stats_map["NorthReadingsTo{}".format(NORTH_PLUGIN_NAME)]

        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 1 == len(val)
        assert ASSET_NAME == val[0]["assetCode"]
        assert 1 == val[0]["count"]

        conn.request("GET", '/fledge/asset/{}'.format(ASSET_NAME))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 1 == len(val)
        assert {'sensor': SENSOR_VALUE} == val[0]["reading"]

        if not skip_verify_north_interface:
            self._read_from_kafka(kafka_host, kafka_rest_port, kafka_topic)

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
        assert len(tracking_details["track"]), "Failed to track Ingest event"
        tracked_item = tracking_details["track"][0]
        assert "coap" == tracked_item["service"]
        assert ASSET_NAME == tracked_item["asset"]
        assert SOUTH_PLUGIN_NAME == tracked_item["plugin"]

        if not skip_verify_north_interface:
            egress_tracking_details = utils.get_asset_tracking_details(fledge_url,"Egress")
            assert len(egress_tracking_details["track"]), "Failed to track Egress event"
            tracked_item = egress_tracking_details["track"][0]
            assert "NorthReadingsTo{}".format(NORTH_PLUGIN_NAME) == tracked_item["service"]
            assert ASSET_NAME == tracked_item["asset"]
            assert NORTH_PLUGIN_NAME == tracked_item["plugin"]


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

        # FIXME: FOGL-2573 local / AWS confluent setup results in no data
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
        assert len(jdoc)
        assert ASSET_NAME == jdoc[0]['value']['asset']
        assert SENSOR_VALUE == float(jdoc[0]['value']['sensor'])

    def _close_consumer(self, kafka_host, kafka_rest_port):
        conn = http.client.HTTPConnection("{}:{}".format(kafka_host, kafka_rest_port))
        conn.request("DELETE", '/consumers/{}/instances/{}'.format(CONSUMER_GROUP, CONSUMER_INSTANCE),
                     headers=HEADER)
        r = conn.getresponse()
        # No content response
        r.read()
