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
    """ Control Flow Entrypoint API tests"""

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
        with patch.object(entrypoint, '_get_entrypoint', return_value=rv1):
            with patch.object(entrypoint, '_get_permitted', return_value=rv2):
                resp = await client.get('/fledge/control/manage/{}'.format(ep_name))
                assert 200 == resp.status
                json_response = json.loads(await resp.text())
                assert 'permitted' in json_response
                assert storage_result == json_response

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
                # allow is empty in given payload
                # TODO: in future
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
                with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=i_result):
                    with patch.object(AuditLogger, '__init__', return_value=None):
                        with patch.object(AuditLogger, 'information', return_value=arv) as audit_info_patch:
                            resp = await client.post('/fledge/control/manage', data=json.dumps(payload))
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert {'message': '{} control entrypoint has been created successfully.'.format(ep_name)
                                    } == json_response
                        audit_info_patch.assert_called_once_with('CTEAD', payload)
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
