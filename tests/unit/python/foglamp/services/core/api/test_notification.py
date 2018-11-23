# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
import json
from unittest.mock import MagicMock, patch, call
from datetime import timedelta, datetime
import uuid
import pytest
import json
import aiohttp
from aiohttp import web
import sys
import os
import time
import copy

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.common.service_record import ServiceRecord
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions
from foglamp.common.audit_logger import AuditLogger
from foglamp.services.core.api import notification


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


mock_registry = [ServiceRecord(uuid.uuid4(), "Notifications", "Notification", "http", "localhost", "8118", "8118")]
rule_config = {
    "threshold": {
        "plugin": {
            "description": "The accepted tolerance",
            "default": "threshold",
            "value": "threshold",
            "type": "string"
        },
        "tolerance": {
            "description": "The accepted tolerance",
            "default": "4",
            "value": "4",
            "type": "integer"
        },
        "window": {
            "description": "The window to perform rule evaluation over in minutes",
            "default": "60",
            "value": "60",
            "type": "integer"
        },
        "trigger": {
            "description": "Temparature threshold value",
            "default": "40",
            "value": "40",
            "type": "integer"
        },
        "asset": {
            "description": "The asset the notification is defined against",
            "default": "temperature",
            "value": "temperature",
            "type": "string"
        }
    }
}

delivery_config = {"email": {
        "plugin": {
            "description": "Email",
            "default": "email",
            "value": "email",
            "type": "string"
        },
        "server": {
            "description": "The smtp server",
            "default": "smtp",
            "value": "smtp",
            "type": "string"
        },
        "from": {
            "description": "The from address to use in the email",
            "default": "foglamp",
            "value": "foglamp",
            "type": "string"
        },
        "to": {
            "description": "The address to send the notification to",
            "default": "test",
            "value": "test",
            "type": "string"
        }
    },
    "sms": {
        "plugin": {
            "description": "SMS",
            "default": "sms",
            "value": "sms",
            "type": "string"
        },
        "number": {
            "description": "The phone number to call",
            "default": "07812 343830",
            "value": "07812 343830",
            "type": "string",
        }
    }
}

NOTIFICATION_TYPE = ["one shot", "retriggered", "toggled"]
notification_config = {
    "name": {
        "description": "The name of this notification",
        "type": "string",
        "default": "TestNotification",
        "value": "TestNotification",
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
    if get_url.endswith("/foglamp/notification/rules"):
        return json.dumps(rule_config)
    if get_url.endswith("/foglamp/notification/delivery"):
        return json.dumps(delivery_config)
    if get_url.endswith("/plugin"):
        return json.dumps({'rules': rule_config, 'delivery': delivery_config})
    if get_url.endswith("/foglamp/notification"):
        pass
    if get_url.endswith("/foglamp/notification/Test Notification"):
        pass


@asyncio.coroutine
def mock_read_category_val(key):
    if key.endswith("ruleTestNotification"):
        return rule_config[notification_config['rule']['value']]
    if key.endswith("deliveryTestNotification"):
        return delivery_config[notification_config['channel']['value']]
    if key.endswith("TestNotification"):
        return notification_config


@asyncio.coroutine
def mock_read_all_child_category_names():
    return [{
        "parent": "Notifications",
        "child": "TestNotification",
    }]


@asyncio.coroutine
def mock_post_url(post_url):
    if post_url.endswith("/foglamp/notification/rules"):
        return json.dumps(rule_config)
    if post_url.endswith("/foglamp/notification/delivery"):
        return json.dumps(delivery_config)
    if post_url.endswith("/plugin"):
        return json.dumps({'rules': rule_config, 'delivery': delivery_config})
    if post_url.endswith("/foglamp/notification"):
        pass
    if post_url.endswith("/foglamp/notification/Test Notification"):
        pass


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
        mocker.patch.object(notification, '_hit_get_url', side_effect=[mock_get_url("/foglamp/notification/rules"),
                                                                       mock_get_url("/foglamp/notification/delivery")])

        resp = await client.get('/foglamp/notification/plugin')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert rules_and_delivery == json_response

    async def test_get_notification(self, mocker, client):
        notif = {
            "name": notification_config['name']['value'],
            "description": notification_config['description']['value'],
            "rule": notification_config['rule']['value'],
            "ruleConfig": rule_config[notification_config['rule']['value']],
            "channel": notification_config['channel']['value'],
            "deliveryConfig": delivery_config[notification_config['channel']['value']],
            "notificationType": notification_config['notification_type']['value'],
            "enable": notification_config['enable']['value'],
        }

        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(ConfigurationManager, '__init__', return_value=None)
        mocker.patch.object(ConfigurationManager, '_read_category_val', side_effect=[
            mock_read_category_val("TestNotification"),
            mock_read_category_val("ruleTestNotification"),
            mock_read_category_val("deliveryTestNotification")])

        resp = await client.get('/foglamp/notification/TestNotification')
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
        mocker.patch.object(ConfigurationManager, '_read_all_child_category_names', return_value=mock_read_all_child_category_names())
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=mock_read_category_val("TestNotification"))

        resp = await client.get('/foglamp/notification')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert notifications == json_response["notifications"]
