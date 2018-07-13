# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import builtins
import asyncio
import json
from aiohttp import web
import pytest
from unittest.mock import MagicMock, patch
from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry
from foglamp.services.core import server
from foglamp.services.core.scheduler.scheduler import Scheduler
from foglamp.services.core.scheduler.entities import Schedule, TimedSchedule, TimedSchedule, \
    IntervalSchedule, ManualSchedule
from foglamp.common.configuration_manager import ConfigurationManager

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "task")
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

    @pytest.mark.parametrize("payload, code, message", [
        ("blah", 500, "Data payload must be a dictionary"),
        ({}, 400, 'Missing name property in payload.'),
        ({"name": "test"}, 400, "Missing plugin property in payload."),
        ({"name": "test", "plugin": "omf"}, 400, 'Missing type property in payload.'),
        ({"name": "test", "plugin": "omf", "type": "north", "schedule_type": 3}, 400, 'schedule_repeat None is required for INTERVAL schedule_type.'),
        ({"name": "test", "plugin": "omf", "type": "north", "schedule_type": 1}, 400, 'schedule_type cannot be STARTUP: 1')
    ])
    async def test_add_task_with_bad_params(self, client, code, payload, message):
        resp = await client.post('/foglamp/scheduled/task', data=json.dumps(payload))
        assert code == resp.status
        assert message == resp.reason

    async def test_dupe_process_name_add_task(self, client):
        data = {"name": "north bound", "type": "north", "schedule_type": 3, "plugin": "omf", "schedule_repeat": 30}
        async def async_mock():
            expected = {'count': 1, 'rows': [{'name': 'north bound'}]}
            return expected

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch('builtins.__import__', side_effect=MagicMock()):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=async_mock()) as query_table_patch:
                    resp = await client.post('/foglamp/scheduled/task', data=json.dumps(data))
                    assert 400 == resp.status
                    assert 'A task with that name already exists' == resp.reason
                args, kwargs = query_table_patch.call_args
                assert 'scheduled_processes' == args[0]
                p = json.loads(args[1])
                assert {"return": ["name"], "where": {"column": "name", "condition": "=", "value": "north bound"}} == p

    async def test_insert_scheduled_process_exception_add_task(self, client):
        data = {"name": "north bound", "type": "north", "schedule_type": 3, "plugin": "omf", "schedule_repeat": 30}

        @asyncio.coroutine
        def async_mock():
            expected = {'count': 0, 'rows': []}
            return expected

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch('builtins.__import__', side_effect=MagicMock()):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=async_mock()) as query_table_patch:
                    with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=Exception()) as insert_table_patch:
                        resp = await client.post('/foglamp/scheduled/task', data=json.dumps(data))
                        assert 500 == resp.status
                        assert 'Internal Server Error' == resp.reason
                    # args, kwargs = insert_table_patch.call_args
                    # assert 'scheduled_processes' == args[0]
                    # p1 = json.loads(args[1])
                    # assert {'name': 'north bound', 'script': '["services/north"]'} == p1
                args1, kwargs1 = query_table_patch.call_args
                assert 'schedules' == args1[0]
                p2 = json.loads(args1[1])
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=', 'value': 'north bound'}} == p2

    async def test_dupe_schedule_name_add_task(self, client):
        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=', 'value': 'north bound'}} == json.loads(payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=', 'value': 'north bound'}} == json.loads(payload)
                return {'count': 1, 'rows': [{'schedule_name': 'schedule_name'}]}

        @asyncio.coroutine
        def async_mock():
            expected = {'rows_affected': 1, "response": "inserted"}
            return expected

        data = {"name": "north bound", "plugin": "omf", "type": "north", "schedule_type": 3, "schedule_repeat": 30}
        description = '{} service configuration'.format(data['name'])
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        val = {'plugin': {'default': data['plugin'], 'description': 'Python module name of the plugin to load', 'type': 'string'}}
        with patch('builtins.__import__', side_effect=MagicMock()):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                    with patch.object(storage_client_mock, 'insert_into_tbl', return_value=async_mock()) as insert_table_patch:
                        with patch.object(c_mgr, 'create_category', return_value=None) as patch_create_cat:
                            resp = await client.post('/foglamp/scheduled/task', data=json.dumps(data))
                            assert 500 == resp.status
                            assert 'Internal Server Error' == resp.reason
                        assert 0 == patch_create_cat.call_count

    async def test_add_task(self, client):
        async def async_mock(return_value):
            return return_value

        async def async_mock_get_schedule():
            schedule = TimedSchedule()
            schedule.schedule_id = '2129cc95-c841-441a-ad39-6469a87dbc8b'
            return schedule

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=', 'value': 'north bound'}} == json.loads(payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=', 'value': 'north bound'}} == json.loads(payload)
                return {'count': 0, 'rows': []}

        async def async_mock_insert():
            expected = {'rows_affected': 1, "response": "inserted"}
            return expected

        mock_plugin_info = {
                'name': "north bound",
                'version': "1.1",
                'type': "north",
                'interface': "1.0",
                'config': {
                            'plugin': {
                                'description': "North OMF plugin",
                                'type': 'string',
                                'default': 'omf'
                            }
            }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)

        server.Server.scheduler = Scheduler(None, None)
        data = {
                "name": "north bound",
                "plugin": "omf",
                "type": "north",
                "schedule_type": 3,
                "schedule_day": 0,
                "schedule_time": 0,
                "schedule_repeat": 30,
                "schedule_enabled": True,
                "cmd_params": {
                    "stream_id": "1",
                    "debug_level": "1"
                }
        }
        description = "North OMF plugin"

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        val = {'plugin': {'description': 'North OMF plugin', 'type': 'string', 'default': 'omf'}}

        with patch('builtins.__import__', return_value=mock):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                    with patch.object(storage_client_mock, 'insert_into_tbl', return_value=async_mock_insert()) as insert_table_patch:
                        with patch.object(c_mgr, 'create_category', return_value=async_mock(None)) as patch_create_cat:
                            with patch.object(server.Server.scheduler, 'save_schedule', return_value=async_mock("")) as patch_save_schedule:
                                with patch.object(server.Server.scheduler, 'get_schedule_by_name', return_value=async_mock_get_schedule()) as patch_get_schedule:
                                    resp = await client.post('/foglamp/scheduled/task', data=json.dumps(data))
                                    server.Server.scheduler = None
                                    assert 200 == resp.status
                                    result = await resp.text()
                                    json_response = json.loads(result)
                                    assert {'id': '2129cc95-c841-441a-ad39-6469a87dbc8b', 'name': 'north bound'} == json_response
                                patch_get_schedule.assert_called_once_with(data['name'])
                            patch_save_schedule.called_once_with()
                        patch_create_cat.assert_called_once_with(category_name=data['name'], category_description=description, category_value=val, keep_original_items=True)

                    args, kwargs = insert_table_patch.call_args
                    assert 'scheduled_processes' == args[0]
                    p = json.loads(args[1])
                    assert p['name'] == 'north bound'
                    assert p['script'] in ['["tasks/north", "--stream_id=1", "--debug_level=1"]','["tasks/north", "--debug_level=1", "--stream_id=1"]']

    # TODO: Add test for negative scenarios
