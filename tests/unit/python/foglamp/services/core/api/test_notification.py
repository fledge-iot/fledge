# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
import uuid
import pytest
import json
from aiohttp import web
from unittest.mock import MagicMock, call

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.service_record import ServiceRecord
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions
from foglamp.services.core.api import notification
from foglamp.common.audit_logger import AuditLogger

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

mock_registry = [ServiceRecord(uuid.uuid4(), "Notifications", "Notification", "http", "localhost", "8118", "8118")]
rule_config = [
        {
            "name": "threshold",
            "version": "1.0.0",
            "type": "notificationRule",
            "interface": "1.0",
            "config": {
                "plugin": {
                    "description" : "The accepted tolerance",
                    "default"     : "threshold",
                    "type"        : "string"
                },
                "builtin": {
                    "description" : "Is this a builtin plugin?",
                    "default"     : "false",
                    "type"        : "boolean"
                },
                "tolerance": {
                    "description": "The accepted tolerance",
                    "default": "4",
                    "type": "integer"
                },
                "window": {
                    "description" : "The window to perform rule evaluation over in minutes",
                    "default"     : "60",
                    "type"        : "integer"
                },
                "trigger": {
                    "description" : "Temparature threshold value",
                    "default"     : "40",
                    "type"        : "integer"
                },
                "asset": {
                    "description" : "The asset the notification is defined against",
                    "default"     : "temperature",
                    "type"        : "string"
                },
            },
        },
        {
            "name": "ruleNotificationTwo",
            "version": "1.0.0",
            "type": "notificationRule",
            "interface": "1.0",
            "config": {
                "plugin": {
                    "description": "Builtin",
                    "default": "Builtin",
                    "type": "string"
                },
                "builtin": {
                    "description": "Is this a builtin plugin?",
                    "default": "true",
                    "type": "boolean"
                },
            },
        },
        {
            "name": "rulePlantAPump",
            "version": "1.0.0",
            "type": "notificationRule",
            "interface": "1.0",
            "config": {
                "plugin": {
                    "description": "Builtin",
                    "default": "Builtin",
                    "type": "string"
                },
                "builtin": {
                    "description": "Is this a builtin plugin?",
                    "default": "true",
                    "type": "boolean"
                },
            },
        },
]

delivery_config = [{
                "name": "email",
                "version": "1.0.0",
                "type": "notificationDelivery",
                "interface": "1.0",
                "config": {
                    "plugin": {
                        "description": "Email",
                        "default": "email",
                        "type": "string"
                    },
                    "server": {
                        "description" : "The smtp server",
                        "default"     : "smtp",
                        "type"        : "string"
                        },
                    "from" : {
                        "description" : "The from address to use in the email",
                        "default"     : "foglamp",
                        "type"        : "string"
                    },
                    "to" : {
                        "description" : "The address to send the notification to",
                        "default"     : "test",
                        "type"        : "string"
                    },
                },
            },
            {
                "name": "sms",
                "version": "1.0.0",
                "type": "notificationDelivery",
                "interface": "1.0",
                "config": {
                    "plugin": {
                        "description": "SMS",
                        "default": "sms",
                        "type": "string"
                    },
                    "number": {
                        "description": "The phone number to call",
                        "type": "string",
                        "default": "01111 222333"
                    },
                },
            },
            {
                "name": "deliveryPlantAPump",
                "version": "1.0.0",
                "type": "notificationDelivery",
                "interface": "1.0",
                "config": {
                    "plugin": {
                        "description": "SMS",
                        "default": "sms",
                        "type": "string"
                    },
                    "number": {
                        "description": "The phone number to call",
                        "type": "string",
                        "default": "01234 567890"
                    },
                },
            },
]

NOTIFICATION_TYPE = notification.NOTIFICATION_TYPE
notification_config = {
    "name": {
        "description": "The name of this notification",
        "type": "string",
        "default": "Test Notification",
        "value": "Test Notification",
    },
    "description": {
        "description": "Description of this notification",
        "type": "string",
        "default": "description",
        "value": "description",
    },
    "rule": {
        "description": "Rule to evaluate",
        "type": "string",
        "default": "threshold",
        "value": "threshold",
    },
    "channel": {
        "description": "Channel to send alert on",
        "type": "string",
        "default": "email",
        "value": "email",
    },
    "notification_type": {
        "description": "Type of notification",
        "type": "enumeration",
        "options": NOTIFICATION_TYPE,
        "default": "one shot",
        "value": "one shot",
    },
    "enable": {
        "description": "Enabled",
        "type": "boolean",
        "default": "true",
        "value": "true",
    }
}


