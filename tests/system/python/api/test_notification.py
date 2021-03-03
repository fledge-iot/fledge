# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test notification REST API """

import os
import subprocess
import http.client
import json
import time
import urllib
import pytest


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

SERVICE = "notification"
SERVICE_NAME = "Notification Server #1"
NOTIFY_PLUGIN = "slack"
NOTIFY_INBUILT_RULES = ["Threshold"]
DATA = {"name": "Test - 1",
        "description": "Test4_Notification",
        "rule": NOTIFY_INBUILT_RULES[0],
        "channel": NOTIFY_PLUGIN,
        "enabled": True,
        "notification_type": "one shot"
        }


class TestNotificationServiceAPI:
    def test_notification_without_install(self, reset_and_start_fledge, fledge_url, wait_time):
        # Wait for fledge server to start
        time.sleep(wait_time)
        conn = http.client.HTTPConnection(fledge_url)

        conn.request("GET", '/fledge/notification/plugin')
        r = conn.getresponse()
        assert 404 == r.status
        r = r.read().decode()
        assert "404: No Notification service available." == r

        conn.request("GET", '/fledge/notification/type')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {"notification_type": ["one shot", "retriggered", "toggled"]} == jdoc

        conn.request("POST", '/fledge/notification', json.dumps({}))
        r = conn.getresponse()
        assert 404 == r.status
        r = r.read().decode()
        assert "404: No Notification service available." == r

        pytest.xfail("FOGL-2748")
        conn.request("GET", '/fledge/notification')
        r = conn.getresponse()
        assert 404 == r.status
        r = r.read().decode()
        assert "404: No Notification service available." == r

    def test_notification_service_add(self, service_branch, fledge_url, wait_time, remove_directories):
        try:
            subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_service {} {}"
                           .format(service_branch, SERVICE)], shell=True, check=True)
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

        # Wait for service to get created
        time.sleep(wait_time)
        conn.request("GET", '/fledge/service')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert SERVICE_NAME == jdoc['services'][2]['name']

    def test_install_delivery_plugin(self, notify_branch, remove_directories):
        # Remove any external plugins if installed
        remove_directories(os.path.expandvars('$FLEDGE_ROOT/plugins/notificationDelivery'))
        remove_directories(os.path.expandvars('$FLEDGE_ROOT/plugins/notificationRule'))
        try:
            subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_plugin {} notify {}".format(
                notify_branch, NOTIFY_PLUGIN)], shell=True, check=True)
        except subprocess.CalledProcessError:
            assert False, "{} installation failed".format(NOTIFY_PLUGIN)
        finally:
            remove_directories("/tmp/fledge-notify-{}".format(NOTIFY_PLUGIN))

    @pytest.mark.parametrize("test_input, expected_error", [
        ({"description": "Test4_Notification", "rule": NOTIFY_INBUILT_RULES[0], "channel": NOTIFY_PLUGIN,
          "enabled": True, "notification_type": "one shot"}, '400: Missing name property in payload.'),
        ({"name": "Test4", "rule": NOTIFY_INBUILT_RULES[0], "channel": NOTIFY_PLUGIN, "enabled": True,
          "notification_type": "one shot"}, '400: Missing description property in payload.'),
        ({"name": "Test4", "description": "Test4_Notification", "channel": NOTIFY_PLUGIN, "enabled": True,
          "notification_type": "one shot"}, '400: Missing rule property in payload.'),
        ({"name": "Test4", "description": "Test4_Notification", "rule": NOTIFY_INBUILT_RULES[0], "enabled": True,
          "notification_type": "one shot"}, '400: Missing channel property in payload.'),
        ({"name": "Test4", "description": "Test4_Notification", "rule": NOTIFY_INBUILT_RULES[0],
          "channel": NOTIFY_PLUGIN, "enabled": True}, '400: Missing notification_type property in payload.'),
        ({"name": "=", "description": "Test4_Notification", "rule": NOTIFY_INBUILT_RULES[0], "channel": NOTIFY_PLUGIN,
          "enabled": True, "notification_type": "one shot"}, '400: Invalid name property in payload.'),
        ({"name": "Test4", "description": "Test4_Notification", "rule": "+", "channel": NOTIFY_PLUGIN, "enabled": True,
          "notification_type": "one shot"}, '400: Invalid rule property in payload.'),
        ({"name": "Test4", "description": "Test4_Notification", "rule": NOTIFY_INBUILT_RULES[0], "channel": ":",
          "enabled": True, "notification_type": "one shot"}, '400: Invalid channel property in payload.'),
        ({"name": "Test4", "description": "Test4_Notification", "rule": NOTIFY_INBUILT_RULES[0],
          "channel": NOTIFY_PLUGIN, "enabled": "bla", "notification_type": "one shot"},
         '400: Only "true", "false", true, false are allowed for value of enabled.'),
        ({"name": "Test4", "description": "Test4_Notification", "rule": "InvalidRulePlugin",
          "channel": "InvalidChannelPlugin", "enabled": True, "notification_type": "one shot"},
         '400: Invalid rule plugin InvalidRulePlugin and/or delivery plugin InvalidChannelPlugin supplied.')
    ])
    def test_invalid_create_notification_instance(self, fledge_url, test_input, expected_error):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", '/fledge/notification', json.dumps(test_input))
        r = conn.getresponse()
        assert 400 == r.status
        r = r.read().decode()
        assert expected_error == r

    def test_create_valid_notification_instance(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", '/fledge/notification', json.dumps(DATA))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Notification {} created successfully".format(DATA['name']) == jdoc['result']

        conn.request("GET", '/fledge/notification')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        actual_data = jdoc['notifications'][0]
        assert DATA['name'] == actual_data['name']
        assert DATA['channel'] == actual_data['channel']
        assert 'true' == actual_data['enable']
        assert DATA['notification_type'] == actual_data['notificationType']
        assert DATA['rule'] == actual_data['rule']

        conn.request("GET", '/fledge/notification/plugin')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 2 == len(jdoc)
        assert NOTIFY_PLUGIN == jdoc['delivery'][0]['name']
        assert "notify" == jdoc['delivery'][0]['type']
        assert 1 == len(jdoc['rules'])

    @pytest.mark.parametrize("test_input, expected_error", [
        ({"rule": "+"}, '400: Invalid rule property in payload.'),
        ({"channel": ":"}, '400: Invalid channel property in payload.'),
        ({"enabled": "bla"}, '400: Only "true", "false", true, false are allowed for value of enabled.'),
        ({"rule": "InvalidRulePlugin"},
         '400: Invalid rule plugin:InvalidRulePlugin and/or delivery plugin:None supplied.'),
        ({"channel": "InvalidChannelPlugin"},
         '400: Invalid rule plugin:None and/or delivery plugin:InvalidChannelPlugin supplied.'),
        ({"rule": "InvalidRulePlugin", "channel": "InvalidChannelPlugin"},
         '400: Invalid rule plugin:InvalidRulePlugin and/or delivery plugin:InvalidChannelPlugin supplied.')
    ])
    def test_invalid_update_notification_instance(self, fledge_url, test_input, expected_error):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/notification/{}'.format(urllib.parse.quote(DATA['name'])), json.dumps(test_input))
        r = conn.getresponse()
        assert 400 == r.status
        r = r.read().decode()
        assert expected_error == r

    def test_invalid_name_update_notification_instance(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        changed_data = {"description": "changed_desc"}
        conn.request("PUT", '/fledge/notification/{}'.format('nonExistent'), json.dumps(changed_data))
        r = conn.getresponse()
        assert 404 == r.status
        r = r.read().decode()
        assert '404: No nonExistent notification instance found' == r

    def test_update_valid_notification_instance(self, fledge_url):
        changed_data = {"description": "changed_desc"}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/notification/{}'.format(urllib.parse.quote(DATA['name'])), json.dumps(changed_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Notification {} updated successfully".format(DATA["name"]) == jdoc['result']

    def test_delete_service_without_notification_delete(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/service/{}'.format(urllib.parse.quote(SERVICE_NAME)))
        r = conn.getresponse()
        assert 400 == r.status
        r = r.read().decode()
        assert "400: Notification service `{}` can not be deleted, as ['{}'] " \
               "notification instances exist.".format(SERVICE_NAME, DATA['name']) == r

    def test_delete_notification_and_service(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/notification/{}'.format(urllib.parse.quote(DATA['name'])))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Notification {} deleted successfully.".format(DATA['name']) == jdoc['result']

        conn.request("DELETE", '/fledge/service/{}'.format(urllib.parse.quote(SERVICE_NAME)))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Service {} deleted successfully.".format(SERVICE_NAME) == jdoc['result']

