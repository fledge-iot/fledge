# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
import json
from uuid import UUID
from aiohttp import web
import pytest
from unittest.mock import MagicMock, patch, call
from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.common.service_record import ServiceRecord
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry
from foglamp.services.core import server
from foglamp.services.core.scheduler.scheduler import Scheduler
from foglamp.services.core.scheduler.entities import StartUpSchedule
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.api import service

from foglamp.services.core.api.service import _logger

__author__ = "Ashwin Gopalakrishnan, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "service")
class TestService:
    def setup_method(self):
        ServiceRegistry._registry = list()

    def teardown_method(self):
        ServiceRegistry._registry = list()

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @asyncio.coroutine
    def async_mock(self, return_value):
        return return_value

    async def test_get_health(self, mocker, client):
        # empty service registry
        resp = await client.get('/foglamp/service')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert {'services': []} == json_response

        mocker.patch.object(InterestRegistry, "__init__", return_value=None)
        mocker.patch.object(InterestRegistry, "get", return_value=list())

        with patch.object(ServiceRegistry._logger, 'info') as log_patch_info:
            # populated service registry
            ServiceRegistry.register(
                'name1', 'Storage', 'address1', 1, 1, 'protocol1')
            ServiceRegistry.register(
                'name2', 'Southbound', 'address2', 2, 2, 'protocol2')
            s_id_3 = ServiceRegistry.register(
                'name3', 'Southbound', 'address3', 3, 3, 'protocol3')
            s_id_4 = ServiceRegistry.register(
                'name4', 'Southbound', 'address4', 4, 4, 'protocol4')

            ServiceRegistry.unregister(s_id_3)
            ServiceRegistry.mark_as_failed(s_id_4)

            resp = await client.get('/foglamp/service')
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert json_response == {
                'services': [
                    {
                        'type': 'Storage',
                        'service_port': 1,
                        'address': 'address1',
                        'protocol': 'protocol1',
                        'status': 'running',
                        'name': 'name1',
                        'management_port': 1
                    },
                    {
                        'type': 'Southbound',
                        'service_port': 2,
                        'address': 'address2',
                        'protocol': 'protocol2',
                        'status': 'running',
                        'name': 'name2',
                        'management_port': 2
                    },
                    {
                        'type': 'Southbound',
                        'service_port': 3,
                        'address': 'address3',
                        'protocol': 'protocol3',
                        'status': 'shutdown',
                        'name': 'name3',
                        'management_port': 3
                    },
                    {
                        'type': 'Southbound',
                        'service_port': 4,
                        'address': 'address4',
                        'protocol': 'protocol4',
                        'status': 'failed',
                        'name': 'name4',
                        'management_port': 4
                    }
                ]
            }
        assert 6 == log_patch_info.call_count

    @pytest.mark.parametrize("payload, code, message", [
        ('"blah"', 400, "Data payload must be a valid JSON"''),
        ('{}', 400, "Missing name property in payload."),
        ('{"name": "test"}', 400, "Missing type property in payload."),
        ('{"name": "a;b", "plugin": "dht11", "type": "south"}', 400, "Invalid name property in payload."),
        ('{"name": "test", "plugin": "dht@11", "type": "south"}', 400, "Invalid plugin property in payload."),
        ('{"name": "test", "plugin": "dht11", "type": "south", "enabled": "blah"}', 400,
         'Only "true", "false", true, false are allowed for value of enabled.'),
        ('{"name": "test", "plugin": "dht11", "type": "south", "enabled": "t"}', 400,
         'Only "true", "false", true, false are allowed for value of enabled.'),
        ('{"name": "test", "plugin": "dht11", "type": "south", "enabled": "True"}', 400,
         'Only "true", "false", true, false are allowed for value of enabled.'),
        ('{"name": "test", "plugin": "dht11", "type": "south", "enabled": "False"}', 400,
         'Only "true", "false", true, false are allowed for value of enabled.'),
        ('{"name": "test", "plugin": "dht11", "type": "south", "enabled": "1"}', 400,
         'Only "true", "false", true, false are allowed for value of enabled.'),
        ('{"name": "test", "plugin": "dht11", "type": "south", "enabled": "0"}', 400,
         'Only "true", "false", true, false are allowed for value of enabled.'),
        ('{"name": "test", "plugin": "dht11"}', 400, "Missing type property in payload."),
        ('{"name": "test", "plugin": "dht11", "type": "blah"}', 400, "Only south and notification type are supported."),
        ('{"name": "test", "plugin": "dht11", "type": "North"}', 406, "north type is not supported for the time being."),
        ('{"name": "test", "type": "south"}', 400, "Missing plugin property for type south in payload.")
    ])
    async def test_add_service_with_bad_params(self, client, code, payload, message):
        resp = await client.post('/foglamp/service', data=payload)
        assert code == resp.status
        assert message == resp.reason

    async def test_plugin_not_supported(self, client):
        data = {"name": "HTTP", "type": "south", "plugin": "http-north"}

        mock_plugin_info = {
            'name': "HTTP",
            'version': "1.1",
            'type': "north",
            'interface': "1.0.0",
            'mode': "async",
            'config': {
                'plugin': {
                    'description': "HTTP North Plugin",
                    'type': 'string',
                    'default': 'http-north'
                }
            }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)
        with patch('builtins.__import__', return_value=mock):
            with patch.object(_logger, 'exception') as ex_logger:
                resp = await client.post('/foglamp/service', data=json.dumps(data))
                assert 400 == resp.status
                assert 'Plugin of north type is not supported' == resp.reason
            assert 1 == ex_logger.call_count

    async def test_insert_scheduled_process_exception_add_service(self, client):
        data = {"name": "furnace4", "type": "south", "plugin": "dht11"}

        @asyncio.coroutine
        def q_result(*arg):
            return {'count': 0, 'rows': []}

        mock_plugin_info = {
            'name': "furnace4",
            'version': "1.1",
            'type': "south",
            'interface': "1.0",
            'mode': "async",
            'config': {
                'plugin': {
                    'description': "DHT11",
                    'type': 'string',
                    'default': 'dht11'
                }
            }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch('builtins.__import__', return_value=mock):
            with patch.object(_logger, 'exception') as ex_logger:
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(c_mgr, 'get_category_all_items',
                                      return_value=self.async_mock(None)) as patch_get_cat_info:
                        with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result) \
                                as query_table_patch:
                            with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=Exception()):
                                resp = await client.post('/foglamp/service', data=json.dumps(data))
                                assert 500 == resp.status
                                assert 'Failed to create service.' == resp.reason
                        args1, kwargs1 = query_table_patch.call_args
                        assert 'scheduled_processes' == args1[0]
                        p2 = json.loads(args1[1])
                        assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=', 'value': 'south_c'}} == p2
                    patch_get_cat_info.assert_called_once_with(category_name=data['name'])
            assert 1 == ex_logger.call_count

    async def test_dupe_category_name_add_service(self, client):
        mock_plugin_info = {
            'name': "furnace4",
            'version': "1.1",
            'type': "south",
            'interface': "1.0",
            'mode': "async",
            'config': {
                'plugin': {
                    'description': "DHT11",
                    'type': 'string',
                    'default': 'dht11'
                }
            }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)

        data = {"name": "furnace4", "type": "south", "plugin": "dht11"}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch('builtins.__import__', return_value=mock):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(mock_plugin_info)) as patch_get_cat_info:
                    resp = await client.post('/foglamp/service', data=json.dumps(data))
                    assert 400 == resp.status
                    assert "The '{}' category already exists".format(data['name']) == resp.reason
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_dupe_schedule_name_add_service(self, client):
        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=',
                                                               'value': 'furnace4'}} == json.loads(payload)
                return {'count': 1, 'rows': [{'schedule_name': 'schedule_name'}]}

        mock_plugin_info = {
            'name': "furnace4",
            'version': "1.1",
            'type': "south",
            'interface': "1.0",
            'mode': "async",
            'config': {
                'plugin': {
                    'description': "DHT11",
                    'type': 'string',
                    'default': 'dht11'
                }
            }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)

        data = {"name": "furnace4", "type": "south", "plugin": "dht11"}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch('builtins.__import__', return_value=mock):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as patch_get_cat_info:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                        resp = await client.post('/foglamp/service', data=json.dumps(data))
                        assert 400 == resp.status
                        assert 'A service with this name already exists.' == resp.reason
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    p1 = '{"name": "furnace4", "type": "south", "plugin": "dht11"}'
    p2 = '{"name": "furnace4", "type": "south", "plugin": "dht11", "enabled": false}'
    p3 = '{"name": "furnace4", "type": "south", "plugin": "dht11", "enabled": true}'
    p4 = '{"name": "furnace4", "type": "south", "plugin": "dht11", "enabled": "true"}'
    p5 = '{"name": "furnace4", "type": "south", "plugin": "dht11", "enabled": "false"}'

    @pytest.mark.parametrize("payload", [p1, p2, p3, p4, p5])
    async def test_add_service(self, client, payload):
        data = json.loads(payload)

        async def async_mock_get_schedule():
            schedule = StartUpSchedule()
            schedule.schedule_id = '2129cc95-c841-441a-ad39-6469a87dbc8b'
            return schedule

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            _payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=',
                                                      'value': 'south_c'}} == json.loads(_payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=',
                                                               'value': 'furnace4'}} == json.loads(_payload)
                return {'count': 0, 'rows': []}

        expected_insert_resp = {'rows_affected': 1, "response": "inserted"}
        mock_plugin_info = {
            'name': "furnace4",
            'version': "1.1",
            'type': "south",
            'interface': "1.0",
            'mode': "async",
            'config': {
                'plugin': {
                    'description': "DHT11 plugin",
                    'type': 'string',
                    'default': 'dht11'
                }
            }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)

        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch('builtins.__import__', return_value=mock):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as patch_get_cat_info:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=self.async_mock(expected_insert_resp)) \
                                as insert_table_patch:
                            with patch.object(c_mgr, 'create_category', return_value=self.async_mock(None)) as patch_create_cat:
                                with patch.object(c_mgr, 'create_child_category', return_value=self.async_mock(None)) \
                                        as patch_create_child_cat:
                                    with patch.object(server.Server.scheduler, 'save_schedule',
                                                      return_value=self.async_mock("")) as patch_save_schedule:
                                        with patch.object(server.Server.scheduler, 'get_schedule_by_name',
                                                          return_value=async_mock_get_schedule()) as patch_get_schedule:
                                            resp = await client.post('/foglamp/service', data=payload)
                                            server.Server.scheduler = None
                                            assert 200 == resp.status
                                            result = await resp.text()
                                            json_response = json.loads(result)
                                            assert {'id': '2129cc95-c841-441a-ad39-6469a87dbc8b',
                                                    'name': 'furnace4'} == json_response
                                        patch_get_schedule.assert_called_once_with(data['name'])
                                    patch_save_schedule.called_once_with()
                                patch_create_child_cat.assert_called_once_with('South', ['furnace4'])
                            assert 2 == patch_create_cat.call_count
                            patch_create_cat.assert_called_with('South', {}, 'South microservices', True)
                        args, kwargs = insert_table_patch.call_args
                        assert 'scheduled_processes' == args[0]
                        p = json.loads(args[1])
                        assert {'name': 'south_c', 'script': '["services/south_c"]'} == p
                patch_get_cat_info.assert_called_once_with(category_name='furnace4')

    p1 = '{"name": "NotificationServer", "type": "notification"}'
    p2 = '{"name": "NotificationServer", "type": "notification", "enabled": false}'
    p3 = '{"name": "NotificationServer", "type": "notification", "enabled": true}'

    @pytest.mark.parametrize("payload", [p1, p2, p3])
    async def test_add_notification_service(self, client, payload):
        data = json.loads(payload)
        sch_id = '45876056-e04c-4cde-8a82-1d8dbbbe6d72'

        async def async_mock_get_schedule():
            schedule = StartUpSchedule()
            schedule.schedule_id = sch_id
            return schedule

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            _payload = json.loads(arg[1])
            if table == 'schedules':
                if _payload['return'][0] == 'process_name':
                    assert {"return": ["process_name"]} == _payload
                    return {'rows': [{'process_name': 'purge'}, {'process_name': 'stats collector'}], 'count': 2}
                else:
                    assert {"return": ["schedule_name"], "where": {"column": "schedule_name", "condition": "=",
                                                                   "value": data['name']}} == _payload

                    return {'count': 0, 'rows': []}
            if table == 'scheduled_processes':
                assert {"return": ["name"], "where": {"column": "name", "condition": "=",
                                                      "value": "notification_c"}} == _payload
                return {'count': 0, 'rows': []}

        expected_insert_resp = {'rows_affected': 1, "response": "inserted"}

        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as patch_get_cat_info:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                    with patch.object(storage_client_mock, 'insert_into_tbl', return_value=self.async_mock(expected_insert_resp)) as insert_table_patch:
                        with patch.object(server.Server.scheduler, 'save_schedule', return_value=self.async_mock("")) as patch_save_schedule:
                            with patch.object(server.Server.scheduler, 'get_schedule_by_name', return_value=async_mock_get_schedule()) as patch_get_schedule:
                                resp = await client.post('/foglamp/service', data=payload)
                                server.Server.scheduler = None
                                assert 200 == resp.status
                                result = await resp.text()
                                json_response = json.loads(result)
                                assert {'id': sch_id, 'name': data['name']} == json_response
                            patch_get_schedule.assert_called_once_with(data['name'])
                        patch_save_schedule.called_once_with()
                    args, kwargs = insert_table_patch.call_args
                    assert 'scheduled_processes' == args[0]
                    p = json.loads(args[1])
                    assert {'name': 'notification_c', 'script': '["services/notification_c"]'} == p
            patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_dupe_notification_service_schedule(self, client):
        payload = '{"name": "NotificationServer", "type": "notification"}'
        data = json.loads(payload)

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            _payload = json.loads(arg[1])
            if table == 'schedules':
                if _payload['return'][0] == 'process_name':
                    assert {"return": ["process_name"]} == _payload
                    return {'rows': [{'process_name': 'stats collector'}, {'process_name': 'notification_c'}], 'count': 2}

                else:
                    assert {"return": ["schedule_name"], "where": {"column": "schedule_name", "condition": "=",
                                                                   "value": data['name']}} == _payload

                    return {'count': 0, 'rows': []}
            if table == 'scheduled_processes':
                assert {"return": ["name"], "where": {"column": "name", "condition": "=",
                                                      "value": "notification_c"}} == _payload
                return {'count': 0, 'rows': []}

        expected_insert_resp = {'rows_affected': 1, "response": "inserted"}

        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as patch_get_cat_info:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                    with patch.object(storage_client_mock, 'insert_into_tbl', return_value=self.async_mock(expected_insert_resp)) as insert_table_patch:
                        resp = await client.post('/foglamp/service', data=payload)
                        server.Server.scheduler = None
                        assert 400 == resp.status
                        assert 'A Notification service schedule already exists.' == resp.reason
                    args, kwargs = insert_table_patch.call_args
                    assert 'scheduled_processes' == args[0]
                    p = json.loads(args[1])
                    assert {'name': 'notification_c', 'script': '["services/notification_c"]'} == p
            patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_add_service_with_config(self, client):
        payload = '{"name": "Sine", "type": "south", "plugin": "sinusoid", "enabled": "false",' \
                  ' "config": {"dataPointsPerSec": {"value": "10"}}}'
        data = json.loads(payload)

        async def async_mock_get_schedule():
            schedule = StartUpSchedule()
            schedule.schedule_id = '2129cc95-c841-441a-ad39-6469a87dbc8b'
            return schedule

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            _payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'],
                        'where': {'column': 'name', 'condition': '=', 'value': 'south_c'}} == json.loads(_payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'],
                        'where': {'column': 'schedule_name', 'condition': '=',
                                  'value': data['name']}} == json.loads(_payload)
                return {'count': 0, 'rows': []}

        expected_insert_resp = {'rows_affected': 1, "response": "inserted"}
        mock_plugin_info = {
            'name': data['name'],
            'version': "1.1",
            'type': "south",
            'interface': "1.0",
            'mode': "async",
            'config': {
                'plugin': {
                    'description': "Sinusoid Plugin",
                    'type': 'string',
                    'default': 'sinusoid'
                },
                'dataPointsPerSec': {
                    'description': 'Data points per second',
                    'type': 'integer',
                    'default': '1',
                    'order': '2'
                }
            }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch('builtins.__import__', return_value=mock):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as patch_get_cat_info:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                        with patch.object(storage_client_mock, 'insert_into_tbl',
                                          return_value=self.async_mock(expected_insert_resp)) as insert_table_patch:
                            with patch.object(c_mgr, 'create_category', return_value=self.async_mock(None)) as patch_create_cat:
                                with patch.object(c_mgr, 'create_child_category',
                                                  return_value=self.async_mock(None)) as patch_create_child_cat:
                                    with patch.object(c_mgr, 'set_category_item_value_entry',
                                                      return_value=self.async_mock(None)) as patch_set_entry:
                                        with patch.object(server.Server.scheduler, 'save_schedule',
                                                          return_value=self.async_mock("")) as patch_save_schedule:
                                            with patch.object(server.Server.scheduler, 'get_schedule_by_name',
                                                              return_value=async_mock_get_schedule()) as patch_get_schedule:
                                                    resp = await client.post('/foglamp/service', data=payload)
                                                    server.Server.scheduler = None
                                                    assert 200 == resp.status
                                                    result = await resp.text()
                                                    json_response = json.loads(result)
                                                    assert {'id': '2129cc95-c841-441a-ad39-6469a87dbc8b',
                                                            'name': data['name']} == json_response
                                            patch_get_schedule.assert_called_once_with(data['name'])
                                        patch_save_schedule.called_once_with()
                                    patch_set_entry.assert_called_once_with(data['name'], 'dataPointsPerSec', '10')
                                patch_create_child_cat.assert_called_once_with('South', ['Sine'])
                            assert 2 == patch_create_cat.call_count
                            patch_create_cat.assert_called_with('South', {}, 'South microservices', True)
                        args, kwargs = insert_table_patch.call_args
                        assert 'scheduled_processes' == args[0]
                        p = json.loads(args[1])
                        assert {'name': 'south_c', 'script': '["services/south_c"]'} == p
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_delete_service(self, mocker, client):
        sch_id = '0178f7b6-d55c-4427-9106-245513e46416'
        reg_id = 'd607c5be-792f-4993-96b7-b513674e7d3b'
        name = "Test"
        sch_name = "Test Service"
        mock_registry = [ServiceRecord(reg_id, name, "Southbound", "http", "localhost", "8118", "8118")]

        async def mock_result():
            return {
                        "count": 1,
                        "rows": [
                            {
                                "id": sch_id,
                                "process_name": name,
                                "schedule_name": sch_name,
                                "schedule_type": "1",
                                "schedule_interval": "0",
                                "schedule_time": "0",
                                "schedule_day": "0",
                                "exclusive": "t",
                                "enabled": "t"
                            },
                        ]
            }
        mocker.patch.object(connect, 'get_storage_async')
        get_schedule = mocker.patch.object(service, "get_schedule", return_value=mock_result())
        scheduler = mocker.patch.object(server.Server, "scheduler", MagicMock())
        delete_schedule = mocker.patch.object(scheduler, "delete_schedule", return_value=asyncio.sleep(.1))
        disable_schedule = mocker.patch.object(scheduler, "disable_schedule", return_value=asyncio.sleep(.1))
        delete_configuration = mocker.patch.object(ConfigurationManager, "delete_category_and_children_recursively", return_value=asyncio.sleep(.1))
        get_registry = mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        remove_registry = mocker.patch.object(ServiceRegistry, 'remove_from_registry')

        mock_registry[0]._status = ServiceRecord.Status.Shutdown

        resp = await client.delete("/foglamp/service/{}".format(sch_name))
        assert 200 == resp.status
        result = await resp.json()
        assert "Service {} deleted successfully.".format(sch_name) == result['result']

        assert 1 == get_schedule.call_count
        args, kwargs = get_schedule.call_args_list[0]
        assert sch_name in args

        assert 1 == delete_schedule.call_count
        delete_schedule_calls = [call(UUID('0178f7b6-d55c-4427-9106-245513e46416'))]
        delete_schedule.assert_has_calls(delete_schedule_calls, any_order=True)

        assert 1 == disable_schedule.call_count
        disable_schedule_calls = [call(UUID('0178f7b6-d55c-4427-9106-245513e46416'))]
        disable_schedule.assert_has_calls(disable_schedule_calls, any_order=True)

        assert 1 == delete_configuration.call_count
        args, kwargs = delete_configuration.call_args_list[0]
        assert sch_name in args

        assert 1 == get_registry.call_count
        get_registry_calls = [call(name=sch_name)]
        get_registry.assert_has_calls(get_registry_calls, any_order=True)

        assert 1 == remove_registry.call_count
        remove_registry_calls = [call('d607c5be-792f-4993-96b7-b513674e7d3b')]
        remove_registry.assert_has_calls(remove_registry_calls, any_order=True)

    async def test_delete_service_exception(self, mocker, client):
        resp = await client.delete("/foglamp/service")
        assert 405 == resp.status
        assert 'Method Not Allowed' == resp.reason

        reg_id = 'd607c5be-792f-4993-96b7-b513674e7d3b'
        name = 'Test'
        mock_registry = [ServiceRecord(reg_id, name, "Southbound", "http", "localhost", "8118", "8118")]

        mocker.patch.object(service, "get_schedule", side_effect=Exception)
        resp = await client.delete("/foglamp/service/{}".format(name))
        assert 500 == resp.status
        assert resp.reason is None

        async def mock_bad_result():
            return {"count": 0, "rows": []}

        mocker.patch.object(connect, 'get_storage_async')
        mock_registry[0]._status = ServiceRecord.Status.Shutdown
        mocker.patch.object(service, "get_schedule", return_value=mock_bad_result())

        resp = await client.delete("/foglamp/service/{}".format(name))
        assert 404 == resp.status
        assert '{} service does not exist.'.format(name) == resp.reason

# TODO:  add negative tests and C type plugin add service tests