@asyncio.coroutine
def mock_get_url(get_url):
    if get_url.endswith("/notification/rules"):
        return json.dumps(rule_config)
    if get_url.endswith("/notification/delivery"):
        return json.dumps(delivery_config)
    if get_url.endswith("/plugin"):
        return json.dumps({'rules': rule_config, 'delivery': delivery_config})
    if get_url.endswith("/notification"):
        return json.dumps(notification_config)
    if get_url.endswith("/foglamp/notification/Test Notification"):
        r = list(filter(lambda rules: rules['name'] == notification_config['rule']['value'], rule_config))
        c = list(filter(lambda channels: channels['name'] == notification_config['channel']['value'], delivery_config))
        if len(r) == 0 or len(c) == 0: raise KeyError
        rule_plugin_config = r[0]['config']
        delivery_plugin_config = c[0]['config']

        notif = {
            "name": notification_config['name']['value'],
            "description": notification_config['description']['value'],
            "rule": notification_config['rule']['value'],
            "ruleConfig": rule_plugin_config,
            "channel": notification_config['channel']['value'],
            "deliveryConfig": delivery_plugin_config,
            "notificationType": notification_config['notification_type']['value'],
            "enable": notification_config['enable']['value'],
        }
        return json.dumps(notif)


@asyncio.coroutine
def mock_post_url(post_url):
    if post_url.endswith("/notification/Test Notification"):
        return json.dumps({"result": "OK"})
    if post_url.endswith("/notification/Test Notification/rule/threshold"):
        return json.dumps({"result": "OK"})
    if post_url.endswith("/notification/Test Notification/delivery/email"):
        return json.dumps({"result": "OK"})

@asyncio.coroutine
def mock_delete_url(delete_url):
    return json.dumps({"result": "OK"})


@asyncio.coroutine
def mock_read_category_val(key):
    r = list(filter(lambda rules: rules['name'] == notification_config['rule']['value'], rule_config))
    c = list(filter(lambda channels: channels['name'] == notification_config['channel']['value'], delivery_config))
    if len(r) == 0 or len(c) == 0: raise KeyError
    rule_plugin_config = r[0]['config']
    delivery_plugin_config = c[0]['config']
    if key.endswith("ruleTest Notification"):
        return rule_plugin_config
    if key.endswith("deliveryTest Notification"):
        return delivery_plugin_config
    if key.endswith("Test Notification"):
        return notification_config
    return ""


@asyncio.coroutine
def mock_read_all_child_category_names():
    return [{
        "parent": "Notifications",
        "child": "Test Notification",
    }]


@asyncio.coroutine
def mock_create_category():
    return ""


@asyncio.coroutine
def mock_update_category():
    return ""


@asyncio.coroutine
def mock_create_child_category():
    return ""


