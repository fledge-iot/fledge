# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


import asyncio
import uuid
import pytest
import json
import sys
from aiohttp import web
from unittest.mock import MagicMock, call

from fledge.services.core import routes
from fledge.services.core import connect
from fledge.common.service_record import ServiceRecord
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.services.core.api import notification
from fledge.common.audit_logger import AuditLogger

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
                        "default"     : "fledge",
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
    },
    "retrigger_time": {
        "description": "Retrigger time in seconds for sending a new notification.",
        "type": "integer",
        "default": "60",
        "value": "60",
    }
}

delivery_channel_config = {
    "action": {
      "description": "Perform a control action to turn pump",
      "type": "boolean",
      "default": "false"
    }
  }


async def mock_get_url(get_url):
    if get_url.endswith("/notification/rules"):
        return json.dumps(rule_config)
    if get_url.endswith("/notification/delivery"):
        return json.dumps(delivery_config)
    if get_url.endswith("/plugin"):
        return json.dumps({'rules': rule_config, 'delivery': delivery_config})
    if get_url.endswith("/notification"):
        return json.dumps(notification_config)
    if get_url.endswith("/fledge/notification/Test Notification"):
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
            "retriggerTime": notification_config['retrigger_time']['value'],
            "enable": notification_config['enable']['value'],
        }
        return json.dumps(notif)


async def mock_post_url(post_url):
    if post_url.endswith("/notification/Test Notification"):
        return json.dumps({"result": "OK"})
    if post_url.endswith("/notification/Test Notification/rule/threshold"):
        return json.dumps({"result": "OK"})
    if post_url.endswith("/notification/Test Notification/delivery/email"):
        return json.dumps({"result": "OK"})

async def mock_delete_url(delete_url):
    return json.dumps({"result": "OK"})


async def mock_read_category_val(key):
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
    if key.endswith("overspeed"):
        return delivery_channel_config
    if key.endswith("foo"):
        return {}
    if key.endswith("bar"):
        return []
    if key.endswith("coolant"):
        return ["coolant"]


async def mock_read_all_child_category_names():
    return [{
        "parent": "Notifications",
        "child": "Test Notification",
    }]


async def mock_create_category():
    return ""


async def mock_update_category():
    return ""


async def mock_create_child_category():
    return ""


