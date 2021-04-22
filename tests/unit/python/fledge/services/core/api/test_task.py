# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


import asyncio
import json
from uuid import UUID
from aiohttp import web
import pytest
from unittest.mock import MagicMock, patch, call
from fledge.services.core import routes
from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core import server
from fledge.services.core.scheduler.scheduler import Scheduler
from fledge.services.core.scheduler.entities import TimedSchedule
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core.api import task
from fledge.services.core.api.plugins import common
from fledge.services.core.api.service import _logger

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "task")
class TestTask:
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

    @pytest.mark.parametrize("payload, code, message", [
        ("blah", 400, "Data payload must be a valid JSON"),
        ({}, 400, 'Missing name property in payload.'),
        ({"name": "test"}, 400, "Missing plugin property in payload."),
        ({"name": "test", "plugin": "omf"}, 400, 'Missing type property in payload.'),
        ({"name": "test", "plugin": "omf", "type": "north", "schedule_type": 3}, 400, 'schedule_repeat None is required for INTERVAL schedule_type.'),
        ({"name": "test", "plugin": "omf", "type": "north", "schedule_type": 1}, 400, 'schedule_type cannot be STARTUP: 1')
    ])
    async def test_add_task_with_bad_params(self, client, code, payload, message):
        resp = await client.post('/fledge/scheduled/task', data=json.dumps(payload))
        assert code == resp.status
        assert message == resp.reason

    async def test_insert_scheduled_process_exception_add_task(self, client):
        data = {"name": "north bound", "type": "north", "schedule_type": 3, "plugin": "omf", "schedule_repeat": 30}

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'],
                        'where': {'column': 'name', 'condition': '=', 'value': 'north'}} == json.loads(payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'],
                        'where': {'column': 'schedule_name', 'condition': '=',
                                  'value': 'north bound'}} == json.loads(payload)
                return {'count': 0, 'rows': []}
            if table == 'tasks':
                return {'count': 0, 'rows': []}

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

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(_logger, 'exception') as ex_logger:
                    with patch.object(c_mgr, 'get_category_all_items',
                                      return_value=self.async_mock(None)) as patch_get_cat_info:
                        with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                            with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=Exception()):
                                resp = await client.post('/fledge/scheduled/task', data=json.dumps(data))
                                assert 500 == resp.status
                                assert 'Failed to create north instance.' == resp.reason
                        assert 1 == ex_logger.call_count
                    patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_dupe_category_name_add_task(self, client):

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]

            if table == 'tasks':
                return {'count': 0, 'rows': []}

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
        data = {"name": "north bound", "plugin": "omf", "type": "north", "schedule_type": 3, "schedule_repeat": 30}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(mock_plugin_info)) as patch_get_cat_info:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                        resp = await client.post('/fledge/scheduled/task', data=json.dumps(data))
                        assert 400 == resp.status
                        assert "The '{}' category already exists".format(data['name']) == resp.reason
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_dupe_schedule_name_add_task(self, client):
        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=',
                                                               'value': 'north bound'}} == json.loads(payload)
                return {'count': 1, 'rows': [{'schedule_name': 'schedule_name'}]}

            if table == 'tasks':
                return {'count': 0, 'rows': []}

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
        data = {"name": "north bound", "plugin": "omf", "type": "north", "schedule_type": 3, "schedule_repeat": 30}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as patch_get_cat_info:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                        resp = await client.post('/fledge/scheduled/task', data=json.dumps(data))
                        assert 400 == resp.status
                        assert 'A north instance with this name already exists' == resp.reason
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_add_task(self, client):
        async def async_mock_get_schedule():
            schedule = TimedSchedule()
            schedule.schedule_id = '2129cc95-c841-441a-ad39-6469a87dbc8b'
            return schedule

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=',
                                                      'value': 'north'}} == json.loads(payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=',
                                                               'value': 'north bound'}} == json.loads(payload)
                return {'count': 0, 'rows': []}

            if table == 'tasks':
                return {'count': 0, 'rows': []}

        expected_insert_resp = {'rows_affected': 1, "response": "inserted"}
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
        server.Server.scheduler = Scheduler(None, None)
        data = {
            "name": "north bound",
            "plugin": "omf",
            "type": "north",
            "schedule_type": 3,
            "schedule_day": 0,
            "schedule_time": 0,
            "schedule_repeat": 30,
            "schedule_enabled": True
        }

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
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
                                            resp = await client.post('/fledge/scheduled/task', data=json.dumps(data))
                                            server.Server.scheduler = None
                                            assert 200 == resp.status
                                            result = await resp.text()
                                            json_response = json.loads(result)
                                            assert {'id': '2129cc95-c841-441a-ad39-6469a87dbc8b',
                                                    'name': 'north bound'} == json_response
                                        patch_get_schedule.assert_called_once_with(data['name'])
                                    patch_save_schedule.called_once_with()
                                patch_create_child_cat.assert_called_once_with('North', ['north bound'])
                            calls = [call(category_description='North OMF plugin', category_name='north bound',
                                          category_value={'plugin': {'description': 'North OMF plugin', 'default': 'omf',
                                                                     'type': 'string'}}, keep_original_items=True),
                                     call('North', {}, 'North tasks', True)]
                            patch_create_cat.assert_has_calls(calls)
                        args, kwargs = insert_table_patch.call_args
                        assert 'scheduled_processes' == args[0]
                        p = json.loads(args[1])
                        assert p['name'] == 'north'
                        assert p['script'] == '["tasks/north"]'
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    @pytest.mark.parametrize(
        "expected_count,"
        "expected_http_code,"
        "expected_message",
        [
            ( 1, 400, '400: Unable to reuse name north bound, already used by a previous task.'),
            (10, 400, '400: Unable to reuse name north bound, already used by a previous task.')
        ]
    )
    async def test_add_task_twice(self,
                                  client,
                                  expected_count,
                                  expected_http_code,
                                  expected_message):

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]

            if table == 'tasks':
                return {'count': expected_count, 'rows': []}

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
        data = {
            "name": "north bound",
            "plugin": "omf",
            "type": "north",
            "schedule_type": 3,
            "schedule_day": 0,
            "schedule_time": 0,
            "schedule_repeat": 30,
            "schedule_enabled": True
        }

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(_logger, 'exception') as ex_logger:
            with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                        with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                            resp = await client.post('/fledge/scheduled/task', data=json.dumps(data))
                            result = await resp.text()
                            assert resp.status == expected_http_code
                            assert result == expected_message
        assert 1 == ex_logger.call_count

    async def test_add_task_with_config(self, client):
        async def async_mock_get_schedule():
            schedule = TimedSchedule()
            schedule.schedule_id = '2129cc95-c841-441a-ad39-6469a87dbc8b'
            return schedule

        @asyncio.coroutine
        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=',
                                                      'value': 'north'}} == json.loads(payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=',
                                                               'value': 'north bound'}} == json.loads(payload)
                return {'count': 0, 'rows': []}

            if table == 'tasks':
                return {'count': 0, 'rows': []}

        expected_insert_resp = {'rows_affected': 1, "response": "inserted"}
        mock_plugin_info = {
            'name': "PI server",
            'version': "1.1",
            'type': "north",
            'interface': "1.0",
            'config': {
                'plugin': {
                    'description': "North PI plugin",
                    'type': 'string',
                    'default': 'omf'
                },
                'producerToken': {
                    'description': 'Producer token for this Fledge stream',
                    'type': 'string',
                    'default': 'pi_server_north_0001',
                    'order': '2'
                }
            }
        }
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
            "config": {
                "producerToken": {"value": "uid=180905062754237&sig=kx5l+"}}
        }

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as patch_get_cat_info:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=self.async_mock(expected_insert_resp)) \
                                as insert_table_patch:
                            with patch.object(c_mgr, 'create_category', return_value=self.async_mock(None)) as patch_create_cat:
                                with patch.object(c_mgr, 'create_child_category', return_value=self.async_mock(None)) \
                                        as patch_create_child_cat:
                                    with patch.object(c_mgr, 'set_category_item_value_entry',
                                                      return_value=self.async_mock(None)) as patch_set_entry:
                                        with patch.object(server.Server.scheduler, 'save_schedule',
                                                          return_value=self.async_mock("")) as patch_save_schedule:
                                            with patch.object(server.Server.scheduler, 'get_schedule_by_name',
                                                              return_value=async_mock_get_schedule()) as patch_get_schedule:
                                                resp = await client.post('/fledge/scheduled/task', data=json.dumps(data))
                                                server.Server.scheduler = None
                                                assert 200 == resp.status
                                                result = await resp.text()
                                                json_response = json.loads(result)
                                                assert {'id': '2129cc95-c841-441a-ad39-6469a87dbc8b',
                                                        'name': 'north bound'} == json_response
                                            patch_get_schedule.assert_called_once_with(data['name'])
                                        patch_save_schedule.called_once_with()
                                    patch_set_entry.assert_called_once_with(data['name'], 'producerToken',
                                                                            'uid=180905062754237&sig=kx5l+')
                                patch_create_child_cat.assert_called_once_with('North', ['north bound'])
                            assert 2 == patch_create_cat.call_count
                            patch_create_cat.assert_called_with('North', {}, 'North tasks', True)
                        args, kwargs = insert_table_patch.call_args
                        assert 'scheduled_processes' == args[0]
                        p = json.loads(args[1])
                        assert p['name'] == 'north'
                        assert p['script'] == '["tasks/north"]'
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_delete_task(self, mocker, client):
        sch_id = '0178f7b6-d55c-4427-9106-245513e46416'
        sch_name = "Test Task"

        async def mock_result():
            return {
                "count": 1,
                "rows": [
                    {
                        "id": sch_id,
                        "process_name": "Test",
                        "schedule_name": sch_name,
                        "schedule_type": "3",
                        "schedule_interval": "30",
                        "schedule_time": "0",
                        "schedule_day": "0",
                        "exclusive": "t",
                        "enabled": "t"
                    },
                ]
            }

        mocker.patch.object(connect, 'get_storage_async')
        get_schedule = mocker.patch.object(task, "get_schedule", return_value=mock_result())
        scheduler = mocker.patch.object(server.Server, "scheduler", MagicMock())
        delete_schedule = mocker.patch.object(scheduler, "delete_schedule", return_value=asyncio.sleep(.1))
        disable_schedule = mocker.patch.object(scheduler, "disable_schedule", return_value=asyncio.sleep(.1))
        delete_task_entry_with_schedule_id = mocker.patch.object(task, "delete_task_entry_with_schedule_id",
                                                                 return_value=asyncio.sleep(.1))
        delete_configuration = mocker.patch.object(ConfigurationManager, "delete_category_and_children_recursively",
                                                   return_value=asyncio.sleep(.1))
        delete_statistics_key = mocker.patch.object(task, "delete_statistics_key", return_value=asyncio.sleep(.1))

        delete_streams = mocker.patch.object(task, "delete_streams", return_value=asyncio.sleep(.1))
        delete_plugin_data = mocker.patch.object(task, "delete_plugin_data", return_value=asyncio.sleep(.1))

        resp = await client.delete("/fledge/scheduled/task/{}".format(sch_name))
        assert 200 == resp.status
        result = await resp.json()
        assert 'North instance {} deleted successfully.'.format(sch_name) == result['result']

        assert 1 == get_schedule.call_count
        args, kwargs = get_schedule.call_args_list[0]
        assert sch_name in args

        assert 1 == delete_schedule.call_count
        delete_schedule_calls = [call(UUID(sch_id))]
        delete_schedule.assert_has_calls(delete_schedule_calls, any_order=True)

        assert 1 == disable_schedule.call_count
        disable_schedule_calls = [call(UUID(sch_id))]
        disable_schedule.assert_has_calls(disable_schedule_calls, any_order=True)

        assert 1 == delete_task_entry_with_schedule_id.call_count
        args, kwargs = delete_task_entry_with_schedule_id.call_args_list[0]
        assert UUID(sch_id) in args

        assert 1 == delete_configuration.call_count
        args, kwargs = delete_configuration.call_args_list[0]
        assert sch_name in args

        assert 1 == delete_statistics_key.call_count
        args, kwargs = delete_statistics_key.call_args_list[0]
        assert sch_name in args

        assert 1 == delete_streams.call_count
        args, kwargs = delete_streams.call_args_list[0]
        assert sch_name in args

        assert 1 == delete_plugin_data.call_count
        args, kwargs = delete_plugin_data.call_args_list[0]
        assert sch_name in args

    async def test_delete_task_exception(self, mocker, client):
        resp = await client.delete("/fledge/scheduled/task")
        assert 405 == resp.status
        assert 'Method Not Allowed' == resp.reason

        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(task, "get_schedule", side_effect=Exception)
        resp = await client.delete("/fledge/scheduled/task/Test")
        assert 500 == resp.status
        assert resp.reason is ''

        async def mock_bad_result():
            return {"count": 0, "rows": []}

        mocker.patch.object(task, "get_schedule", return_value=mock_bad_result())
        resp = await client.delete("/fledge/scheduled/task/Test")
        assert 404 == resp.status
        assert 'Test north instance does not exist.' == resp.reason

# TODO: Add test for negative scenarios