@pytest.allure.feature("unit")
@pytest.allure.story("core", "api", "notification")
class TestNotification:
    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_plugin(self, mocker, client):
        rules_and_delivery = {'rules': rule_config, 'delivery': delivery_config}
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', side_effect=[mock_get_url("/notification/rules"),
                                                                       mock_get_url("/notification/delivery")])

        resp = await client.get('/foglamp/notification/plugin')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert rules_and_delivery == json_response

    async def test_get_notification(self, mocker, client):
        r = list(filter(lambda rules: rules['name'] == notification_config['rule']['value'], rule_config))
        c = list(filter(lambda channels: channels['name'] == notification_config['channel']['value'], delivery_config))
        if len(r) == 0 or len(c) == 0: raise KeyError
        rule_plugin_config = r[0]['config']
        delivery_plugin_config = c[0]['config']
        notif = {
            "name": notification_config['name']['value'],
            "description": notification_config['description']['value'],
            "rule": notification_config['rule']['value'],
            "ruleConfig": rule_plugin_config,
            "channel": notification_config['channel']['value'],
            "deliveryConfig": delivery_plugin_config,
            "notificationType": notification_config['notification_type']['value'],
            "enable": notification_config['enable']['value'],
        }

        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[
            mock_read_category_val("Test Notification"),
            mock_read_category_val("ruleTest Notification"),
            mock_read_category_val("deliveryTest Notification")])

        resp = await client.get('/foglamp/notification/Test Notification')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert notif == json_response["notification"]

    async def test_get_notifications(self, mocker, client):
        notifications = [{
            "name": notification_config['name']['value'],
            "rule": notification_config['rule']['value'],
            "channel": notification_config['channel']['value'],
            "notificationType": notification_config['notification_type']['value'],
            "enable": notification_config['enable']['value'],
        }]

        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_all_child_category_names',
                            return_value=mock_read_all_child_category_names())
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=mock_read_category_val("Test Notification"))

        resp = await client.get('/foglamp/notification')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert notifications == json_response["notifications"]

    async def test_post_notification(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=mock_get_url("/foglamp/notification/plugin"))
        mocker.patch.object(notification, '_hit_post_url',
                            side_effect=[mock_post_url("/notification/Test Notification"),
                                         mock_post_url("/notification/Test Notification/rule/threshold"),
                                         mock_post_url("/notification/Test Notification/delivery/email")])
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        update_configuration_item_bulk = mocker.patch.object(ConfigurationManager, 'update_configuration_item_bulk',
                                              return_value=mock_create_category())
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=mock_read_category_val())
        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=asyncio.sleep(.1))
        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": false}'

        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 200 == resp.status
        result = await resp.json()
        assert result['result'].endswith("Notification {} created successfully".format("Test Notification"))
        update_configuration_item_bulk_calls = [call('Test Notification', {'enable': 'false', 'rule': 'threshold', 'description': 'Test Notification', 'channel': 'email', 'notification_type': 'one shot'})]
        update_configuration_item_bulk.assert_has_calls(update_configuration_item_bulk_calls, any_order=True)

    async def test_post_notification2(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=mock_get_url("/foglamp/notification/plugin"))
        mocker.patch.object(notification, '_hit_post_url',
                            side_effect=[mock_post_url("/notification/Test Notification"),
                                         mock_post_url("/notification/Test Notification/rule/threshold"),
                                         mock_post_url("/notification/Test Notification/delivery/email")])
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=asyncio.sleep(.1))
        update_configuration_item_bulk = mocker.patch.object(ConfigurationManager, 'update_configuration_item_bulk',
                                              return_value=mock_create_category())
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=mock_read_category_val())
        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": false, "rule_config":{"window": "100"}, "delivery_config": {"server": "pop"}}'

        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 200 == resp.status
        result = await resp.json()
        assert result['result'].endswith("Notification {} created successfully".format("Test Notification"))
        update_configuration_item_bulk_calls = [call('Test Notification', {'description': 'Test Notification', 'rule': 'threshold', 'channel': 'email',
                                        'notification_type': 'one shot', 'enable': 'false'}),
             call('ruleTest Notification', {'window': '100'}),
             call('deliveryTest Notification', {'server': 'pop'})]
        update_configuration_item_bulk.assert_has_calls(update_configuration_item_bulk_calls, any_order=True)

    async def test_post_notification_exception(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=mock_get_url("/foglamp/notification/plugin"))
        mocker.patch.object(notification, '_hit_post_url',
                            side_effect=[mock_post_url("/notification/Test Notification"),
                                         mock_post_url("/notification/Test Notification/rule/threshold"),
                                         mock_post_url("/notification/Test Notification/delivery/email")])
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        create_category = mocker.patch.object(ConfigurationManager, 'create_category',
                                              return_value=mock_create_category())
        create_child_category = mocker.patch.object(ConfigurationManager, 'create_child_category',
                                                    return_value=mock_create_child_category())
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=mock_read_category_val())

        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=asyncio.sleep(.1))
        mock_payload = '{"description":"Test Notification", "rule": "threshold", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing name property in payload.')

        mock_payload = '{"name": "", "description":"Test Notification", "rule": "threshold", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing name property in payload.')

        mock_payload = '{"name": "Test Notification", "rule": "threshold", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing description property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing rule property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing channel property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing notification_type property in payload.')

        mock_payload = '{"name": ";", "description":"Test Notification", "rule": "threshold", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid name property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": ";", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid rule property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": ";", "notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid channel property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": ";", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid notification_type property in payload.')


        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": fals}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Expecting value: line 1 column 151 (char 150)')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshol", ' \
                       '"channel": "emai", "notification_type": "one shot", "enabled": false}'
        resp = await client.post("/foglamp/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith(
            "Invalid rule plugin:[{}] and/or delivery plugin:[{}] supplied.".format("threshol", "emai"))

    async def test_put_notification(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=mock_get_url("/foglamp/notification/plugin"))
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        update_configuration_item_bulk = mocker.patch.object(ConfigurationManager, 'update_configuration_item_bulk',
                                              return_value=mock_create_category())
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=mock_read_category_val("Test Notification"))
        create_category = mocker.patch.object(ConfigurationManager, 'create_category',
                                              return_value=mock_create_category())
        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "sms", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'

        resp = await client.put("/foglamp/notification/Test Notification", data=mock_payload)
        assert 200 == resp.status
        result = await resp.json()
        assert result['result'].endswith("Notification {} updated successfully".format("Test Notification"))
        update_configuration_item_bulk_calls = [call('Test Notification', {'description': 'Test Notification', 'notification_type': 'one shot', 'enable': 'false', 'rule': 'threshold', 'channel': 'sms'}),
                                                call('ruleTest Notification', {'asset': 'temperature', 'trigger': '70', 'tolerance': '4', 'window': '60'}),
                                                call('deliveryTest Notification', {'number': '07812 343830'})]
        update_configuration_item_bulk.assert_has_calls(update_configuration_item_bulk_calls, any_order=True)


    async def test_put_notification_exception(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=mock_get_url("/foglamp/notification/plugin"))
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        update_configuration_item_bulk = mocker.patch.object(ConfigurationManager, 'update_configuration_item_bulk',
                                              return_value=mock_create_category())
        create_category = mocker.patch.object(ConfigurationManager, 'create_category',
                                              return_value=mock_create_category())
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=mock_read_category_val("Test Notification"))

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "sms", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/foglamp/notification", data=mock_payload)
        assert 405 == resp.status
        result = await resp.text()
        assert result.endswith(" Method Not Allowed")

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": ";", ' \
                       '"channel": "sms", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/foglamp/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid rule property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": ";", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/foglamp/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid channel property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "sms", "notification_type": ";", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/foglamp/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid notification_type property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "sms", "notification_type": "one shot", "enabled": fals, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/foglamp/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Expecting value: line 1 column 149 (char 148)')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshol", ' \
                       '"channel": "sm", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/foglamp/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith(
            "Invalid rule plugin:{} and/or delivery plugin:{} supplied.".format("threshol", "sm"))

    async def test_delete_notification(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=mock_get_url("/foglamp/notification/plugin"))
        storage_client_mock = mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=mock_read_category_val("Test Notification"))
        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=asyncio.sleep(.1))

        c_mgr = ConfigurationManager(storage_client_mock)
        delete_configuration = mocker.patch.object(ConfigurationManager, "delete_category_and_children_recursively", return_value=asyncio.sleep(.1))
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=asyncio.sleep(.1))

        mocker.patch.object(notification, '_hit_delete_url',
                            side_effect=[mock_delete_url("/notification/Test Notification")])

        resp = await client.delete("/foglamp/notification/Test Notification")
        assert 200 == resp.status
        result = await resp.json()
        assert result['result'].endswith("Notification {} deleted successfully.".format("Test Notification"))
        args, kwargs = delete_configuration.call_args_list[0]
        assert "Test Notification" in args

        assert 1 == audit_logger.call_count
        print(audit_logger.call_args_list)
        audit_logger_calls = [call('NTFDL', {'name': 'Test Notification'})]
        audit_logger.assert_has_calls(audit_logger_calls, any_order=True)

    async def test_delete_notification_exception(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=mock_get_url("/foglamp/notification/plugin"))
        storage_client_mock = mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=mock_read_category_val("Test Notification"))
        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=asyncio.sleep(.1))

        c_mgr = ConfigurationManager(storage_client_mock)
        delete_configuration = mocker.patch.object(ConfigurationManager, "delete_category_and_children_recursively", return_value=asyncio.sleep(.1))

        resp = await client.delete("/foglamp/notification")
        assert 405 == resp.status
        result = await resp.text()
        assert result.endswith(" Method Not Allowed")

    async def test_registry_exception(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', side_effect=service_registry_exceptions.DoesNotExist)
        resp = await client.delete("/foglamp/notification/Test Notification")
        assert 404 == resp.status
        result = await resp.text()
        assert result.endswith("No Notification service available.")