async def mock_check_category(val=None):
    return val


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
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _se1 = await mock_get_url("/notification/rules")
            _se2 = await mock_get_url("/notification/delivery")
        else:
            _se1 = asyncio.ensure_future(mock_get_url("/notification/rules"))
            _se2 = asyncio.ensure_future(mock_get_url("/notification/delivery"))
        
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', side_effect=[_se1, _se2])

        resp = await client.get('/fledge/notification/plugin')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert rules_and_delivery == json_response

    async def test_get_type(self, client):
        notification_type = {'notification_type': NOTIFICATION_TYPE}
        resp = await client.get('/fledge/notification/type')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert notification_type == json_response

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
            "retriggerTime": notification_config['retrigger_time']['value'],
            "enable": notification_config['enable']['value'],
        }

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _se1 = await mock_read_category_val("Test Notification")
            _se2 = await mock_read_category_val("ruleTest Notification")
            _se3 = await mock_read_category_val("deliveryTest Notification")
        else:
            _se1 = asyncio.ensure_future(mock_read_category_val("Test Notification"))
            _se2 = asyncio.ensure_future(mock_read_category_val("ruleTest Notification"))
            _se3 = asyncio.ensure_future(mock_read_category_val("deliveryTest Notification"))         
        
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[_se1, _se2, _se3])

        resp = await client.get('/fledge/notification/Test Notification')
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
            "retriggerTime": notification_config['retrigger_time']['value'],
            "enable": notification_config['enable']['value'],
        }]

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_read_all_child_category_names()
            _rv2 = await mock_read_category_val("Test Notification")
        else:
            _rv1 = asyncio.ensure_future(mock_read_all_child_category_names())
            _rv2 = asyncio.ensure_future(mock_read_category_val("Test Notification"))
        
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_all_child_category_names',
                            return_value=_rv1)
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=_rv2)

        resp = await client.get('/fledge/notification')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert notifications == json_response["notifications"]

    async def test_post_notification(self, mocker, client):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_get_url("/fledge/notification/plugin")
            _rv2 = await mock_create_category()
            _rv3 = await mock_read_category_val("")
            _rv4 = await mock_check_category()
            _rv5 = await asyncio.sleep(.1)
            _se1 = await mock_post_url("/notification/Test Notification")
            _se2 = await mock_post_url("/notification/Test Notification/rule/threshold")
            _se3 = await mock_post_url("/notification/Test Notification/delivery/email")
        else:
            _rv1 = asyncio.ensure_future(mock_get_url("/fledge/notification/plugin"))
            _rv2 = asyncio.ensure_future(mock_create_category())
            _rv3 = asyncio.ensure_future(mock_read_category_val(""))
            _rv4 = asyncio.ensure_future(mock_check_category())
            _rv5 = asyncio.ensure_future(asyncio.sleep(.1))
            _se1 = asyncio.ensure_future(mock_post_url("/notification/Test Notification"))
            _se2 = asyncio.ensure_future(mock_post_url("/notification/Test Notification/rule/threshold"))
            _se3 = asyncio.ensure_future(mock_post_url("/notification/Test Notification/delivery/email"))        
        
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=_rv1)
        mocker.patch.object(notification, '_hit_post_url',
                            side_effect=[_se1, _se2, _se3])
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        update_configuration_item_bulk = mocker.patch.object(ConfigurationManager, 'update_configuration_item_bulk',
                                              return_value=_rv2)
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=_rv3)
        mocker.patch.object(ConfigurationManager, 'get_category_all_items', return_value=_rv4)
        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=_rv5)
        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": false}'

        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 200 == resp.status
        result = await resp.json()
        assert result['result'].endswith("Notification {} created successfully".format("Test Notification"))
        update_configuration_item_bulk_calls = [call('Test Notification', {'enable': 'false', 'rule': 'threshold', 'description': 'Test Notification', 'channel': 'email', 'notification_type': 'one shot'})]
        update_configuration_item_bulk.assert_has_calls(update_configuration_item_bulk_calls, any_order=True)

    async def test_post_notification_duplicate_name(self, mocker, client):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_check_category(True)
        else:
            _rv = asyncio.ensure_future(mock_check_category(True))
        
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, 'get_category_all_items', return_value=_rv)
        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": false}'

        # Check duplicate name
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert "400: A Category with name Test Notification already exists." == result

    async def test_post_notification2(self, mocker, client):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_get_url("/fledge/notification/plugin")
            _rv2 = await mock_create_category()
            _rv3 = await mock_read_category_val("")
            _rv4 = await mock_check_category()
            _rv5 = await asyncio.sleep(.1)
            _se1 = await mock_post_url("/notification/Test Notification")
            _se2 = await mock_post_url("/notification/Test Notification/rule/threshold")
            _se3 = await mock_post_url("/notification/Test Notification/delivery/email")
        else:
            _rv1 = asyncio.ensure_future(mock_get_url("/fledge/notification/plugin"))
            _rv2 = asyncio.ensure_future(mock_create_category())
            _rv3 = asyncio.ensure_future(mock_read_category_val(""))
            _rv4 = asyncio.ensure_future(mock_check_category())
            _rv5 = asyncio.ensure_future(asyncio.sleep(.1))
            _se1 = asyncio.ensure_future(mock_post_url("/notification/Test Notification"))
            _se2 = asyncio.ensure_future(mock_post_url("/notification/Test Notification/rule/threshold"))
            _se3 = asyncio.ensure_future(mock_post_url("/notification/Test Notification/delivery/email"))      
        
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=_rv1)
        mocker.patch.object(notification, '_hit_post_url',
                            side_effect=[_se1, _se2, _se3])
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=_rv5)
        update_configuration_item_bulk = mocker.patch.object(ConfigurationManager, 'update_configuration_item_bulk',
                                              return_value=_rv2)
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=_rv3)
        mocker.patch.object(ConfigurationManager, 'get_category_all_items', return_value=_rv4)
        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": false, "rule_config":{"window": "100"}, "delivery_config": {"server": "pop"}}'

        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 200 == resp.status
        result = await resp.json()
        assert result['result'].endswith("Notification {} created successfully".format("Test Notification"))
        update_configuration_item_bulk_calls = [call('Test Notification', {'description': 'Test Notification', 'rule': 'threshold', 'channel': 'email',
                                        'notification_type': 'one shot', 'enable': 'false'}),
             call('ruleTest Notification', {'window': '100'}),
             call('deliveryTest Notification', {'server': 'pop'})]
        update_configuration_item_bulk.assert_has_calls(update_configuration_item_bulk_calls, any_order=True)

    async def test_post_notification_exception(self, mocker, client):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_get_url("/fledge/notification/plugin")
            _rv2 = await mock_create_category()
            _rv3 = await mock_read_category_val("")
            _rv4 = await mock_check_category()
            _rv5 = await asyncio.sleep(.1)
            _rv6 = await mock_create_child_category()
            _se1 = await mock_post_url("/notification/Test Notification")
            _se2 = await mock_post_url("/notification/Test Notification/rule/threshold")
            _se3 = await mock_post_url("/notification/Test Notification/delivery/email")
        else:
            _rv1 = asyncio.ensure_future(mock_get_url("/fledge/notification/plugin"))
            _rv2 = asyncio.ensure_future(mock_create_category())
            _rv3 = asyncio.ensure_future(mock_read_category_val(""))
            _rv4 = asyncio.ensure_future(mock_check_category())
            _rv5 = asyncio.ensure_future(asyncio.sleep(.1))
            _rv6 = asyncio.ensure_future(mock_create_child_category())
            _se1 = asyncio.ensure_future(mock_post_url("/notification/Test Notification"))
            _se2 = asyncio.ensure_future(mock_post_url("/notification/Test Notification/rule/threshold"))
            _se3 = asyncio.ensure_future(mock_post_url("/notification/Test Notification/delivery/email"))
        
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=_rv1)
        mocker.patch.object(notification, '_hit_post_url',
                            side_effect=[_se1, _se2, _se3])
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        create_category = mocker.patch.object(ConfigurationManager, 'create_category',
                                              return_value=_rv2)
        create_child_category = mocker.patch.object(ConfigurationManager, 'create_child_category',
                                                    return_value=_rv6)
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=_rv3)
        mocker.patch.object(ConfigurationManager, 'get_category_all_items', return_value=_rv4)

        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=_rv5)
        mock_payload = '{"description":"Test Notification", "rule": "threshold", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing name property in payload.')

        mock_payload = '{"name": "", "description":"Test Notification", "rule": "threshold", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing name property in payload.')

        mock_payload = '{"name": "Test Notification", "rule": "threshold", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing description property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing rule property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing channel property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Missing notification_type property in payload.')

        mock_payload = '{"name": ";", "description":"Test Notification", "rule": "threshold", "channel": "email", ' \
                       '"notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid name property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": ";", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid rule property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": ";", "notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid channel property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": ";", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid notification_type property in payload.')


        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "email", "notification_type": "one shot", "enabled": fals}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Expecting value: line 1 column 151 (char 150)')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshol", ' \
                       '"channel": "emai", "notification_type": "one shot", "enabled": false}'
        resp = await client.post("/fledge/notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith(
            "Invalid rule plugin {} and/or delivery plugin {} supplied.".format("threshol", "emai"))

    async def test_put_notification(self, mocker, client):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_get_url("/fledge/notification/plugin")
            _rv2 = await mock_create_category()
            _rv3 = await mock_read_category_val("Test Notification")
        else:
            _rv1 = asyncio.ensure_future(mock_get_url("/fledge/notification/plugin"))
            _rv2 = asyncio.ensure_future(mock_create_category())
            _rv3 = asyncio.ensure_future(mock_read_category_val("Test Notification"))
        
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=_rv1)
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        update_configuration_item_bulk = mocker.patch.object(ConfigurationManager, 'update_configuration_item_bulk',
                                              return_value=_rv2)
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=_rv3)
        create_category = mocker.patch.object(ConfigurationManager, 'create_category',
                                              return_value=_rv2)
        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "sms", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'

        resp = await client.put("/fledge/notification/Test Notification", data=mock_payload)
        assert 200 == resp.status
        result = await resp.json()
        assert result['result'].endswith("Notification {} updated successfully".format("Test Notification"))
        update_configuration_item_bulk_calls = [call('Test Notification', {'description': 'Test Notification', 'notification_type': 'one shot', 'enable': 'false', 'rule': 'threshold', 'channel': 'sms'}),
                                                call('ruleTest Notification', {'asset': 'temperature', 'trigger': '70', 'tolerance': '4', 'window': '60'}),
                                                call('deliveryTest Notification', {'number': '07812 343830'})]
        update_configuration_item_bulk.assert_has_calls(update_configuration_item_bulk_calls, any_order=True)


    async def test_put_notification_exception(self, mocker, client):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_get_url("/fledge/notification/plugin")
            _rv2 = await mock_create_category()
            _rv3 = await mock_read_category_val("Test Notification")
        else:
            _rv1 = asyncio.ensure_future(mock_get_url("/fledge/notification/plugin"))
            _rv2 = asyncio.ensure_future(mock_create_category())
            _rv3 = asyncio.ensure_future(mock_read_category_val("Test Notification"))
        
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=_rv1)
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        update_configuration_item_bulk = mocker.patch.object(ConfigurationManager, 'update_configuration_item_bulk',
                                              return_value=_rv2)
        create_category = mocker.patch.object(ConfigurationManager, 'create_category',
                                              return_value=_rv2)
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=_rv3)

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "sms", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/fledge/notification", data=mock_payload)
        assert 405 == resp.status
        result = await resp.text()
        assert result.endswith(" Method Not Allowed")

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": ";", ' \
                       '"channel": "sms", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/fledge/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid rule property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": ";", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/fledge/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid channel property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "sms", "notification_type": ";", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/fledge/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Invalid notification_type property in payload.')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", ' \
                       '"channel": "sms", "notification_type": "one shot", "enabled": fals, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/fledge/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith('Expecting value: line 1 column 149 (char 148)')

        mock_payload = '{"name": "Test Notification", "description":"Test Notification", "rule": "threshol", ' \
                       '"channel": "sm", "notification_type": "one shot", "enabled": false, ' \
                       '"rule_config": {"asset": "temperature", "trigger": "70", "window": "60", "tolerance": "4"}, ' \
                       '"delivery_config": {"number": "07812 343830"} }'
        resp = await client.put("/fledge/notification/Test Notification", data=mock_payload)
        assert 400 == resp.status
        result = await resp.text()
        assert result.endswith(
            "Invalid rule plugin:{} and/or delivery plugin:{} supplied.".format("threshol", "sm"))

    async def test_delete_notification(self, mocker, client):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_get_url("/fledge/notification/plugin")
            _rv2 = await asyncio.sleep(.1)
            _rv3 = await mock_read_category_val("Test Notification")
            _se = await mock_delete_url("/notification/Test Notification")
        else:
            _rv1 = asyncio.ensure_future(mock_get_url("/fledge/notification/plugin"))
            _rv2 = asyncio.ensure_future(asyncio.sleep(.1))
            _rv3 = asyncio.ensure_future(mock_read_category_val("Test Notification"))
            _se = asyncio.ensure_future(mock_delete_url("/notification/Test Notification"))
            
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=_rv1)
        storage_client_mock = mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=_rv3)
        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=_rv2)

        c_mgr = ConfigurationManager(storage_client_mock)
        delete_configuration = mocker.patch.object(ConfigurationManager, "delete_category_and_children_recursively", return_value=_rv2)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=_rv2)

        mocker.patch.object(notification, '_hit_delete_url', side_effect=[_se])

        resp = await client.delete("/fledge/notification/Test Notification")
        assert 200 == resp.status
        result = await resp.json()
        assert result['result'].endswith("Notification {} deleted successfully.".format("Test Notification"))
        args, kwargs = delete_configuration.call_args_list[0]
        assert "Test Notification" in args

        assert 1 == audit_logger.call_count
        audit_logger_calls = [call('NTFDL', {'name': 'Test Notification'})]
        audit_logger.assert_has_calls(audit_logger_calls, any_order=True)

    async def test_delete_notification_exception(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        mocker.patch.object(notification, '_hit_get_url', return_value=(await mock_get_url("/fledge/notification/plugin")))
        storage_client_mock = mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val',
                            return_value=(await mock_read_category_val("Test Notification")))
        mocker.patch.object(AuditLogger, "__init__", return_value=None)
        audit_logger = mocker.patch.object(AuditLogger, "information", return_value=(await asyncio.sleep(.1)))

        c_mgr = ConfigurationManager(storage_client_mock)
        delete_configuration = mocker.patch.object(ConfigurationManager, "delete_category_and_children_recursively", return_value=(await asyncio.sleep(.1)))

        resp = await client.delete("/fledge/notification")
        assert 405 == resp.status
        result = await resp.text()
        assert result.endswith(" Method Not Allowed")

    async def test_registry_exception(self, mocker, client):
        mocker.patch.object(ServiceRegistry, 'get', side_effect=service_registry_exceptions.DoesNotExist)
        resp = await client.delete("/fledge/notification/Test Notification")
        assert 404 == resp.status
        result = await resp.text()
        assert result.endswith("No Notification service available.")

    @pytest.mark.parametrize("payload, message", [
        ({}, "Missing name property in payload"),
        ({"name": ""}, "Name should not be empty"),
        ({"name": " "}, "Name should not be empty"),
        ({"name": "Test@123"}, "name should not use reserved words"),
        ({"name": "Test123", "config": ""}, "config must be a valid JSON")
    ])
    async def test_bad_post_delivery_channel(self, client, payload, message):
        resp = await client.post("/fledge/notification/overspeed/delivery", data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        r = await resp.text()
        json_response = json.loads(r)
        assert {"message": message} == json_response

    @pytest.mark.parametrize("name, config, description", [
        ("coolant", delivery_channel_config, None),
        (" coolant2", {}, ''),
        (" coolant3", {}, 'Test coolant'),
    ])
    async def test_good_post_delivery_channel(self, mocker, client, name, config, description):
        notification_instance_name = "overspeed"
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            _se = await mock_read_category_val(notification_instance_name)
            _rv1 = await mock_create_category()
            _rv2 = await mock_check_category(delivery_channel_config)
            _rv3 = await mock_create_child_category()
        else:
            _se = asyncio.ensure_future(mock_read_category_val(notification_instance_name))
            _rv1 = asyncio.ensure_future(mock_create_category())
            _rv2 = asyncio.ensure_future(mock_check_category(delivery_channel_config))
            _rv3 = asyncio.ensure_future(mock_create_child_category())
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[_se])
        mocker.patch.object(ConfigurationManager, 'create_category', return_value=_rv1)
        mocker.patch.object(ConfigurationManager, 'get_category_all_items', return_value=_rv2)
        mocker.patch.object(ConfigurationManager, 'create_child_category', return_value=_rv3)
        payload = {"name": name, "config": config}
        expected_description = "{} delivery channel".format(name.strip())
        if description is not None:
            payload['description'] = description
            expected_description = description
        resp = await client.post("/fledge/notification/{}/delivery".format(notification_instance_name), data=json.dumps(payload))
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        expected_cat_name = "{}_channel_{}".format(notification_instance_name, name.strip())
        assert expected_cat_name == json_response['category']
        assert config == json_response['config']
        assert expected_description == json_response['description']

    async def test_bad_get_delivery_channel(self, mocker, client):
        notification_instance_name = "blah"
        message = "{} notification instance does not exist".format(notification_instance_name)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _se = await mock_read_category_val(notification_instance_name) if sys.version_info >= (3, 8) else \
            asyncio.ensure_future(mock_read_category_val(notification_instance_name))
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[_se])

        resp = await client.get('/fledge/notification/{}/delivery'.format(notification_instance_name))
        assert 404 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    @pytest.mark.parametrize("notification_instance_name, categories, exp_channel, plugin_type", [
        ("overspeed", [], [], {}),
        ("overspeed", [("overspeed_channel_coolant", 1), ("Pump_channel_coolant2", 2)], ['coolant'], {}),
        ("overspeed", [("overspeed_channel_coolant", 1), ("overspeed_channel_coolant2", 2)], ['coolant', 'coolant2'], {}),
        ("overspeed", [("deliveryoverspeed", 1), ("overspeed_channel_coolant2", 2)], ['deliveryoverspeed', 'coolant2'], {}),
        ("overspeed", [("deliveryoverspeed", 1), ("overspeed_channel_coolant2", 2)], ['deliveryoverspeed/mqtt', 'coolant2'], {"value": {"plugin": {"value": "mqtt" }}})
    ])
    async def test_good_get_delivery_channel(self, mocker, client, notification_instance_name, categories, exp_channel, plugin_type):
        async def async_mock(cat):
            return cat

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            _se = await mock_read_category_val(notification_instance_name)
            _rv = await async_mock(categories)
            _rv2 = await async_mock(plugin_type)
        else:
            _se = asyncio.ensure_future(mock_read_category_val(notification_instance_name))
            _rv = asyncio.ensure_future(async_mock(categories))
            _rv2 = asyncio.ensure_future(async_mock(plugin_type))

        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[_se])
        mocker.patch.object(ConfigurationManager, 'get_all_category_names', return_value=_rv)
        mocker.patch.object(ConfigurationManager, '_read_category', return_value=_rv2)
        resp = await client.get('/fledge/notification/{}/delivery'.format(notification_instance_name))
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert exp_channel == json_response['channels']

    @pytest.mark.parametrize("notification_instance_name, channel_name, message", [
        ("foo", "bar", "foo notification instance does not exist"),
        ("Test Notification", "bar", "bar channel does not exist")
    ])
    async def test_bad_get_delivery_channel_configuration(self, mocker, client, notification_instance_name,
                                                          channel_name, message):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            _se1 = await mock_read_category_val(notification_instance_name)
            _se2 = await mock_read_category_val(channel_name)
        else:
            _se1 = asyncio.ensure_future(mock_read_category_val(notification_instance_name))
            _se2 = asyncio.ensure_future(mock_read_category_val(channel_name))
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[_se1])
        mocker.patch.object(notification, '_get_channels', side_effect=[_se2])
        resp = await client.get('/fledge/notification/{}/delivery/{}'.format(notification_instance_name, channel_name))
        assert 404 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    async def test_good_get_delivery_channel_configuration(self, mocker, client):
        notification_instance_name = "overspeed"
        channel_name = "coolant"
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            _se1 = await mock_read_category_val(notification_instance_name)
            _se2 = await mock_read_category_val(channel_name)
        else:
            _se1 = asyncio.ensure_future(mock_read_category_val(notification_instance_name))
            _se2 = asyncio.ensure_future(mock_read_category_val(channel_name))
            _rv = asyncio.ensure_future(asyncio.sleep(.1))
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[_se1, _se1])
        mocker.patch.object(notification, '_get_channels', side_effect=[_se2])
        resp = await client.get('/fledge/notification/{}/delivery/{}'.format(notification_instance_name, channel_name))
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert 'config' in json_response
        assert delivery_channel_config == json_response['config']

    @pytest.mark.parametrize("notification_instance_name, channel_name, message", [
        ("foo", "bar", "No Notification service available."),
        ("Test Notification", "bar", "No Notification service available.")
    ])
    async def test_bad_delete_delivery_channel(self, mocker, client, notification_instance_name, channel_name, message):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            _se1 = await mock_read_category_val(notification_instance_name)
            _se2 = await mock_read_category_val(channel_name)
        else:
            _se1 = asyncio.ensure_future(mock_read_category_val(notification_instance_name))
            _se2 = asyncio.ensure_future(mock_read_category_val(channel_name))
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[_se1])
        mocker.patch.object(notification, '_get_channels', side_effect=[_se2])
        resp = await client.delete('/fledge/notification/{}/delivery/{}'.format(notification_instance_name,
                                                                                channel_name))
        assert 404 == resp.status
        assert message == resp.reason
        result = await resp.text()
        #// FIXME_I:
        #json_response = json.loads(result)
        #assert {"message": message} == json_response

    # FIXME:
    #@pytest.mark.this
    async def test_good_delete_delivery_channel(self, mocker, client):
        notification_instance_name = "overspeed"
        channel_name = "coolant"
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            _se1 = await mock_read_category_val(notification_instance_name)
            _se2 = await mock_read_category_val(channel_name)
            _se3 = await mock_read_category_val("bar")
            _rv = await asyncio.sleep(.1)
        else:
            _se1 = asyncio.ensure_future(mock_read_category_val(notification_instance_name))
            _se2 = asyncio.ensure_future(mock_read_category_val(channel_name))
            _se3 = asyncio.ensure_future(mock_read_category_val("bar"))
            _rv = asyncio.ensure_future(asyncio.sleep(.1))
        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[_se1])
        mocker.patch.object(notification, '_get_channels', side_effect=[_se2, _se3])
        mocker.patch.object(ConfigurationManager, 'delete_category_and_children_recursively', return_value=_rv)
        resp = await client.delete('/fledge/notification/{}/delivery/{}'.format(notification_instance_name,
                                                                                channel_name))
        #// FIXME_I:
        #assert 200 == resp.status
        #result = await resp.text()
        #json_response = json.loads(result)
        #assert [] == json_response['channels']
