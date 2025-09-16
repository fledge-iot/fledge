# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
import json
from uuid import UUID
from unittest.mock import MagicMock, patch, call
import pytest
from aiohttp import web
from fledge.services.core import routes
from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.common.service_record import ServiceRecord
from fledge.services.core.interest_registry.interest_registry import InterestRegistry
from fledge.services.core import server
from fledge.services.core.scheduler.scheduler import Scheduler
from fledge.services.core.scheduler.entities import StartUpSchedule
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core.api import service
from fledge.services.core.api.plugins import common
from fledge.services.core.api.plugins.exceptions import *


__author__ = "Ashwin Gopalakrishnan, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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

    async def async_mock(self, return_value):
        return return_value

    async def test_get_health(self, mocker, client):
        # empty service registry
        resp = await client.get('/fledge/service')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert {'services': []} == json_response

        mocker.patch.object(InterestRegistry, "__init__", return_value=None)
        mocker.patch.object(InterestRegistry, "get", return_value=list())

        with patch.object(ServiceRegistry._logger, 'info') as log_patch_info:
            # populated service registry
            ServiceRegistry.register('name1', 'Storage', 'address1', 1, 1, 'protocol1')
            ServiceRegistry.register('name2', 'Southbound', 'address2', 2, 2, 'protocol2')
            s_id_3 = ServiceRegistry.register('name3', 'Southbound', 'address3', 3, 3, 'protocol3')
            s_id_4 = ServiceRegistry.register('name4', 'Notification', 'address4', 4, 4, 'protocol4')
            ServiceRegistry.register('name5', 'Management', 'address5', 5, 5, 'http')
            ServiceRegistry.register('name6', 'Northbound', 'address6', 6, 6, 'http')
            ServiceRegistry.register('name7', 'Dispatcher', 'address7', 7, 7, 'http')
            ServiceRegistry.register('name8', 'BucketStorage', 'address8', 8, 8, 'http')
            ServiceRegistry.register('name9', 'Northbound', 'address9', 9, 9, 'http')
            ServiceRegistry.unregister(s_id_3)
            ServiceRegistry.mark_as_failed(s_id_4)
            default_debugger = {"debugger": "Detached"}
            svc_3_debugger = {"debugger": "Attached", "ingress": "Suspended", "egress": "Storage"}
            svc_9_debugger = {"debugger": "Attached", "ingress": "Running", "egress": "Storage"}
            for service_record in ServiceRegistry.all():
                if service_record._type in ('Southbound', 'Northbound'):
                    if service_record._name == 'name3':
                        service_record._debug = svc_3_debugger
                    elif service_record._name == 'name9':
                        service_record._debug = svc_9_debugger
                    else:
                        service_record._debug = default_debugger
            resp = await client.get('/fledge/service')
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
                        'management_port': 2,
                        'debug': default_debugger
                    },
                    {
                        'type': 'Southbound',
                        'service_port': 3,
                        'address': 'address3',
                        'protocol': 'protocol3',
                        'status': 'shutdown',
                        'name': 'name3',
                        'management_port': 3,
                        'debug': svc_3_debugger
                    },
                    {
                        'type': 'Notification',
                        'service_port': 4,
                        'address': 'address4',
                        'protocol': 'protocol4',
                        'status': 'failed',
                        'name': 'name4',
                        'management_port': 4
                    },
                    {
                        'type': 'Management',
                        'service_port': 5,
                        'address': 'address5',
                        'protocol': 'http',
                        'status': 'running',
                        'name': 'name5',
                        'management_port': 5
                    },
                    {
                        'type': 'Northbound',
                        'service_port': 6,
                        'address': 'address6',
                        'protocol': 'http',
                        'status': 'running',
                        'name': 'name6',
                        'management_port': 6,
                        'debug': default_debugger
                    },
                    {
                        'type': 'Dispatcher',
                        'service_port': 7,
                        'address': 'address7',
                        'protocol': 'http',
                        'status': 'running',
                        'name': 'name7',
                        'management_port': 7
                    },
                    {
                        'type': 'BucketStorage',
                        'service_port': 8,
                        'address': 'address8',
                        'protocol': 'http',
                        'status': 'running',
                        'name': 'name8',
                        'management_port': 8
                    },
                    {
                        'type': 'Northbound',
                        'service_port': 9,
                        'address': 'address9',
                        'protocol': 'http',
                        'status': 'running',
                        'name': 'name9',
                        'management_port': 9,
                        'debug': svc_9_debugger
                    }
                ]
            }
        assert 11 == log_patch_info.call_count

    async def test_get_service_with_type_not_found(self, client, _type="Notification"):
        expected_msg = "No record found for {} service type".format(_type)
        resp = await client.get('/fledge/service?type={}'.format(_type))
        assert 404 == resp.status
        assert expected_msg == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": expected_msg} == json_response

    @pytest.mark.parametrize("_type, svc_record_count", [
        ("Storage", 1),
        ("Southbound", 2),
        ("Northbound", 1),
        ("Notification", 1),
        ("Management", 1),
        ("Dispatcher", 1),
        ("BucketStorage", 1)
    ])
    async def test_get_service_with_type(self, mocker, client, _type, svc_record_count):
        mocker.patch.object(InterestRegistry, "__init__", return_value=None)
        mocker.patch.object(InterestRegistry, "get", return_value=list())
        with patch.object(ServiceRegistry._logger, 'info') as log_patch_info:
            # populated service registry
            ServiceRegistry.register('name1', 'Storage', 'address1', 1, 1, 'protocol1')
            ServiceRegistry.register('name2', 'Southbound', 'address2', 2, 2, 'protocol2')
            ServiceRegistry.register('name3', 'Northbound', 'address3', 3, 3, 'protocol3')
            ServiceRegistry.register('name4', 'Southbound', 'address4', 4, 4, 'protocol4')
            ServiceRegistry.register('name5', 'Notification', 'address5', 5, 5, 'http')
            ServiceRegistry.register('name6', 'Management', 'address6', 6, 6, 'http')
            ServiceRegistry.register('name7', 'Dispatcher', 'address7', 7, 7, 'http')
            ServiceRegistry.register('name8', 'BucketStorage', 'address8', 8, 8, 'http')
        assert 8 == log_patch_info.call_count
        resp = await client.get('/fledge/service?type={}'.format(_type))
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert svc_record_count == len(json_response['services'])

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
        ('{"name": "test", "type": "south"}', 400, "Missing plugin property for type south in payload.")
    ])
    async def test_add_service_with_bad_params(self, client, code, payload, message):
        data = json.loads(payload)
        resp = await client.post('/fledge/service', data=payload)
        assert code == resp.status
        assert message == resp.reason

    async def test_insert_scheduled_process_exception_add_service(self, client):
        data = {"name": "furnace4", "type": "south", "plugin": "dht11"}

        async def q_result(*arg):
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
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        _rv = await self.async_mock(None)
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(service._logger, 'error') as patch_logger:
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(c_mgr, 'get_category_all_items',
                                      return_value=_rv) as patch_get_cat_info:
                        with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result) \
                                as query_table_patch:
                            with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=Exception()):
                                resp = await client.post('/fledge/service', data=json.dumps(data))
                                assert 500 == resp.status
                                assert 'Failed to create service.' == resp.reason
                        args1, kwargs1 = query_table_patch.call_args
                        assert 'scheduled_processes' == args1[0]
                        p2 = json.loads(args1[1])
                        assert {'return': ['name'], 'where': {'column': 'name', 'condition': '=', 'value': 'south_c',
                                                              'and': {'column': 'script', 'condition': '=',
                                                                      'value': '[\"services/south_c\"]'}}
                                } == p2
                    patch_get_cat_info.assert_called_once_with(category_name=data['name'])
            assert 1 == patch_logger.call_count

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
        data = {"name": "furnace4", "type": "south", "plugin": "dht11"}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        _rv = await self.async_mock(mock_plugin_info)
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_cat_info:
                    resp = await client.post('/fledge/service', data=json.dumps(data))
                    assert 400 == resp.status
                    assert "The '{}' category already exists".format(data['name']) == resp.reason
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_dupe_schedule_name_add_service(self, client):
        async def q_result(*arg):
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
        data = {"name": "furnace4", "type": "south", "plugin": "dht11"}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        msg = "A service with {} name already exists.".format(data['name'])
        _rv = await self.async_mock(None)
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_cat_info:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                        resp = await client.post('/fledge/service', data=json.dumps(data))
                        assert 400 == resp.status
                        assert msg == resp.reason
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert {"message": msg} == json_response
                patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    @pytest.mark.parametrize("svc_name, svc_type, svc_process, svc_script, svc_priority, enabled", [
        ("furnace4", "south", "south_c", "[\"services/south_c\"]", 100, None),
        ("Sine Wave", "south", "south_c", "[\"services/south_c\"]", 100, "true"),
        ("PI", "north", "north_C", "[\"services/north_C\"]", 200, "false"),
        ("PI2PI", "north", "north_C", "[\"services/north_C\"]", 100, "true"),
    ])
    async def test_add_service(self, client, svc_name, svc_type, svc_process, svc_script, svc_priority, enabled):
        async def async_mock_get_schedule():
            schedule = StartUpSchedule()
            schedule.schedule_id = '2129cc95-c841-441a-ad39-6469a87dbc8b'
            return schedule

        payload_dict = {"name": svc_name, "type": svc_type, "plugin": "plugin"}
        if enabled is not None:
            payload_dict["enabled"] = enabled
        payload = json.dumps(payload_dict)
        data = json.loads(payload)
        expected_insert_resp = {'rows_affected': 1, "response": "inserted"}
        mock_plugin_info = {
            'name': "Plugin",
            'version': "1.1",
            'type': svc_type,
            'interface': "1.0",
            'mode': "async",
            'config': {
                'plugin': {
                    'description': "Plugin description",
                    'type': 'string',
                    'default': "plugin"
                }
            }
        }
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        _rv1 = await self.async_mock(None)
        _rv2 = await self.async_mock(expected_insert_resp)
        _rv3 = await self.async_mock("")
        _rv4 = await async_mock_get_schedule()
        _rv5 = await self.async_mock(0)
        _rv6 = await self.async_mock({'count': 1})
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=_rv1) as patch_get_cat_info:
                    with patch.object(service, 'check_schedules', return_value=_rv5) as patch_schedules:
                        with patch.object(service, 'check_scheduled_processes', return_value=_rv6) as patch_scheduled_processes:
                            with patch.object(c_mgr, 'create_category', return_value=_rv2) as patch_create_cat:
                                with patch.object(c_mgr, 'create_child_category', return_value=_rv2) as patch_create_child_cat:
                                    with patch.object(server.Server.scheduler, 'save_schedule', return_value=_rv3) as patch_save_schedule:
                                        with patch.object(server.Server.scheduler, 'get_schedule_by_name', return_value=_rv4) as patch_get_schedule:
                                            resp = await client.post('/fledge/service', data=payload)
                                            server.Server.scheduler = None
                                            print(resp.reason)
                                            assert 200 == resp.status
                                            result = await resp.text()
                                            json_response = json.loads(result)
                                            assert {'id': '2129cc95-c841-441a-ad39-6469a87dbc8b',
                                                    'name': svc_name} == json_response
                                        patch_get_schedule.assert_called_once_with(svc_name)
                                    patch_save_schedule.assert_called_once()
                                patch_create_child_cat.assert_called_once_with(svc_type.capitalize(), [svc_name])
                            assert 2 == patch_create_cat.call_count
                            patch_create_cat.assert_called_with(svc_type.capitalize(), {}, f"{svc_type.capitalize()} microservices", True)
                        patch_scheduled_processes.assert_called_once_with(storage_client_mock, svc_process, svc_script)
                    patch_schedules.assert_called_once_with(storage_client_mock, svc_name)
                patch_get_cat_info.assert_called_once_with(category_name=svc_name)

    p1 = '{"name": "DispatcherServer", "type": "Dispatcher"}'
    p2 = '{"name": "NotificationServer", "type": "Notification"}'
    p3 = '{"name": "ManagementServer", "type": "Management"}'
    p4 = '{"name": "BucketServer", "type": "BucketStorage"}'

    @pytest.mark.parametrize("payload", [p1, p2, p3, p4])
    async def test_bad_external_service(self, client, payload):
        data = json.loads(payload)
        with patch('os.path.exists', return_value=False):
            resp = await client.post('/fledge/service', data=payload)
            assert 404 == resp.status
            msg = f"The '{data['type']}' service has not been installed correctly."
            assert msg == resp.reason
            result = await resp.text()
            json_response = json.loads(result)
            assert {"message": msg} == json_response

    @pytest.mark.parametrize("svc_name, svc_type, svc_process, svc_script, svc_priority, enabled", [
        ("Mgt Server", "Management", "management", "[\"services/management\"]", 300, None),
        ("NF Server", "Notification", "notification_c", "[\"services/notification_c\"]", 30, "true"),
        ("DS Server", "Dispatcher", "dispatcher_c", "[\"services/dispatcher_c\"]", 20, "false"),
        ("BS Server", "BucketStorage", "bucket_storage_c", "[\"services/bucket_storage_c\"]", 10, None)
    ])
    async def test_add_external_service(self, client, svc_name, svc_type, svc_process, svc_script, svc_priority, enabled):
        async def async_mock_get_schedule():
            schedule = StartUpSchedule()
            schedule.schedule_id = sch_id
            return schedule

        sch_id = '45876056-e04c-4cde-8a82-1d8dbbbe6d72'
        payload_dict = {"name": svc_name, "type": svc_type}
        if enabled is not None:
            payload_dict["enabled"] = enabled
        payload = json.dumps(payload_dict)
        data = json.loads(payload)
        svc_info = {
            "name": svc_name,
            "type": svc_type,
            "process": svc_process,
            "process_script": svc_script,
            "startup_priority": svc_priority
        }
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        _rv1 = await self.async_mock(svc_info)
        _rv2 = await self.async_mock(None)
        _rv3 = await self.async_mock(0)
        _rv4 = await self.async_mock({'count': 1})
        _rv5 = await self.async_mock({'count': 1, 'rows': [{'process_name': "blah"}]})
        _rv6 = await async_mock_get_schedule()
        with patch('os.path.exists', return_value=True):
            with patch.object(service, '_fetch_service_info', return_value=_rv1):
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(c_mgr, 'get_category_all_items', return_value=_rv2) as patch_get_cat_info:
                        with patch.object(service, 'check_schedules', return_value=_rv3) as patch_schedules:
                            with patch.object(service, 'check_scheduled_processes', return_value=_rv4) as patch_scheduled_processes:
                                with patch.object(service, 'check_schedule_entry', return_value=_rv5) as patch_schedule_entry:
                                    with patch.object(server.Server.scheduler, 'save_schedule', return_value=_rv2) as patch_save_schedule:
                                        with patch.object(server.Server.scheduler, 'get_schedule_by_name', return_value=_rv6) as patch_schedule_by_name:
                                            resp = await client.post('/fledge/service', data=payload)
                                            server.Server.scheduler = None
                                            assert 200 == resp.status
                                            result = await resp.text()
                                            json_response = json.loads(result)
                                            assert {'id': sch_id, 'name': data['name']} == json_response
                                        patch_schedule_by_name.assert_called_once_with(data['name'])
                                    patch_save_schedule.assert_called_once()
                            patch_schedules.assert_called_once_with(storage_client_mock, data['name'])
                        patch_scheduled_processes.assert_called_once_with(storage_client_mock, svc_info['process'], svc_info['process_script'])
                    patch_get_cat_info.assert_called_once_with(category_name=data['name'])


    @pytest.mark.parametrize("svc_name, svc_type, svc_process, svc_script, svc_priority", [
        ("Mgt Server", "Management", "management", "[\"services/management\"]", 300),
        ("NF Server", "Notification", "notification_c", "[\"services/notification_c\"]", 30),
        ("DS Server", "Dispatcher", "dispatcher_c", "[\"services/dispatcher_c\"]", 20),
        ("BS Server", "BucketStorage", "bucket_storage_c", "[\"services/bucket_storage_c\"]", 10)
    ])
    async def test_dupe_external_service_schedule(self, client, svc_name, svc_type, svc_process, svc_script, svc_priority):
        payload = json.dumps({"name": svc_name, "type": svc_type})
        data = json.loads(payload)
        svc_info = {
            "name": svc_name,
            "type": svc_type,
            "process": svc_process,
            "process_script": svc_script,
            "startup_priority": svc_priority
        }
        msg = f"A {svc_info['process']} service type schedule already exists."
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        _rv1 = await self.async_mock(svc_info)
        _rv2 = await self.async_mock(None)
        _rv3 = await self.async_mock(0)
        _rv4 = await self.async_mock({'count': 1})
        _rv5 = await self.async_mock({'count': 1, 'rows': [{'process_name': svc_info['process']}]})
        with patch('os.path.exists', return_value=True):
            with patch.object(service, '_fetch_service_info', return_value=_rv1):
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(c_mgr, 'get_category_all_items', return_value=_rv2) as patch_get_cat_info:
                        with patch.object(service, 'check_schedules', return_value=_rv3) as patch_schedules:
                            with patch.object(service, 'check_scheduled_processes', return_value=_rv4) as patch_scheduled_processes:
                                with patch.object(service, 'check_schedule_entry', return_value=_rv5) as patch_schedule_entry:
                                    resp = await client.post('/fledge/service', data=payload)
                                    server.Server.scheduler = None
                                    assert 400 == resp.status
                                    assert msg == resp.reason
                                    result = await resp.text()
                                    json_response = json.loads(result)
                                    assert {"message": msg} == json_response
                            patch_schedules.assert_called_once_with(storage_client_mock, data['name'])
                        patch_scheduled_processes.assert_called_once_with(storage_client_mock, svc_info['process'], svc_info['process_script'])
                    patch_get_cat_info.assert_called_once_with(category_name=data['name'])

    async def test_add_service_with_config(self, client):
        payload = '{"name": "Sine", "type": "south", "plugin": "sinusoid", "enabled": "false",' \
                  ' "config": {"dataPointsPerSec": {"value": "10"}}}'
        data = json.loads(payload)

        async def async_mock_get_schedule():
            schedule = StartUpSchedule()
            schedule.schedule_id = '2129cc95-c841-441a-ad39-6469a87dbc8b'
            return schedule

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
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        _rv1 = await self.async_mock(None)
        _rv2 = await self.async_mock(expected_insert_resp)
        _rv3 = await self.async_mock("")
        _rv4 = await async_mock_get_schedule()
        _rv5 = await self.async_mock(0)
        _rv6 = await self.async_mock({'count': 1})
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=_rv1) as patch_get_cat_info:
                    with patch.object(service, 'check_schedules', return_value=_rv5) as patch_schedules:
                        with patch.object(service, 'check_scheduled_processes', return_value=_rv6) as patch_scheduled_processes:
                            with patch.object(c_mgr, 'create_category', return_value=_rv1) as patch_create_cat:
                                with patch.object(c_mgr, 'create_child_category',
                                                  return_value=_rv1) as patch_create_child_cat:
                                    with patch.object(c_mgr, 'set_category_item_value_entry',
                                                      return_value=_rv1) as patch_set_entry:
                                        with patch.object(server.Server.scheduler, 'save_schedule',
                                                          return_value=_rv3) as patch_save_schedule:
                                            with patch.object(server.Server.scheduler, 'get_schedule_by_name',
                                                              return_value=_rv4) as patch_get_schedule:
                                                resp = await client.post('/fledge/service', data=payload)
                                                server.Server.scheduler = None
                                                assert 200 == resp.status
                                                result = await resp.text()
                                                json_response = json.loads(result)
                                                assert {'id': '2129cc95-c841-441a-ad39-6469a87dbc8b',
                                                        'name': data['name']} == json_response
                                            patch_get_schedule.assert_called_once_with(data['name'])
                                        patch_save_schedule.assert_called_once()
                                    patch_set_entry.assert_called_once_with(data['name'], 'dataPointsPerSec', '10')
                                patch_create_child_cat.assert_called_once_with('South', ['Sine'])
                            assert 2 == patch_create_cat.call_count
                            patch_create_cat.assert_called_with('South', {}, 'South microservices', True)
                        patch_scheduled_processes.assert_called_once_with(storage_client_mock, "south_c", "[\"services/south_c\"]")
                    patch_schedules.assert_called_once_with(storage_client_mock, data['name'])
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

        delete_result = {'response': 'deleted', 'rows_affected': 1}
        update_result = {'rows_affected': 1, "response": "updated"}
        query_result = [{'rows': [{'name': 'Delta #123'}], 'count': 1}]
        _rv1 = await mock_result()
        _rv2 = asyncio.ensure_future(asyncio.sleep(.1))
        _rv3 = await self.async_mock(delete_result)
        _rv4 = await self.async_mock(update_result)
        _rv5 = await self.async_mock(query_result)
        mocker.patch.object(connect, 'get_storage_async')
        get_schedule = mocker.patch.object(service, "get_schedule", return_value=_rv1)
        scheduler = mocker.patch.object(server.Server, "scheduler", MagicMock())
        delete_schedule = mocker.patch.object(scheduler, "delete_schedule", return_value=_rv2)
        disable_schedule = mocker.patch.object(scheduler, "disable_schedule", return_value=_rv2)
        delete_configuration = mocker.patch.object(ConfigurationManager, "delete_category_and_children_recursively",
                                                   return_value=_rv2)
        get_registry = mocker.patch.object(ServiceRegistry, 'get', return_value=mock_registry)
        remove_registry = mocker.patch.object(ServiceRegistry, 'remove_from_registry')
        delete_streams = mocker.patch.object(service, "delete_streams", return_value=_rv3)
        delete_plugin_data = mocker.patch.object(service, "delete_plugin_data", return_value=_rv3)
        delete_filters = mocker.patch.object(service, "delete_filters", return_value=_rv5)
        update_deprecated_ts_in_asset_tracker = mocker.patch.object(service, "update_deprecated_ts_in_asset_tracker",
                                                                    return_value=_rv4)

        mock_registry[0]._status = ServiceRecord.Status.Shutdown

        resp = await client.delete("/fledge/service/{}".format(sch_name))
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

        assert 1 == delete_streams.call_count
        args, kwargs = delete_streams.call_args_list[0]
        assert sch_name in args

        assert 1 == delete_plugin_data.call_count
        args, kwargs = delete_plugin_data.call_args_list[0]
        assert sch_name in args

        assert 1 == delete_filters.call_count
        args, kwargs = delete_plugin_data.call_args_list[0]
        assert sch_name in args

        assert 1 == update_deprecated_ts_in_asset_tracker.call_count
        args, kwargs = update_deprecated_ts_in_asset_tracker.call_args_list[0]
        assert sch_name in args

    async def test_delete_service_exception(self, mocker, client):
        resp = await client.delete("/fledge/service")
        assert 405 == resp.status
        assert 'Method Not Allowed' == resp.reason

        reg_id = 'd607c5be-792f-4993-96b7-b513674e7d3b'
        name = 'Test'
        mock_registry = [ServiceRecord(reg_id, name, "Southbound", "http", "localhost", "8118", "8118")]

        mocker.patch.object(connect, 'get_storage_async')
        mocker.patch.object(service, "get_schedule", side_effect=Exception)
        resp = await client.delete("/fledge/service/{}".format(name))
        assert 500 == resp.status
        assert resp.reason is ''

        async def mock_bad_result():
            return {"count": 0, "rows": []}

        _rv = await mock_bad_result()
        mock_registry[0]._status = ServiceRecord.Status.Shutdown
        mocker.patch.object(service, "get_schedule", return_value=_rv)

        resp = await client.delete("/fledge/service/{}".format(name))
        assert 404 == resp.status
        assert '{} service does not exist.'.format(name) == resp.reason

    async def test_post_install_package_from_repo_already_in_progress(self, client):
        async def async_mock(return_value):
            return return_value

        pkg_name = 'fledge-service-notification'
        param = {"format": "repository", "name": pkg_name}
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "install",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "install",
            "status": -1,
            "log_file_uri": ""
        }]}
        msg = '{} package installation already in progress'.format(pkg_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        _rv = await async_mock(select_row_resp)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              return_value=_rv) as query_tbl_patch:
                resp = await client.post('/fledge/service?action=install', data=json.dumps(param))
                assert 429 == resp.status
                assert msg == resp.reason
                r = await resp.text()
                actual = json.loads(r)
                assert {'message': msg} == actual
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    async def test_post_install_package_from_repo_already_installed(self, client):
        async def async_mock(return_value):
            return return_value

        pkg_name = 'fledge-service-notification'
        param = {"format": "repository", "name": pkg_name}
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "install",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        svc_list = ["storage", "south", "notification"]
        msg = '{} package is already installed'.format(pkg_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        _rv = await async_mock({'count': 0, 'rows': []})
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              return_value=_rv) as query_tbl_patch:
                with patch.object(service, 'get_service_installed', return_value=svc_list
                                  ) as svc_list_patch:
                    resp = await client.post('/fledge/service?action=install', data=json.dumps(param))
                    assert 400 == resp.status
                    assert msg == resp.reason
                    r = await resp.text()
                    actual = json.loads(r)
                    assert {'message': msg} == actual
                svc_list_patch.assert_called_once_with()
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    async def test_post_service_package_from_repo(self, client, loop):
        async def async_mock(return_value):
            return return_value

        pkg_name = 'fledge-service-notification'
        param = {"format": "repository", "name": pkg_name}
        storage_client_mock = MagicMock(StorageClientAsync)
        insert_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "install",
            "status": 0,
            "log_file_uri": ""
        }]}
        query_tbl_payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "install",
                                                             "and": {"column": "name", "condition": "=",
                                                                     "value": pkg_name}}}
        svc_list = ["storage", "south"]
        _rv1 = await async_mock({'count': 0, 'rows': []})
        _rv2 = await async_mock(([pkg_name, "fledge-north-http", "fledge-south-sinusoid"], 'log/190801-12-41-13.log'))
        _rv3 = await async_mock({"response": "inserted", "rows_affected": 1})
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv1
                              ) as query_tbl_patch:
                with patch.object(service, 'get_service_installed', return_value=svc_list) as svc_list_patch:
                    with patch.object(common, 'fetch_available_packages', return_value=_rv2
                                      ) as patch_fetch_available_package:
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=_rv3
                                          ) as insert_tbl_patch:
                            with patch.object(service._logger, "info") as log_info:
                                with patch('multiprocessing.Process'):
                                    resp = await client.post('/fledge/service?action=install', data=json.dumps(param))
                                    assert 200 == resp.status
                                    result = await resp.text()
                                    response = json.loads(result)
                                    assert 'id' in response
                                    assert '{} service installation started'.format(pkg_name) == response['message']
                                    assert response['statusLink'].startswith('fledge/package/install/status?id=')
                            assert 1 == log_info.call_count
                            log_info.assert_called_once_with('{} service installation started...'.format(pkg_name))
                        args, kwargs = insert_tbl_patch.call_args_list[0]
                        assert 'packages' == args[0]
                        actual = json.loads(args[1])
                        assert 'id' in actual
                        assert pkg_name == actual['name']
                        assert 'install' == actual['action']
                        assert -1 == actual['status']
                        assert '' == actual['log_file_uri']
                    patch_fetch_available_package.assert_called_once_with()
                svc_list_patch.assert_called_once_with()
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            actual = json.loads(args[1])
            assert query_tbl_payload == actual

    @pytest.mark.parametrize("req_param, post_param, message", [
        ("?action=install", {"name": "blah"}, "format param is required"),
        ("?action=install", {"format": "repository"}, "Missing name property in payload."),
        ("?action=install", {"format": "blah", "name": "blah"}, "Invalid format. Must be 'repository'"),
        ("?action=blah", {"format": "blah", "name": "blah"}, "blah is not a valid action"),
        ("?action=install", {"format": "repository", "name": "fledge-service-notification", "version": "1.6"},
         "Service semantic version is incorrect; it should be like X.Y.Z"),
        ("?action=install", {"format": "repository", "name": "blah"},
         "name should start with \"fledge-service-\" prefix")
    ])
    async def test_bad_post_service_package_from_repo(self, client, req_param, post_param, message):
        resp = await client.post('/fledge/service{}'.format(req_param), data=json.dumps(post_param))
        assert 400 == resp.status
        assert message == resp.reason

    async def test_post_service_package_from_repo_is_not_available(self, client):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-service-notification"
        param = {"format": "repository", "name": pkg_name}
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "install",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        storage_client_mock = MagicMock(StorageClientAsync)
        svc_list = ["storage", "south"]
        _rv1 = await async_mock({'count': 0, 'rows': []})
        _rv2 = await async_mock(([], 'log/190801-12-19-24'))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              return_value=_rv1) as query_tbl_patch:
                with patch.object(service, 'get_service_installed', return_value=svc_list) as svc_list_patch:
                    with patch.object(common, 'fetch_available_packages', return_value=_rv2
                                      ) as patch_fetch_available_package:
                        resp = await client.post('/fledge/service?action=install', data=json.dumps(param))
                        assert 404 == resp.status
                        assert "'{} service is not available for the given repository'".format(pkg_name) == resp.reason
                    patch_fetch_available_package.assert_called_once_with()
                svc_list_patch.assert_called_once_with()
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    async def test_get_service_available(self, client):
        async def async_mock(return_value):
            return return_value

        _rv = await async_mock(([], 'log/190801-12-19-24'))
        with patch.object(common, 'fetch_available_packages', return_value=_rv) as patch_fetch_available_package:
            resp = await client.get('/fledge/service/available')
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'services': [], 'link': 'log/190801-12-19-24'} == json_response
        patch_fetch_available_package.assert_called_once_with('service')

    async def test_bad_get_service_available(self, client):
        log_path = "log/190801-12-19-24"
        msg = "Fetch available service package request failed"
        with patch.object(common, 'fetch_available_packages', side_effect=PackageError(log_path)) as patch_fetch_available_package:
            resp = await client.get('/fledge/service/available')
            assert 400 == resp.status
            assert msg == resp.reason
            r = await resp.text()
            json_response = json.loads(r)
            assert log_path == json_response['link']
            assert msg == json_response['message']
        patch_fetch_available_package.assert_called_once_with('service')

    @pytest.mark.parametrize("mock_value1, mock_value2, exp_result", [
        ([(['/usr/local/fledge/services'], [], [])], [(['/usr/local/fledge/python/fledge/services/management'],
                                                       [], [])], []),
        ([(['/usr/local/fledge/services'], [], ['fledge.services.south', 'fledge.services.storage'])], [],
         ["south", "storage"]),
        ([(['/usr/local/fledge/services'], [],
           ['fledge.services.south', 'fledge.services.storage', 'fledge.services.notification'])], [],
         ["south", "storage", "notification"]),
        ([(['/usr/local/fledge/services'], [], ['fledge.services.south', 'fledge.services.storage'])],
         [(['/usr/local/fledge/python/fledge/services/management'], [], [])], ["south", "storage"]),
        ([(['/usr/local/fledge/services'], [], ['fledge.services.south', 'fledge.services.storage'])],
         [(['/usr/local/fledge/python/fledge/services/management'], [], ['__init__.py', '__main__.py'])],
         ["south", "storage", "management"]),
        ([(['/usr/local/fledge/services'], [],
           ['fledge.services.south', 'fledge.services.storage', 'fledge.services.notification'])],
         [(['/usr/local/fledge/python/fledge/services/management'], [], ['__init__.py', '__main__.py'])],
         ["south", "storage", "notification", "management"]),
        ([(['/usr/local/fledge/services'], [],
           ['fledge.services.south', 'fledge.services.storage', 'fledge.services.north'])], [],
         ["south", "storage", "north"]),
        ([(['/usr/local/fledge/services'], [],
           ['fledge.services.south', 'fledge.services.storage', 'fledge.services.dispatcher'])], [],
         ["south", "storage", "dispatcher"]),
        ([(['/usr/local/fledge/services'], [],
           ['fledge.services.south', 'fledge.services.storage', 'fledge.services.north',
            'fledge.services.notification', 'fledge.services.dispatcher', 'fledge.services.bucket'])], [],
         ["south", "storage", "north", "notification", "dispatcher", "bucket"]),
        ([(['/usr/local/fledge/services'], [], ['fledge.services.south', 'fledge.services.storage'])],
         [(['/usr/local/fledge/python/fledge/services/management'], [], ['__init__.py', '__main__.py']),
          (['/usr/local/fledge/python/fledge/services/test'], [], ['__init__.py', '__main__.py'])],
         ["south", "storage", "management", "test"])
    ])
    async def test_get_service_installed(self, client, mock_value1, mock_value2, exp_result):
        with patch('os.walk', side_effect=(mock_value1,)) as mockwalk, \
             patch('os.listdir') as mocklistdir, \
             patch('os.path.isfile') as mockisfile, \
             patch('os.path.isdir') as mockisdir, \
             patch('os.path.exists') as mockexists, \
             patch('fledge.services.core.api.service._logger') as mocklogger:

            # Mock os.path.exists to return True for both service paths
            mockexists.return_value = True

            # Set up mocks for Python services based on mock_value2
            if mock_value2:  # If there's Python service mock data
                # Extract service names from the mock_value2 directory paths
                python_services = []
                available_files = {}

                for walk_data in mock_value2:
                    root_list, dirs, files = walk_data
                    root = root_list[0]  # Get the actual path string from the list
                    service_name = root.split('/')[-1]  # Extract service name from path
                    python_services.append(service_name)
                    available_files[service_name] = files

                mocklistdir.return_value = python_services
                mockisdir.return_value = True

                # Mock os.path.isfile based on the files available for each service
                def mock_isfile_side_effect(path):
                    for service_name, files in available_files.items():
                        if service_name in path:
                            filename = path.split('/')[-1]
                            return filename in files
                    return False

                mockisfile.side_effect = mock_isfile_side_effect
            else:
                mocklistdir.return_value = []
                mockisdir.return_value = False
                mockisfile.return_value = False

            resp = await client.get('/fledge/service/installed')
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert json_response == {'services': exp_result}

        # Only assert walk was called if there's C-service data
        if mock_value1:
            mockwalk.assert_called_once()

    @pytest.mark.parametrize("param", ["blah", 1, "storage", "south"])
    async def test_bad_type_update_package(self, client, param):
        resp = await client.put('/fledge/service/{}/name/update'.format(param), data=None)
        assert 400 == resp.status
        assert "Invalid service type." == resp.reason

    async def test_bad_update_package(self, client, _type="notification", name="notification"):
        svc_list = ["storage", "south"]
        with patch.object(service, 'get_service_installed', return_value=svc_list) as svc_list_patch:
            resp = await client.put('/fledge/service/{}/{}/update'.format(_type, name), data=None)
            assert 404 == resp.status
            assert "'{} service is not installed yet. Hence update is not possible.'".format(name) == resp.reason
        svc_list_patch.assert_called_once_with()

    async def test_package_update_already_in_progress(self, client, _type="notification", name="notification"):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-service-{}".format(name)
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}

        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "update",
            "status": -1,
            "log_file_uri": ""
        }]}
        msg = '{} package update already in progress'.format(pkg_name)
        svc_list = ["south", "storage", name]
        storage_client_mock = MagicMock(StorageClientAsync)
        _rv = await async_mock(select_row_resp)
        with patch.object(service, 'get_service_installed', return_value=svc_list) as svc_list_patch:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=_rv) as query_tbl_patch:
                    resp = await client.put('/fledge/service/{}/{}/update'.format(_type, name),
                                            data=None)
                    assert 429 == resp.status
                    assert msg == resp.reason
                    r = await resp.text()
                    actual = json.loads(r)
                    assert {'message': msg} == actual
                args, kwargs = query_tbl_patch.call_args_list[0]
                assert 'packages' == args[0]
                assert payload == json.loads(args[1])
        svc_list_patch.assert_called_once_with()

    async def test_package_update_when_in_use(self, client, _type="notification", name="notification"):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-service-{}".format(name)
        svc_name = "NF #1"
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "update",
            "status": 0,
            "log_file_uri": ""
        }]}
        delete = {"response": "deleted", "rows_affected": 1}
        delete_payload = {"where": {"column": "action", "condition": "=", "value": "update",
                                    "and": {"column": "name", "condition": "=", "value": pkg_name}}}

        sch_info = {'count': 1, 'rows': [
            {'id': '6637c9ff-7090-4774-abca-07dee59a0610', 'schedule_name': svc_name, 'enabled': 't'}]}
        insert = {"response": "inserted", "rows_affected": 1}
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        svc_list = ["south", "storage", name]
        _rv1 = await async_mock(delete)
        _rv2 = await async_mock((True, "Schedule successfully disabled"))
        _rv3 = await async_mock(insert)
        _se1 = await async_mock(select_row_resp)
        _se2 = await async_mock(sch_info)
        with patch.object(service, 'get_service_installed', return_value=svc_list
                          ) as svc_list_patch:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  side_effect=[_se1, _se2]) as query_tbl_patch:
                    with patch.object(storage_client_mock, 'delete_from_tbl',
                                      return_value=_rv1) as delete_tbl_patch:
                        with patch.object(server.Server.scheduler, 'disable_schedule', return_value=_rv2) as disable_sch_patch:
                            with patch.object(service._logger, "warning") as log_warn_patch:
                                with patch.object(storage_client_mock, 'insert_into_tbl',
                                                  return_value=_rv3) as insert_tbl_patch:
                                    with patch('multiprocessing.Process'):
                                        resp = await client.put('/fledge/service/{}/{}/update'.format(_type, name),
                                                                data=None)
                                        server.Server.scheduler = None
                                        assert 200 == resp.status
                                        result = await resp.text()
                                        response = json.loads(result)
                                        assert 'id' in response
                                        assert '{} update started'.format(pkg_name) == response['message']
                                        assert response['statusLink'].startswith('fledge/package/update/status?id=')
                                args, kwargs = insert_tbl_patch.call_args_list[0]
                                assert 'packages' == args[0]
                                actual = json.loads(args[1])
                                assert 'id' in actual
                                assert pkg_name == actual['name']
                                assert 'update' == actual['action']
                                assert -1 == actual['status']
                                assert '' == actual['log_file_uri']
                            assert 1 == log_warn_patch.call_count
                            log_warn_patch.assert_called_once_with(
                                'Schedule is disabled for {}, as {} service of type {} is being updated...'.format(
                                    sch_info['rows'][0]['schedule_name'], name, _type))
                        disable_sch_patch.assert_called_once_with(UUID(sch_info['rows'][0]['id']))
                    args, kwargs = delete_tbl_patch.call_args_list[0]
                    assert 'packages' == args[0]
                    assert delete_payload == json.loads(args[1])
                args, kwargs = query_tbl_patch.call_args_list[0]
                assert 'packages' == args[0]
                assert payload == json.loads(args[1])
        svc_list_patch.assert_called_once_with()

    async def test_package_update_when_not_in_use(self, client, _type="notification", name="notification"):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-service-{}".format(name)
        svc_name = "NF #1"
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "update",
            "status": 0,
            "log_file_uri": ""
        }]}
        delete = {"response": "deleted", "rows_affected": 1}
        delete_payload = {"where": {"column": "action", "condition": "=", "value": "update",
                                    "and": {"column": "name", "condition": "=", "value": pkg_name}}}

        sch_info = {'count': 1, 'rows': [
            {'id': '6637c9ff-7090-4774-abca-07dee59a0610', 'schedule_name': svc_name, 'enabled': 'f'}]}
        insert = {"response": "inserted", "rows_affected": 1}
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        svc_list = ["south", "storage", name]
        _rv1 = await async_mock(delete)
        _rv2 = await async_mock(insert)
        _se1 = await async_mock(select_row_resp)
        _se2 = await async_mock(sch_info)
        with patch.object(service, 'get_service_installed', return_value=svc_list
                          ) as svc_list_patch:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  side_effect=[_se1, _se2]) as query_tbl_patch:
                    with patch.object(storage_client_mock, 'delete_from_tbl',
                                      return_value=_rv1) as delete_tbl_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl',
                                          return_value=_rv2) as insert_tbl_patch:
                            with patch('multiprocessing.Process'):
                                resp = await client.put('/fledge/service/{}/{}/update'.format(_type, name), data=None)
                                server.Server.scheduler = None
                                assert 200 == resp.status
                                result = await resp.text()
                                response = json.loads(result)
                                assert 'id' in response
                                assert '{} update started'.format(pkg_name) == response['message']
                                assert response['statusLink'].startswith('fledge/package/update/status?id=')
                        args, kwargs = insert_tbl_patch.call_args_list[0]
                        assert 'packages' == args[0]
                        actual = json.loads(args[1])
                        assert 'id' in actual
                        assert pkg_name == actual['name']
                        assert 'update' == actual['action']
                        assert -1 == actual['status']
                        assert '' == actual['log_file_uri']
                    args, kwargs = delete_tbl_patch.call_args_list[0]
                    assert 'packages' == args[0]
                    assert delete_payload == json.loads(args[1])
                args, kwargs = query_tbl_patch.call_args_list[0]
                assert 'packages' == args[0]
                assert payload == json.loads(args[1])
        svc_list_patch.assert_called_once_with()

    # TODO:  add negative tests and C type plugin add service tests
