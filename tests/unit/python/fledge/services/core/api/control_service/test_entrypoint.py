import asyncio
import json
import sys

from unittest.mock import MagicMock, patch
import pytest
from aiohttp import web

from fledge.common.audit_logger import AuditLogger
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.web import middleware
from fledge.services.core import connect, routes
from fledge.services.core.api.control_service import entrypoint


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2023 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args):
    return None if len(args) == 0 else args[0]


@pytest.allure.feature("unit")
@pytest.allure.story("api", "entrypoint")
class TestEntrypoint:
    """ Control Flow Entrypoint API tests """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_all_entrypoints(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {'count': 3, 'rows': [
            {'name': 'EP1', 'description': 'EP1', 'type': 1, 'operation_name': 'OP1', 'destination': 0,
             'destination_arg': '', 'anonymous': 't'},
            {'name': 'EP2', 'description': 'Ep2', 'type': 0, 'operation_name': '', 'destination': 0,
             'destination_arg': '', 'anonymous': 'f'},
            {'name': 'EP3', 'description': 'EP3', 'type': 1, 'operation_name': 'OP2', 'destination': 0,
             'destination_arg': '', 'anonymous': 'f'}]}
        expected_api_response = {"controls": [{"name": "EP1", "description": "EP1", "permitted": True},
                                              {"name": "EP2", "description": "Ep2", "permitted": True},
                                              {"name": "EP3", "description": "EP3", "permitted": True}]}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=rv) as patch_query_tbl:
                resp = await client.get('/fledge/control/manage')
                assert 200 == resp.status
                json_response = json.loads(await resp.text())
                assert 'controls' in json_response
                assert expected_api_response == json_response
            patch_query_tbl.assert_called_once_with('control_api')

    @pytest.mark.parametrize("exception, message, status_code", [
        (ValueError, 'name should be in string.', 400),
        (KeyError, 'EP control entrypoint not found.', 404),
        (KeyError, '', 404),
        (Exception, 'Interval Server error.', 500)
    ])
    async def test_bad_get_entrypoint_by_name(self, client, exception, message, status_code):
        ep_name = "EP"
        with patch.object(entrypoint, '_get_entrypoint', side_effect=exception(message)):
            with patch.object(entrypoint._logger, 'error') as patch_logger:
                resp = await client.get('/fledge/control/manage/{}'.format(ep_name))
                assert status_code == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            if exception == Exception:
                patch_logger.assert_called()

    async def test_get_entrypoint_by_name(self, client):
        ep_name = "EP"
        storage_result = {'name': ep_name, 'description': 'EP1', 'type': 'operation', 'operation_name': 'OP1',
                          'destination': 'broadcast', 'anonymous': True, 'constants': {'x': '640', 'y': '480'},
                          'variables': {'rpm': '800', 'distance': '138'}, 'allow': ['admin', 'user']}
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro(storage_result)
            rv2 = await mock_coro(True)
        else:
            rv1 = asyncio.ensure_future(mock_coro(storage_result))
            rv2 = asyncio.ensure_future(mock_coro(True))
        with patch.object(entrypoint, '_get_entrypoint', return_value=rv1) as patch_entrypoint:
            with patch.object(entrypoint, '_get_permitted', return_value=rv2) as patch_permitted:
                resp = await client.get('/fledge/control/manage/{}'.format(ep_name))
                assert 200 == resp.status
                json_response = json.loads(await resp.text())
                assert 'permitted' in json_response
                assert storage_result == json_response
            assert 1 == patch_permitted.call_count
        patch_entrypoint.assert_called_once_with(ep_name)

    async def test_create_entrypoint_in_use(self, client):
        ep_name = "SetLatheSpeed"
        payload = {"name": ep_name, "description": "Set the speed of the lathe", "type": "write",
                   "destination": "asset", "asset": "lathe", "constants": {"units": "spin"},
                   "variables": {"rpm": "100"}, "allow": [], "anonymous": False}
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {"count": 1, "rows": [{"name": ep_name}]}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=rv) as patch_query_tbl:
                resp = await client.post('/fledge/control/manage', data=json.dumps(payload))
                assert 400 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'message': '{} control entrypoint is already in use.'.format(ep_name)} == json_response
            patch_query_tbl.assert_called_once_with('control_api')

    async def test_create_entrypoint(self, client):
        ep_name = "SetLatheSpeed"
        payload = {"name": ep_name, "description": "Set the speed of the lathe", "type": "write",
                   "destination": "asset", "asset": "lathe", "constants": {"units": "spin"},
                   "variables": {"rpm": "100"}, "allow": [], "anonymous": False}
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {"count": 0, "rows": []}
        insert_result = {"response": "inserted", "rows_affected": 1}

        @asyncio.coroutine
        def i_result(*args):
            table = args[0]
            insert_payload = args[1]
            if table == 'control_api':
                p = {'name': payload['name'], 'description': payload['description'], 'type': 0, 'operation_name': '',
                     'destination': 2, 'destination_arg': payload['asset'],
                     'anonymous': 'f' if payload['anonymous'] is False else 't'}
                assert p == json.loads(insert_payload)
            elif table == 'control_api_parameters':
                if json.loads(insert_payload)['constant'] == 't':
                    assert {'name': ep_name, 'parameter': 'units', 'value': 'spin', 'constant': 't'
                            } == json.loads(insert_payload)
                else:
                    assert {'name': ep_name, 'parameter': 'rpm', 'value': '100', 'constant': 'f'
                            } == json.loads(insert_payload)
            elif table == 'control_api_acl':
                pass
            return insert_result

        if sys.version_info >= (3, 8):
            rv = await mock_coro(storage_result)
            arv = await mock_coro(None)
        else:
            rv = asyncio.ensure_future(mock_coro(storage_result))
            arv = asyncio.ensure_future(mock_coro(None))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=rv) as patch_query_tbl:
                with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=i_result
                                  ) as patch_insert_tbl:
                    with patch.object(AuditLogger, '__init__', return_value=None):
                        with patch.object(AuditLogger, 'information', return_value=arv) as audit_info_patch:
                            resp = await client.post('/fledge/control/manage', data=json.dumps(payload))
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert {'message': '{} control entrypoint has been created successfully.'.format(ep_name)
                                    } == json_response
                        audit_info_patch.assert_called_once_with('CTEAD', payload)
                assert 3 == patch_insert_tbl.call_count
            patch_query_tbl.assert_called_once_with('control_api')

    async def test_update_entrypoint_not_found(self, client):
        ep_name = "EP"
        message = '{} control entrypoint not found.'.format(ep_name)
        payload = {"where": {"column": "name", "condition": "=", "value": ep_name}}
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {"count": 0, "rows": []}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv
                              ) as patch_query_tbl:
                resp = await client.put('/fledge/control/manage/{}'.format(ep_name))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, kwargs = patch_query_tbl.call_args
            assert 'control_api' == args[0]
            assert payload == json.loads(args[1])

    async def test_update_entrypoint(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        ep_name = "SetLatheSpeed"
        payload = {"description": "Updated"}
        query_payload = '{"where": {"column": "name", "condition": "=", "value": "SetLatheSpeed"}}'
        storage_result = {"count": 1, "rows": [{"name": ep_name}]}
        ep_info = {'name': ep_name, 'description': 'Perform speed of lathe', 'type': 'operation',
                   'operation_name': 'Speed', 'destination': 'broadcast', 'anonymous': False,
                   'constants': {'x': '640', 'y': '480'}, 'variables': {'rpm': '800', 'distance': '138'}, 'allow': []}
        new_ep_info = {'name': ep_name, 'description': payload['description'], 'type': 'operation',
                       'operation_name': 'Speed', 'destination': 'broadcast', 'anonymous': False,
                       'constants': {'x': '640', 'y': '480'}, 'variables': {'rpm': '800', 'distance': '138'},
                       'allow': []}

        update_payload = ('{"values": {"description": "Updated"}, '
                          '"where": {"column": "name", "condition": "=", "value": "SetLatheSpeed"}}')
        update_result = {"response": "updated", "rows_affected": 1}
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro(storage_result)
            rv2 = await mock_coro(ep_info)
            rv3 = await mock_coro(new_ep_info)
            rv4 = await mock_coro(update_result)
            arv = await mock_coro(None)
        else:
            rv1 = asyncio.ensure_future(mock_coro(storage_result))
            arv = asyncio.ensure_future(mock_coro(None))
            rv2 = asyncio.ensure_future(mock_coro(ep_info))
            rv3 = asyncio.ensure_future(mock_coro(new_ep_info))
            rv4 = asyncio.ensure_future(mock_coro(update_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv1
                              ) as patch_query_tbl:
                with patch.object(entrypoint, '_get_entrypoint', side_effect=[rv2, rv3]) as patch_entrypoint:
                    with patch.object(storage_client_mock, 'update_tbl', return_value=rv4) as patch_update_tbl:
                        with patch.object(AuditLogger, '__init__', return_value=None):
                            with patch.object(AuditLogger, 'information', return_value=arv
                                              ) as audit_info_patch:
                                resp = await client.put('/fledge/control/manage/{}'.format(ep_name),
                                                        data=json.dumps(payload))
                                assert 200 == resp.status
                                result = await resp.text()
                                json_response = json.loads(result)
                                assert {'message': '{} control entrypoint has been updated successfully.'.format(
                                    ep_name)} == json_response
                            audit_info_patch.assert_called_once_with(
                                'CTECH', {"entrypoint": new_ep_info, "old_entrypoint": ep_info})
                    patch_update_tbl.assert_called_once_with('control_api', update_payload)
                assert 2 == patch_entrypoint.call_count
            patch_query_tbl.assert_called_once_with('control_api', query_payload)

    async def test_delete_entrypoint_not_found(self, client):
        ep_name = "EP"
        message = '{} control entrypoint not found.'.format(ep_name)
        payload = {"where": {"column": "name", "condition": "=", "value": ep_name}}
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {"count": 0, "rows": []}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv
                              ) as patch_query_tbl:
                resp = await client.delete('/fledge/control/manage/{}'.format(ep_name))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, kwargs = patch_query_tbl.call_args
            assert 'control_api' == args[0]
            assert payload == json.loads(args[1])

    async def test_delete_entrypoint(self, client):
        ep_name = "EP"
        payload = {"where": {"column": "name", "condition": "=", "value": ep_name}}
        storage_result = {"count": 0, "rows": [
            {'name': ep_name, 'description': 'EP1', 'type': 'operation', 'operation_name': 'OP1',
             'destination': 'broadcast', 'anonymous': True, 'constants': {'x': '640', 'y': '480'},
             'variables': {'rpm': '800', 'distance': '138'}, 'allow': ['admin', 'user']}]}
        message = "{} control entrypoint has been deleted successfully.".format(ep_name)
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro(storage_result)
            rv2 = await mock_coro(None)
            arv = await mock_coro(None)
        else:
            rv1 = asyncio.ensure_future(mock_coro(storage_result))
            rv2 = asyncio.ensure_future(mock_coro(None))
            arv = asyncio.ensure_future(mock_coro(None))
        storage_client_mock = MagicMock(StorageClientAsync)
        del_payload = {"where": {"column": "name", "condition": "=", "value": ep_name}}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv1
                              ) as patch_query_tbl:
                with patch.object(storage_client_mock, 'delete_from_tbl', return_value=rv2
                                  ) as patch_delete_tbl:
                    with patch.object(AuditLogger, '__init__', return_value=None):
                        with patch.object(AuditLogger, 'information', return_value=arv) as audit_info_patch:
                            resp = await client.delete('/fledge/control/manage/{}'.format(ep_name))
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert {"message": message} == json_response
                        audit_info_patch.assert_called_once_with('CTEDL', {'message': message, "name": ep_name})
                assert 3 == patch_delete_tbl.call_count
                del_args = patch_delete_tbl.call_args_list
                args1, _ = del_args[0]
                assert 'control_api_acl' == args1[0]
                assert del_payload == json.loads(args1[1])
                args2, _ = del_args[1]
                assert 'control_api_parameters' == args2[0]
                assert del_payload == json.loads(args2[1])
                args3, _ = del_args[2]
                assert 'control_api' == args3[0]
                assert del_payload == json.loads(args3[1])
            args, kwargs = patch_query_tbl.call_args
            assert 'control_api' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.parametrize("ep_type", ["operation", "write"])
    async def test_update_request_entrypoint(self, client, ep_type):
        from fledge.services.core.service_registry.service_registry import ServiceRegistry
        from fledge.common.service_record import ServiceRecord

        ServiceRegistry._registry = []

        with patch.object(ServiceRegistry._logger, 'info'):
            ServiceRegistry.register('Fledge Storage', 'Storage', '127.0.0.1', 1, 1, 'http')
            ServiceRegistry.register('Dispatcher Service', 'Dispatcher', '127.0.0.1', 8, 8, 'http')

        ep_name = "SetLatheSpeed"
        if ep_type == "operation":
            storage_result = {'name': ep_name, 'description': 'Perform speed of lathe', 'type': 'operation',
                              'operation_name': 'Speed', 'destination': 'broadcast', 'anonymous': False,
                              'constants': {'x': '640', 'y': '480'}, 'variables': {'rpm': '800', 'distance': '138'},
                              'allow': []}
            dispatch_payload = {'destination': 'broadcast', 'source': 'API', 'source_name': 'Anonymous',
                                'operation': {'Speed': {'x': '420', 'y': '480', 'rpm': '800', 'distance': '200'}}}
            payload = {"x": "420", "distance": "200"}
            dispatch_endpoint = 'dispatch/operation'
        else:
            storage_result = {'name': ep_name, 'description': 'Perform speed of lathe', 'type': 'write',
                              'destination': 'broadcast', 'anonymous': False, 'constants': {'x': '640', 'y': '480'},
                              'variables': {'rpm': '800', 'distance': '138'}, 'allow': ['admin', 'user']}
            payload = {"rpm": "1200"}
            dispatch_endpoint = 'dispatch/write'
            dispatch_payload = {'destination': 'broadcast', 'source': 'API', 'source_name': 'Anonymous',
                                'write': {'x': '640', 'y': '480', 'rpm': '1200', 'distance': '138'}}

        svc_info = (ServiceRecord("d607c5be-792f-4993-96b7-b513674e7d3b",
                                  ep_name, "Dispatcher", "http", "127.0.0.1", "8118", "8118"), "Token")

        if sys.version_info >= (3, 8):
            rv1 = await mock_coro(storage_result)
            rv2 = await mock_coro(svc_info)
            rv3 = await mock_coro(None)
        else:
            rv1 = asyncio.ensure_future(mock_coro(storage_result))
            rv2 = asyncio.ensure_future(mock_coro(svc_info))
            rv3 = asyncio.ensure_future(mock_coro(None))

        with patch.object(entrypoint, '_get_entrypoint', return_value=rv1):
            with patch.object(entrypoint, '_get_service_record_info_along_with_bearer_token',
                              return_value=rv2) as patch_service:
                with patch.object(entrypoint, '_call_dispatcher_service_api',
                                  return_value=rv3) as patch_call_service:
                    resp = await client.put('/fledge/control/request/{}'.format(ep_name), data=json.dumps(payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'message': '{} control entrypoint URL called.'.format(ep_name)} == json_response
                    if ep_type == "operation":
                        op = dispatch_payload['operation']['Speed']
                        assert storage_result['constants']['x'] != op['x']
                        assert storage_result['constants']['y'] == op['y']
                        assert storage_result['variables']['distance'] != op['distance']
                        assert storage_result['variables']['rpm'] == op['rpm']
                    else:
                        write = dispatch_payload['write']
                        assert storage_result['constants']['x'] == write['x']
                        assert storage_result['constants']['y'] == write['y']
                        assert storage_result['variables']['distance'] == write['distance']
                        assert storage_result['variables']['rpm'] != write['rpm']
                patch_call_service.assert_called_once_with('http', '127.0.0.1', 8118, dispatch_endpoint,
                                                           svc_info[1], dispatch_payload)
            patch_service.assert_called_once_with()

    @pytest.mark.parametrize("identifier, identifier_value", [
        (0, 'write'),
        (1, 'operation'),
        ('write', 0),
        ('operation', 1)
    ])
    async def test__get_type(self, identifier, identifier_value):
        assert identifier_value == await entrypoint._get_type(identifier)

    @pytest.mark.parametrize("identifier, identifier_value", [
        (0, 'broadcast'),
        (1, 'service'),
        (2, 'asset'),
        (3, 'script'),
        ('broadcast', 0),
        ('service', 1),
        ('asset', 2),
        ('script', 3)
    ])
    async def test__get_destination(self, identifier, identifier_value):
        assert identifier_value == await entrypoint._get_destination(identifier)

    async def test__update_params(self):
        ep_name = "SetLatheSpeed"
        old = {'x': '640', 'y': '480'}
        new = {'x': '180', 'z': '90'}
        is_constant = 't'
        storage_client_mock = MagicMock(StorageClientAsync)
        rows_affected = {"response": "updated", "rows_affected": 1}
        rv = await mock_coro(rows_affected) if sys.version_info >= (3, 8) else (
            asyncio.ensure_future(mock_coro(rows_affected)))
        tbl_name = 'control_api_parameters'
        delete_payload = {"where": {"column": "name", "condition": "=", "value": ep_name,
                                    "and": {"column": "constant", "condition": "=", "value": "t",
                                            "and": {"column": "parameter", "condition": "=", "value": list(old)[1]}}}}
        insert_payload = {'name': ep_name, 'parameter': 'z', 'value': new['z'], 'constant': 't'}
        update_payload = {"where": {"column": "name", "condition": "=", "value": ep_name,
                                    "and": {"column": "constant", "condition": "=", "value": "t",
                                            "and": {"column": "parameter", "condition": "=", "value": "x"}}},
                          "values": {"value": new['x']}}
        with patch.object(storage_client_mock, 'update_tbl', return_value=rv) as patch_update_tbl:
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=rv) as patch_delete_tbl:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=rv) as patch_insert_tbl:
                    await entrypoint._update_params(ep_name, old, new, is_constant, storage_client_mock)
                args, _ = patch_insert_tbl.call_args
                assert tbl_name == args[0]
                assert insert_payload == json.loads(args[1])
            args, _ = patch_delete_tbl.call_args
            assert tbl_name == args[0]
            assert delete_payload == json.loads(args[1])
        args, _ = patch_update_tbl.call_args
        assert tbl_name == args[0]
        assert update_payload == json.loads(args[1])

    async def test__get_entrypoint(self):
        ep_name = "SetLatheSpeed"
        storage_client_mock = MagicMock(StorageClientAsync)
        payload = {"where": {"column": "name", "condition": "=", "value": ep_name}}
        storage_result1 = {"count": 1, "rows": [
            {'name': ep_name, 'description': 'Perform lathe Speed', 'type': 'operation', 'operation_name': 'Speed',
             'destination': 'broadcast', 'destination_arg': '', 'anonymous': True,
             'constants': {}, 'variables': {},
             'allow': []}]}
        storage_result2 = {"count": 0, "rows": []}
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro(storage_result1)
            rv2 = await mock_coro(storage_result2)
            rv3 = await mock_coro(storage_result2)
        else:
            rv1 = asyncio.ensure_future(mock_coro(storage_result1))
            rv2 = asyncio.ensure_future(mock_coro(storage_result2))
            rv3 = asyncio.ensure_future(mock_coro(storage_result2))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=[rv1, rv2, rv3]
                              ) as patch_query_tbl:
                await entrypoint._get_entrypoint(ep_name)
            assert 3 == patch_query_tbl.call_count
            args1 = patch_query_tbl.call_args_list[0]
            assert 'control_api' == args1[0][0]
            assert payload == json.loads(args1[0][1])
            args2 = patch_query_tbl.call_args_list[1]
            assert 'control_api_parameters' == args2[0][0]
            assert payload == json.loads(args2[0][1])
            args3 = patch_query_tbl.call_args_list[2]
            assert 'control_api_acl' == args3[0][0]
            assert payload == json.loads(args3[0][1])

    @pytest.mark.parametrize("payload", [
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'operation',
         'operation_name': 'OP', 'destination': 'script', 'script': 'S1', 'anonymous': False},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'write',
         'destination': 'script', 'script': 'S1', 'constants': {'unit': 'cm'}, 'variables': {'aperture': 'f/11'}},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'operation',
         'operation_name': 'OP', 'destination': 'asset', 'asset': 'AS'},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'write',
         'destination': 'asset', 'asset': 'AS', 'constants': {'unit': 'cm'}, 'variables': {'aperture': 'f/11'}},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'operation',
         'operation_name': 'OP', 'destination': 'broadcast'},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'write',
         'destination': 'broadcast', 'constants': {'unit': 'cm'}, 'variables': {'aperture': 'f/11'}, 'anonymous': True},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'operation',
         'operation_name': 'OP', 'destination': 'service', 'service': 'Camera'},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'write',
         'destination': 'service', 'service': 'Camera', 'constants': {'unit': 'cm'}, 'variables': {'aperture': 'f/11'}},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'operation',
         'operation_name': 'OP', 'destination': 'script', 'script': 'S1', 'anonymous': False,
         'constants': {'unit': 'cm'}, 'variables': {'aperture': 'f/16'}}
    ])
    async def test__check_parameters(self, payload):
        cols = await entrypoint._check_parameters(payload)
        assert isinstance(cols, dict)

    @pytest.mark.parametrize("payload", [
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'operation',
         'operation_name': 'OP', 'destination': 'script', 'script': 'S1', 'anonymous': False},
        {'name': 'FocusCamera', 'description': 'Perform focus on camera', 'type': 'write',
         'destination': 'script', 'script': 'S1', 'constants': {'unit': 'cm'}, 'variables': {'aperture': 'f/11'}},
        {'anonymous': True},
        {'description': 'updated'},
        {'type': 'operation', 'operation_name': 'Distance'},
        {'type': 'operation', 'operation_name': 'Test', 'constants': {'unit': 'cm'}, 'variables': {'aperture': 'f/11'}},
        {'type': 'write', 'constants': {'unit': 'cm'}, 'variables': {'aperture': 'f/11'}},
        {'destination': 'asset', 'asset': 'AS'},
        {'constants': {'unit': 'cm'}},
        {'variables': {'aperture': 'f/11'}}
    ])
    async def test__check_parameters_without_required_keys(self, payload):
        cols = await entrypoint._check_parameters(payload, skip_required=True)
        assert isinstance(cols, dict)

    @pytest.mark.parametrize("payload, exception_name, error_msg", [
        # ({"a": 1}, KeyError,
        #  "{'name', 'type', 'destination', 'description'} required keys are missing in request payload.")
        ({"name": 1}, ValueError, "Control entrypoint name should be in string."),
        ({"name": ""}, ValueError, "Control entrypoint name cannot be empty."),
        ({"description": 1}, ValueError, "Control entrypoint description should be in string."),
        ({"description": ""}, ValueError, "Control entrypoint description cannot be empty."),
        ({"type": 1}, ValueError, "Control entrypoint type should be in string."),
        ({"type": ""}, ValueError, "Control entrypoint type cannot be empty."),
        ({"type": "Blah"}, ValueError, "Possible types are: ['write', 'operation']."),
        ({"type": "operation"}, KeyError, "operation_name KV pair is missing."),
        ({"type": "operation", "operation_name": ""}, ValueError, "Control entrypoint operation name cannot be empty."),
        ({"type": "operation", "operation_name": 1}, ValueError,
         "Control entrypoint operation name should be in string."),
        ({"destination": ""}, ValueError, "Control entrypoint destination cannot be empty."),
        ({"destination": 1}, ValueError, "Control entrypoint destination should be in string."),
        ({"destination": "Blah"}, ValueError,
         "Possible destination values are: ['broadcast', 'service', 'asset', 'script']."),
        ({"destination": "script", "destination_arg": ""}, KeyError, "script destination argument is missing."),
        ({"destination": "script", "script": 1}, ValueError,
         "Control entrypoint destination argument should be in string."),
        ({"destination": "script", "script": ""}, ValueError,
         "Control entrypoint destination argument cannot be empty."),
        ({"anonymous": "t"}, ValueError, "anonymous should be a bool."),
        ({"constants": "t"}, ValueError, "constants should be a dictionary."),
        ({"type": "write", "constants": {}}, ValueError, "constants should not be empty."),
        ({"type": "write", "constants": None}, ValueError,
         "For type write constants must have passed in payload and cannot have empty value."),
        ({"variables": "t"}, ValueError, "variables should be a dictionary."),
        ({"type": "write", "constants": {"unit": "cm"}, "variables": {}}, ValueError, "variables should not be empty."),
        ({"type": "write", "constants": {"unit": "cm"}, "variables": None}, ValueError,
         "For type write variables must have passed in payload and cannot have empty value."),
        ({"allow": "user"}, ValueError, "allow should be an array of list of users.")
    ])
    async def test_bad__check_parameters(self, payload, exception_name, error_msg):
        with pytest.raises(Exception) as exc_info:
            await entrypoint._check_parameters(payload, skip_required=True)
        assert exc_info.type is exception_name
        assert exc_info.value.args[0] == error_msg

    # TODO: add more tests
    """
        a) authentication based
        b) allow
        c) exception handling tests
    """
