# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test end to end flow with:
        Notification service with
        Threshold in-built rule plugin
        notify-python35 delivery channel plugin
"""

import os
import time
import subprocess
import http.client
import json
from threading import Event
import urllib.parse

import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SERVICE = "notification"
SERVICE_NAME = "NotificationServer #1"
NOTIFY_PLUGIN = "python35"
NOTIFY_INBUILT_RULES = ["Threshold"]


def _configure_and_start_service(service_branch, fledge_url, remove_directories):
    try:
        subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_service {} {}"
                       .format(service_branch, SERVICE)], shell=True, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        assert False, "{} installation failed".format(SERVICE)
    finally:
        remove_directories("/tmp/fledge-service-{}".format(SERVICE))

    # Start service
    conn = http.client.HTTPConnection(fledge_url)
    data = {"name": SERVICE_NAME,
            "type": "notification",
            "enabled": "true"
            }
    conn.request("POST", '/fledge/service', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert 2 == len(jdoc)
    assert SERVICE_NAME == jdoc['name']


def _install_notify_plugin(notify_branch, plugin_name, remove_directories):
    try:
        subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_plugin {} notify {}".format(
            notify_branch, plugin_name)], shell=True, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        assert False, "{} installation failed".format(plugin_name)
    finally:
        remove_directories("/tmp/fledge-notify-{}".format(plugin_name))


def _get_result(fledge_url, path):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("GET", path)
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def _verify_service(fledge_url, status):
    jdoc = _get_result(fledge_url, '/fledge/service')
    srvc = [s for s in jdoc['services'] if s['name'] == SERVICE_NAME]
    assert 1 == len(srvc)
    svc = srvc[0]
    assert SERVICE.capitalize() == svc['type']
    assert status == svc['status']


def _verify_audit_log_entry(fledge_url, path, name, severity='INFORMATION', count=1):
    jdoc = _get_result(fledge_url, path)
    assert len(jdoc['audit'])
    assert count == jdoc['totalCount']
    audit_detail = jdoc['audit'][0]
    assert severity == audit_detail['severity']
    assert name == audit_detail['details']['name']


def _add_notification_instance(fledge_url, payload):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("POST", '/fledge/notification', json.dumps(payload))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "Notification {} created successfully".format(payload['name']) == jdoc['result']


def pause_for_x_seconds(x=1):
    wait_e = Event()
    wait_e.clear()
    wait_e.wait(timeout=x)


class TestNotificationService:
    def test_service(self, reset_and_start_fledge, service_branch, fledge_url, wait_time, retries, remove_directories):
        _configure_and_start_service(service_branch, fledge_url, remove_directories)

        retry_count = 0
        # only 2 services is being up by default i.e core and storage
        default_registry_count = 2
        service_registry = default_registry_count
        while service_registry != 3 and retry_count < retries:
            svc = _get_result(fledge_url, '/fledge/service')
            service_registry = svc['services']
            retry_count += 1

            pause_for_x_seconds(x=wait_time * 2)

        if len(service_registry) == default_registry_count:
            assert False, "Failed to start the {} service".format(SERVICE)

        _verify_service(fledge_url, status='running')
        _verify_audit_log_entry(fledge_url, '/fledge/audit?source=NTFST', name=SERVICE_NAME)

    def test_get_default_notification_plugins(self, fledge_url, remove_directories):
        remove_directories(os.environ['FLEDGE_ROOT'] + '/plugins/notificationDelivery')
        remove_directories(os.environ['FLEDGE_ROOT'] + '/plugins/notificationRule')
        remove_directories(os.environ['FLEDGE_ROOT'] + 'cmake_build/C/plugins/notificationDelivery')
        remove_directories(os.environ['FLEDGE_ROOT'] + 'cmake_build/C/plugins/notificationRule')
        jdoc = _get_result(fledge_url, '/fledge/notification/plugin')
        assert [] == jdoc['delivery']
        assert 1 == len(jdoc['rules'])
        assert NOTIFY_INBUILT_RULES[0] == jdoc['rules'][0]['name']


class TestNotificationCRUD:

    @pytest.mark.parametrize("data", [
        {"name": "Test 1", "description": "Test 1 notification", "rule": NOTIFY_INBUILT_RULES[0],
         "channel": NOTIFY_PLUGIN, "enabled": "false", "notification_type": "retriggered"},
        {"name": "Test2", "description": "Test 2 notification", "rule": NOTIFY_INBUILT_RULES[0],
         "channel": NOTIFY_PLUGIN, "enabled": "false", "notification_type": "toggled"},
        {"name": "Test #3", "description": "Test 3 notification", "rule": NOTIFY_INBUILT_RULES[0],
         "channel": NOTIFY_PLUGIN, "enabled": "false", "notification_type": "one shot"}
    ])
    def test_create_notification_instances_with_default_rule_and_channel_python35(self, fledge_url, notify_branch,
                                                                                  data,
                                                                                  remove_directories):
        if data['name'] == 'Test 1':
            _install_notify_plugin(notify_branch, NOTIFY_PLUGIN, remove_directories)
        _add_notification_instance(fledge_url, data)

    def test_inbuilt_rule_plugin_and_notify_python35_delivery(self, fledge_url):
        jdoc = _get_result(fledge_url, '/fledge/notification/plugin')
        assert 1 == len(jdoc['delivery'])
        assert NOTIFY_PLUGIN == jdoc['delivery'][0]['name']
        assert 1 == len(jdoc['rules'])
        assert NOTIFY_INBUILT_RULES[0] == jdoc['rules'][0]['name']

    def test_get_notifications_and_audit_entry(self, fledge_url):
        jdoc = _get_result(fledge_url, '/fledge/notification')
        assert 3 == len(jdoc['notifications'])

        # Test 1, Test2 and Test #3
        jdoc = _get_result(fledge_url, '/fledge/audit?source=NTFAD')
        assert 3 == jdoc['totalCount']

    def test_update_notification(self, fledge_url, name="Test 1"):
        conn = http.client.HTTPConnection(fledge_url)
        data = {"notification_type": "toggled"}
        conn.request("PUT", '/fledge/notification/{}'.format(urllib.parse.quote(name))
                     , json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Notification {} updated successfully".format(name) == jdoc["result"]

        # Verify updated notification info
        jdoc = _get_result(fledge_url, '/fledge/notification/{}'.format(urllib.parse.quote(name)))
        assert "toggled" == jdoc['notification']['notificationType']

    def test_delete_notification(self, fledge_url, name="Test #3"):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/notification/{}'.format(urllib.parse.quote(name)))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Notification {} deleted successfully.".format(name) == jdoc["result"]

        # Verify only two notifications should exist NOT 3
        jdoc = _get_result(fledge_url, '/fledge/notification')
        notifications = jdoc['notifications']
        assert 2 == len(notifications)
        assert "Test 1" == notifications[0]['name']
        assert "Test2" == notifications[1]['name']

        jdoc = _get_result(fledge_url, '/fledge/audit?source=NTFDL')
        assert 1 == jdoc['totalCount']


class TestSentAndReceiveNotification:
    FOGBENCH_TEMPLATE = "fogbench-template.json"
    SENSOR_VALUE = 20
    SOUTH_PLUGIN_NAME = "coap"
    ASSET_NAME = "{}".format(SOUTH_PLUGIN_NAME)

    @pytest.fixture
    def start_south(self, add_south, remove_data_file, remove_directories, south_branch, fledge_url):
        """ This fixture clone a south repo and starts south instance
            add_south: Fixture that starts any south service with given configuration
            remove_data_file: Fixture that remove data file created during the tests
            remove_directories: Fixture that remove directories created during the tests """

        fogbench_template_path = self.prepare_template_reading_from_fogbench()

        add_south(self.SOUTH_PLUGIN_NAME, south_branch, fledge_url, service_name=self.SOUTH_PLUGIN_NAME)

        yield self.start_south

        # Cleanup code that runs after the test is over
        remove_data_file(fogbench_template_path)
        remove_directories("/tmp/fledge-south-{}".format(self.SOUTH_PLUGIN_NAME))

    def prepare_template_reading_from_fogbench(self):
        """ Define the template file for fogbench readings """

        fogbench_template_path = os.path.join(
            os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(self.FOGBENCH_TEMPLATE))
        with open(fogbench_template_path, "w") as f:
            f.write(
                '[{"name": "%s", "sensor_values": '
                '[{"name": "sensor", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                    self.ASSET_NAME, self.SENSOR_VALUE, self.SENSOR_VALUE))

        return fogbench_template_path

    def ingest_readings_from_fogbench(self, fledge_url, wait_time):
        pause_for_x_seconds(x=wait_time*3)
        conn = http.client.HTTPConnection(fledge_url)
        subprocess.run(["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -"
                       .format(self.FOGBENCH_TEMPLATE)], shell=True, check=True, stdout=subprocess.DEVNULL)

        pause_for_x_seconds(x=wait_time)

        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 1 == len(val)
        assert self.ASSET_NAME == val[0]["assetCode"]
        assert 1 == val[0]["count"]

        conn.request("GET", '/fledge/asset/{}'.format(self.ASSET_NAME))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 1 == len(val)
        assert {'sensor': self.SENSOR_VALUE} == val[0]["reading"]

    def configure_rule_with_single_item_eval_type(self, fledge_url, cat_name):
        conn = http.client.HTTPConnection(fledge_url)
        data = {"asset": self.ASSET_NAME,
                "datapoint": "sensor",
                "evaluation_data": "Single Item",
                "condition": ">",
                "trigger_value": str(self.SENSOR_VALUE - 10),
                }
        conn.request("PUT", '/fledge/category/rule{}'.format(cat_name), json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status

    def enable_notification(self, fledge_url, cat_name, is_enabled=True):
        _enabled = "true" if is_enabled else "false"
        data = {"value": _enabled}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/category/{}/enable'.format(cat_name), json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status

    def test_sent_and_receive_notification(self, fledge_url, start_south, wait_time):
        data = {"name": "Test4",
                "description": "Test4_Notification",
                "rule": NOTIFY_INBUILT_RULES[0],
                "channel": NOTIFY_PLUGIN,
                "enabled": True,
                "notification_type": "one shot"
                }
        name = data['name']
        _add_notification_instance(fledge_url, data)
        self.configure_rule_with_single_item_eval_type(fledge_url, name)

        # upload script NotifyPython35::configure() -> lowercase(categoryName) + _script_ + method_name + ".py"
        cat_name = "delivery{}".format(name)
        script_path = '$FLEDGE_ROOT/tests/system/python/data/notify35.py'
        url = 'http://' + fledge_url + '/fledge/category/' + cat_name + '/script/upload'
        upload_script = 'curl -F "script=@{}" {}'.format(script_path, url)
        subprocess.run(upload_script, shell=True, check=True, stdout=subprocess.DEVNULL)

        # enable notification delivery (it was getting disabled, as no script file was available)
        self.enable_notification(fledge_url, "delivery" + name)

        self.ingest_readings_from_fogbench(fledge_url, wait_time)
        time.sleep(wait_time)

        _verify_audit_log_entry(fledge_url, '/fledge/audit?source=NTFSN', name=name)


class TestStartStopNotificationService:
    def test_shutdown_service_with_schedule_disable(self, fledge_url, disable_schedule, wait_time):
        disable_schedule(fledge_url, SERVICE_NAME)
        _verify_service(fledge_url, status='shutdown')
        pause_for_x_seconds(x=wait_time)
        # After shutdown there should be 1 entry for NTFSD (shutdown)
        _verify_audit_log_entry(fledge_url, '/fledge/audit?source=NTFSD', name=SERVICE_NAME, count=1)

    def test_restart_notification_service(self, fledge_url, enable_schedule, wait_time):
        enable_schedule(fledge_url, SERVICE_NAME)
        pause_for_x_seconds(x=wait_time)
        _verify_service(fledge_url, status='running')
        # After restart there should be 2 entries for NTFST (start)
        _verify_audit_log_entry(fledge_url, '/fledge/audit?source=NTFST', name=SERVICE_NAME, count=2)
