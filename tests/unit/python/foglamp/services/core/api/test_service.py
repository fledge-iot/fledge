# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core import server
from foglamp.services.core.scheduler.scheduler import Scheduler
from foglamp.services.core.scheduler.entities import StartUpSchedule
from foglamp.common.configuration_manager import ConfigurationManager

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

    async def test_get_health(self, client):
        # empty service registry
        resp = await client.get('/foglamp/service')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert {'services': []} == json_response
        with patch.object(ServiceRegistry._logger, 'info') as log_patch_info:
            # populated service registry
            ServiceRegistry.register('sname1', 'Storage', 'saddress1', 1, 1,  'protocol1')
            ServiceRegistry.register('sname2', 'Southbound', 'saddress2', 2, 2,  'protocol2')
            ServiceRegistry.register('sname3', 'Southbound', 'saddress3', 3, 3,  'protocol3')
            resp = await client.get('/foglamp/service')
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'services': [{'type': 'Storage', 'service_port': 1, 'address': 'saddress1', 'protocol': 'protocol1', 'status': 'running', 'name': 'sname1', 'management_port': 1},
                                 {'type': 'Southbound', 'service_port': 2, 'address': 'saddress2', 'protocol': 'protocol2', 'status': 'running', 'name': 'sname2', 'management_port': 2},
                                 {'type': 'Southbound', 'service_port': 3, 'address': 'saddress3', 'protocol': 'protocol3', 'status': 'running', 'name': 'sname3', 'management_port': 3}]} == json_response
        assert 3 == log_patch_info.call_count

    @pytest.mark.parametrize("payload, code, message", [
        ("blah", 404, "Data payload must be a dictionary"),
        ({}, 400, "Missing name property in payload."),
        ({"name": "test"}, 400, "Missing plugin property in payload."),
        ({"name": "test", "plugin": "dht11"}, 400, "Missing type property in payload."),
        ({"name": "test", "plugin": "dht11", "type": "blah"}, 400, "Only north and south types are supported.")
    ])
    async def test_add_service_with_bad_params(self, client, code, payload, message):
        resp = await client.post('/foglamp/service', data=json.dumps(payload))
        assert code == resp.status
        assert message == resp.reason

    async def test_dupe_process_name_add_service(self, client):
        data = {"name": "furnace4", "type": "south", "plugin": "dht11"}
        expected = {'count': 1, 'rows': [{'name': 'furnace4'}]}

        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=expected) as query_table_patch:
                resp = await client.post('/foglamp/service', data=json.dumps(data))
                assert 400 == resp.status
                assert 'A service with that name already exists' == resp.reason
            args, kwargs = query_table_patch.call_args
            assert 'scheduled_processes' == args[0]
            p = json.loads(args[1])
            assert {"return": ["name"], "where": {"column": "name", "condition": "=", "value": "furnace4"}} == p

    async def test_insert_scheduled_process_exception_add_service(self, client):
        data = {"name": "furnace4", "type": "north", "plugin": "dht11"}
        expected = {'count': 0, 'rows': []}
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=expected) as query_table_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=Exception()) as insert_table_patch:
                    resp = await client.post('/foglamp/service', data=json.dumps(data))
                    assert 500 == resp.status
                    assert 'Failed to created scheduled process. ' == resp.reason
                args, kwargs = insert_table_patch.call_args
                assert 'scheduled_processes' == args[0]
                p1 = json.loads(args[1])
                assert {'name': 'furnace4', 'script': '["services/north"]'} == p1
            args1, kwargs1 = query_table_patch.call_args
            assert 'scheduled_processes' == args1[0]
            p2 = json.loads(args1[1])
            assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=', 'value': 'furnace4'}} == p2

    async def test_dupe_schedule_name_add_service(self, client):
        async def async_mock():
            return None

        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=', 'value': 'furnace4'}} == json.loads(payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=', 'value': 'furnace4'}} == json.loads(payload)
                return {'count': 1, 'rows': [{'schedule_name': 'schedule_name'}]}

        data = {"name": "furnace4", "type": "north", "plugin": "dht11"}
        description = '{} service configuration'.format(data['name'])
        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        val = {'plugin': {'default': data['plugin'], 'description': 'Python module name of the plugin to load', 'type': 'string'}}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value={'rows_affected': 1, "response": "inserted"}) as insert_table_patch:
                    with patch.object(c_mgr, 'create_category', return_value=async_mock()) as patch_create_cat:
                        resp = await client.post('/foglamp/service', data=json.dumps(data))
                        assert 400 == resp.status
                        assert 'A schedule with that name already exists' == resp.reason
                    patch_create_cat.assert_called_once_with(category_name=data['name'], category_description=description, category_value=val, keep_original_items=False)
                args, kwargs = insert_table_patch.call_args
                assert 'scheduled_processes' == args[0]
                p = json.loads(args[1])
                assert {'name': 'furnace4', 'script': '["services/north"]'} == p

    async def test_add_service(self, client):
        async def async_mock(return_value):
            return return_value

        async def async_mock_get_schedule():
            schedule = StartUpSchedule()
            schedule.schedule_id = '2129cc95-c841-441a-ad39-6469a87dbc8b'
            return schedule

        def q_result(*arg):
            table = arg[0]
            payload = arg[1]

            if table == 'scheduled_processes':
                assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=', 'value': 'furnace4'}} == json.loads(payload)
                return {'count': 0, 'rows': []}
            if table == 'schedules':
                assert {'return': ['schedule_name'], 'where': {'column': 'schedule_name', 'condition': '=', 'value': 'furnace4'}} == json.loads(payload)
                return {'count': 0, 'rows': []}

        server.Server.scheduler = Scheduler(None, None)
        data = {"name": "furnace4", "type": "south", "plugin": "dht11"}
        description = '{} service configuration'.format(data['name'])
        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        val = {'plugin': {'default': data['plugin'], 'description': 'Python module name of the plugin to load', 'type': 'string'}}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value={'rows_affected': 1, "response": "inserted"}) as insert_table_patch:
                    with patch.object(c_mgr, 'create_category', return_value=async_mock(None)) as patch_create_cat:
                        with patch.object(server.Server.scheduler, 'save_schedule', return_value=async_mock("")) as patch_save_schedule:
                            with patch.object(server.Server.scheduler, 'get_schedule_by_name', return_value=async_mock_get_schedule()) as patch_get_schedule:
                                resp = await client.post('/foglamp/service', data=json.dumps(data))
                                server.Server.scheduler = None
                                assert 200 == resp.status
                                result = await resp.text()
                                json_response = json.loads(result)
                                assert {'id': '2129cc95-c841-441a-ad39-6469a87dbc8b', 'name': 'furnace4'} == json_response
                            patch_get_schedule.assert_called_once_with(data['name'])
                        patch_save_schedule.called_once_with()
                    patch_create_cat.assert_called_once_with(category_name=data['name'], category_description=description, category_value=val, keep_original_items=False)

                args, kwargs = insert_table_patch.call_args
                assert 'scheduled_processes' == args[0]
                p = json.loads(args[1])
                assert {'name': 'furnace4', 'script': '["services/south"]'} == p
