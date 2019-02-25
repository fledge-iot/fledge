# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test end to end flow with:
        Notification service And OverMaxRule in built rule plugin
        notify-python35 delivery plugin
"""

import os
import time
import subprocess
import http.client
import json
import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SERVICE = "notification"
SERVICE_NAME = "NotificationServer #1"
NOTIFY_PLUGIN = "python35"
NOTIFY_RULE = "OverMaxRule"


def _configure_and_start_service(service_branch, foglamp_url, remove_directories):
    try:
        subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/install_c_service {} {}"
                       .format(service_branch, SERVICE)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "{} installation failed".format(SERVICE)
    finally:
        remove_directories("/tmp/foglamp-service-{}".format(SERVICE))

    # Start service
    conn = http.client.HTTPConnection(foglamp_url)
    data = {"name": SERVICE_NAME,
            "type": "notification",
            "enabled": "true"
            }
    conn.request("POST", '/foglamp/service', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert 2 == len(jdoc)
    assert SERVICE_NAME == jdoc['name']


def _install_notify_plugin(notify_branch, plugin_name, remove_directories):
    try:
        subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/install_c_plugin {} notify {}".format(
            notify_branch, plugin_name)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "{} installation failed".format(plugin_name)
    finally:
        remove_directories("/tmp/foglamp-notify-{}".format(plugin_name))


def _get_result(foglamp_url, path):
    conn = http.client.HTTPConnection(foglamp_url)
    conn.request("GET", path)
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def _verify_service(foglamp_url, status):
    jdoc = _get_result(foglamp_url, '/foglamp/service')
    svc = jdoc['services'][2]
    assert SERVICE_NAME == svc['name']
    assert SERVICE.capitalize() == svc['type']
    assert status == svc['status']


def _verify_audit_log_entry(foglamp_url, path, name, severity='INFORMATION'):
    jdoc = _get_result(foglamp_url, path)
    audit_detail = jdoc['audit'][0]
    assert 1 == jdoc['totalCount']
    assert severity == audit_detail['severity']
    assert name == audit_detail['details']['name']


def _add_notification_instance(foglamp_url, payload):
    conn = http.client.HTTPConnection(foglamp_url)
    conn.request("POST", '/foglamp/notification', json.dumps(payload))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "Notification {} created successfully".format(payload['name']) == jdoc['result']


class TestNotificationService:

    def test_service(self, reset_and_start_foglamp, service_branch, foglamp_url, wait_time, retries, remove_directories):
        _configure_and_start_service(service_branch, foglamp_url, remove_directories)

        retry_count = 0
        # only 2 services is being up by default i.e core and storage
        default_registry_count = 2
        service_registry = default_registry_count
        while service_registry != 3 and retry_count < retries:
            svc = _get_result(foglamp_url, '/foglamp/service')
            service_registry = svc['services']
            retry_count += 1
            time.sleep(wait_time * 2)

        if len(service_registry) == default_registry_count:
            assert False, "Failed to start the {} service".format(SERVICE)

        _verify_service(foglamp_url, status='running')

        _verify_audit_log_entry(foglamp_url, '/foglamp/audit?source=NTFST', name=SERVICE_NAME)

    def test_get_default_notification_plugins(self, foglamp_url, remove_directories):
        remove_directories(os.environ['FOGLAMP_ROOT'] + '/plugins/notificationDelivery')
        remove_directories(os.environ['FOGLAMP_ROOT'] + 'cmake_build/C/plugins/notificationDelivery')
        jdoc = _get_result(foglamp_url, '/foglamp/notification/plugin')
        assert [] == jdoc['delivery']
        assert 1 == len(jdoc['rules'])
        assert NOTIFY_RULE == jdoc['rules'][0]['name']


class TestNotificationCRUD:

    # FIXME: FOGL-2434 Add name with some special character
    @pytest.mark.parametrize("data", [
        {"name": "Test1", "description": "Test 1 notification", "rule": NOTIFY_RULE,
         "channel": NOTIFY_PLUGIN, "enabled": "false", "notification_type": "retriggered"},
        {"name": "Test2", "description": "Test 2 notification", "rule": NOTIFY_RULE,
         "channel": NOTIFY_PLUGIN, "enabled": "false", "notification_type": "toggled"},
        {"name": "Test3", "description": "Test 3 notification", "rule": NOTIFY_RULE,
         "channel": NOTIFY_PLUGIN, "enabled": "false", "notification_type": "one shot"}
    ])
    def test_create_notification_instances_with_default_rule_and_channel_python35(self, foglamp_url, notify_branch,
                                                                                  data,
                                                                                  remove_directories):
        # FIXME: Handle in a better way; we need below code once for a test
        if data['name'] == 'Test1':
            _install_notify_plugin(notify_branch, NOTIFY_PLUGIN, remove_directories)
        _add_notification_instance(foglamp_url, data)

    def test_inbuilt_rule_plugin_and_notify_python35_delivery(self, foglamp_url):
        jdoc = _get_result(foglamp_url, '/foglamp/notification/plugin')
        assert 1 == len(jdoc['delivery'])
        assert NOTIFY_PLUGIN == jdoc['delivery'][0]['name']
        assert 1 == len(jdoc['rules'])
        assert NOTIFY_RULE == jdoc['rules'][0]['name']

    def test_get_notifications_and_audit_entry(self, foglamp_url):
        jdoc = _get_result(foglamp_url, '/foglamp/notification')
        assert 3 == len(jdoc['notifications'])

        jdoc = _get_result(foglamp_url, '/foglamp/audit?source=NTFAD')
        assert 3 == jdoc['totalCount']

    def test_update_notification(self, foglamp_url, name="Test1"):
        conn = http.client.HTTPConnection(foglamp_url)
        data = {"notification_type": "toggled"}
        conn.request("PUT", '/foglamp/notification/{}'.format(name), json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Notification {} updated successfully".format(name) == jdoc["result"]

        # Verify updated notification info
        jdoc = _get_result(foglamp_url, '/foglamp/notification/{}'.format(name))
        assert "toggled" == jdoc['notification']['notificationType']

    def test_delete_notification(self, foglamp_url, name="Test3"):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("DELETE", '/foglamp/notification/{}'.format(name))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Notification {} deleted successfully.".format(name) == jdoc["result"]

        # Verify only two notifications should exist NOT 3
        jdoc = _get_result(foglamp_url, '/foglamp/notification')
        notifications = jdoc['notifications']
        assert 2 == len(notifications)
        assert "Notification Test1" == notifications[0]['name']
        assert "Notification Test2" == notifications[1]['name']


class TestSentAndReceiveNotification:
    FOGBENCH_TEMPLATE = "fogbench-template.json"
    SENSOR_VALUE = 20
    SOUTH_PLUGIN_NAME = "coap"
    ASSET_NAME = "{}".format(SOUTH_PLUGIN_NAME)

    @pytest.fixture
    def start_south(self, add_south, remove_data_file, remove_directories, south_branch, foglamp_url, wait_time):
        """ This fixture clone a south repo and starts south instance
            add_south: Fixture that starts any south service with given configuration
            remove_data_file: Fixture that remove data file created during the tests
            remove_directories: Fixture that remove directories created during the tests """

        fogbench_template_path = self.prepare_template_reading_from_fogbench()

        add_south(self.SOUTH_PLUGIN_NAME, south_branch, foglamp_url, service_name=self.SOUTH_PLUGIN_NAME)

        yield self.start_south

        # Cleanup code that runs after the test is over
        remove_data_file(fogbench_template_path)
        remove_directories("/tmp/foglamp-south-{}".format(self.SOUTH_PLUGIN_NAME))

    def prepare_template_reading_from_fogbench(self):
        """ Define the template file for fogbench readings """

        fogbench_template_path = os.path.join(
            os.path.expandvars('${FOGLAMP_ROOT}'), 'data/{}'.format(self.FOGBENCH_TEMPLATE))
        with open(fogbench_template_path, "w") as f:
            f.write(
                '[{"name": "%s", "sensor_values": '
                '[{"name": "sensor", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                    self.ASSET_NAME, self.SENSOR_VALUE, self.SENSOR_VALUE))

        return fogbench_template_path

    def ingest_readings_from_fogbench(self, foglamp_url, wait_time):
        conn = http.client.HTTPConnection(foglamp_url)
        subprocess.run(["cd $FOGLAMP_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -"
                       .format(self.FOGBENCH_TEMPLATE)], shell=True, check=True)
        time.sleep(wait_time)
        conn.request("GET", '/foglamp/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 1 == len(val)
        assert self.ASSET_NAME == val[0]["assetCode"]
        assert 1 == val[0]["count"]

        conn.request("GET", '/foglamp/asset/{}'.format(self.ASSET_NAME))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 1 == len(val)
        assert {'sensor': self.SENSOR_VALUE} == val[0]["reading"]

    def configure_rule_with_latest_eval_type(self, foglamp_url, cat_name):
        conn = http.client.HTTPConnection(foglamp_url)
        data = {"asset": self.ASSET_NAME,
                "datapoint": "sensor",
                "evaluation_type": "latest",
                "trigger_value": str(self.SENSOR_VALUE),
                }
        conn.request("PUT", '/foglamp/category/rule{}'.format(cat_name), json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status

    def enable_notification(self, foglamp_url, cat_name, is_enabled=True):
        _enabled = "true" if is_enabled else "false"
        data = {"value": _enabled}
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("PUT", '/foglamp/category/{}/enable'.format(cat_name), json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status

    def test_sent_and_receive_notification(self, foglamp_url, start_south, wait_time):
        data = {"name": "Test4", "description": "Test4_Notification", "rule": NOTIFY_RULE, "channel": NOTIFY_PLUGIN,
                "enabled": False, "notification_type": "retriggered"}
        name = data['name']
        _add_notification_instance(foglamp_url, data)
        self.configure_rule_with_latest_eval_type(foglamp_url, name)
        self.enable_notification(foglamp_url, name)

        time.sleep(wait_time)
        self.ingest_readings_from_fogbench(foglamp_url, wait_time)

        _verify_audit_log_entry(foglamp_url, '/foglamp/audit?source=NTFSN', name=name)


class TestStartStopNotificationService:

    def test_shutdown_service_with_schedule_disable(self, foglamp_url, disable_schedule, wait_time):
        disable_schedule(foglamp_url, SERVICE_NAME)

        _verify_service(foglamp_url, status='shutdown')
        time.sleep(wait_time)
        _verify_audit_log_entry(foglamp_url, '/foglamp/audit?source=NTFSD', name=SERVICE_NAME)

    def test_restart_notification_service(self, foglamp_url, enable_schedule):
        enable_schedule(foglamp_url, SERVICE_NAME)

        _verify_service(foglamp_url, status='running')
        _verify_audit_log_entry(foglamp_url, '/foglamp/audit?source=NTFST', name=SERVICE_NAME)
