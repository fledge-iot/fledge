import asyncio
import json
import sys
from unittest.mock import MagicMock, patch
import pytest
from aiohttp import web

from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.web import middleware
from fledge.services.core import connect
from fledge.services.core import routes

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]


@pytest.allure.feature("unit")
@pytest.allure.story("api", "acl-management")
class TestACLManagement:
    """ ACL API tests """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_all_acls(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {'count': 2, 'rows': [
            {'name': 'demoACL', 'service': [{'name': 'Fledge Storage'}, {'type': 'Southbound'}],
             'url': [{'url': '/fledge/south/operation', 'acl': [{'type': 'Southbound'}]}]},
            {'name': 'testACL', 'service': [], 'url': []}]}
        payload = {"return": ["name", "service", "url"]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/ACL')
                assert 200 == resp.status
                result = await resp.text()
                assert 'acls' in result
            args, _ = patch_query_tbl.call_args
            assert 'control_acl' == args[0]
            assert payload == json.loads(args[1])

    async def test_bad_get_acl_by_name(self, client):
        acl_name = 'blah'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 0, "rows": []}
        payload = {"return": ["name", "service", "url"], "where": {"column": "name", "condition": "=",
                                                                   "value": acl_name}}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        message = "ACL with name {} is not found.".format(acl_name)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/ACL/{}'.format(acl_name))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'control_acl' == args[0]
            assert payload == json.loads(args[1])

    async def test_good_get_acl_by_name(self, client):
        acl_name = 'demoACL'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {'count': 1, 'rows': [
            {'name': acl_name, 'service': [{'name': 'Fledge Storage'}, {'type': 'Southbound'}],
             'url': [{'url': '/fledge/south/operation', 'acl': [{'type': 'Southbound'}]}]}]}
        payload = {"return": ["name", "service", "url"], "where": {"column": "name", "condition": "=",
                                                                   "value": acl_name}}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/ACL/{}'.format(acl_name))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert acl_name == json_response['name']
            args, _ = patch_query_tbl.call_args
            assert 'control_acl' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.parametrize("payload, message", [
        ({}, "ACL name is required."),
        ({"name": 1}, "ACL name must be a string."),
        ({"name": ""}, "ACL name cannot be empty."),
        ({"name": "test"}, "service parameter is required."),
        ({"name": "test", "service": 1}, "service must be a list."),
        ({"name": "test", "service": []}, "url parameter is required."),
        ({"name": "test", "service": [], "url": 1}, "url must be a list.")
    ])
    async def test_bad_add_acl(self, client, payload, message):
        resp = await client.post('/fledge/ACL', data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    async def test_duplicate_add_acl(self, client):
        acl_name = "testACL"
        request_payload = {"name": acl_name, "service": [], "url": []}
        result = {'count': 1, 'rows': [
            {'name': acl_name, 'service': [{'name': 'Fledge Storage'}, {'type': 'Southbound'}],
             'url': [{'url': '/fledge/south/operation', 'acl': [{'type': 'Southbound'}]}]}]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        message = "ACL with name {} already exists.".format(acl_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.post('/fledge/ACL', data=json.dumps(request_payload))
                assert 409 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'control_acl' == args[0]
            assert query_payload == json.loads(args[1])
    
    async def test_good_add_acl(self, client):
        acl_name = "testACL"
        request_payload = {"name": acl_name, "service": [], "url": []}
        result = {"count": 0, "rows": []}
        insert_result = {"response": "inserted", "rows_affected": 1}
        acl_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            insert_value = await mock_coro(insert_result)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            insert_value = asyncio.ensure_future(mock_coro(insert_result))
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=insert_value
                                  ) as insert_tbl_patch:
                    resp = await client.post('/fledge/ACL', data=json.dumps(request_payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'name': acl_name, 'service': [], 'url': []} == json_response
                args, _ = insert_tbl_patch.call_args_list[0]
                assert 'control_acl' == args[0]
                assert {'name': acl_name, 'service': '[]', 'url': '[]'} == json.loads(args[1])
            args, _ = query_tbl_patch.call_args_list[0]
            assert 'control_acl' == args[0]
            assert acl_query_payload == json.loads(args[1])

    @pytest.mark.parametrize("payload, message", [
        ({}, "Nothing to update for the given payload."),
        ({"service": 1}, "service must be a list."),
        ({"url": 1}, "url must be a list.")
    ])
    async def test_bad_update_acl(self, client, payload, message):
        acl_name = "testACL"
        resp = await client.put('/fledge/ACL/{}'.format(acl_name), data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    async def test_update_acl_not_found(self, client):
        acl_name = "testACL"
        req_payload = {"service": []}
        result = {"count": 0, "rows": []}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        message = "ACL with name {} is not found.".format(acl_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.put('/fledge/ACL/{}'.format(acl_name), data=json.dumps(req_payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'control_acl' == args[0]
            assert query_payload == json.loads(args[1])

    @pytest.mark.parametrize("payload", [
        {"service": []},
        {"service": [{"service": [{"name": "Sinusoid"}, {"type": "Southbound"}]}]},
        {"service": [], "url": []},
        {"service": [], "url": [{"url": "/fledge/south/operation", "acl": [{"type": "Southbound"}]}]},
        {"service": [{"service": [{"name": "Sinusoid"}, {"type": "Southbound"}]}],
         "url": [{"url": "/fledge/south/operation", "acl": [{"type": "Southbound"}]}]}
    ])
    async def test_update_acl(self, client, payload):
        acl_name = "testACL"
        acl_q_result = {"count": 0, "rows": []}
        update_result = {"response": "updated", "rows_affected": 1}
        query_tbl_result = {"count": 1, "rows": [{"name": acl_name, "service": [], "url": []}]}
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(query_tbl_result)
            update_value = await mock_coro(update_result)
        else:
            rv = asyncio.ensure_future(mock_coro(query_tbl_result))
            update_value = asyncio.ensure_future(mock_coro(update_result))
        storage_client_mock = MagicMock(StorageClientAsync)
        acl_query_payload_service = {"return": ["entity_name"], "where": {"column": "entity_type",
                                                                          "condition": "=",
                                                                          "value": "service",
                                                                          "and":
                                                                              {"column": "name",
                                                                               "condition": "=",
                                                                               "value": "{}".format(acl_name)}}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            if table == 'acl_usage':
                assert acl_query_payload_service == json.loads(args[1])
                return acl_q_result
            elif table == 'control_acl':
                assert query_payload == json.loads(args[1])
                return query_tbl_result
            else:
                return {}

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result) as patch_query_tbl:
                with patch.object(storage_client_mock, 'update_tbl', return_value=update_value) as patch_update_tbl:
                    resp = await client.put('/fledge/ACL/{}'.format(acl_name), data=json.dumps(payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": "ACL {} updated successfully.".format(acl_name)} == json_response
                update_args, _ = patch_update_tbl.call_args
                assert 'control_acl' == update_args[0]

    async def test_delete_acl_not_found(self, client):
        acl_name = "test"
        result = {"count": 0, "rows": []}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        message = "ACL with name {} is not found.".format(acl_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.delete('/fledge/ACL/{}'.format(acl_name))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'control_acl' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_delete_acl(self, client):
        acl_name = 'demoACL'
        storage_client_mock = MagicMock(StorageClientAsync)
        acl_q_result = {"count": 0, "rows": []}
        result = {"count": 1, "rows": [{"name": acl_name, "service": [], "url": []}]}
        payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        delete_payload = {"where": {"column": "name", "condition": "=", "value": acl_name}}
        delete_result = {"response": "deleted", "rows_affected": 1}
        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            del_value = await mock_coro(delete_result)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            del_value = asyncio.ensure_future(mock_coro(delete_result))

        acl_query_payload_service = {"return": ["entity_name"], "where": {"column": "entity_type",
                                                                          "condition": "=",
                                                                          "value": "service",
                                                                          "and":
                                                                              {"column": "name",
                                                                               "condition": "=",
                                                                               "value": "{}".format(acl_name)}}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            if table == 'acl_usage':
                assert acl_query_payload_service == json.loads(args[1])
                return acl_q_result
            elif table == 'control_acl':
                assert payload == json.loads(args[1])
                return result
            else:
                return {}

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result) as query_tbl_patch:
                with patch.object(storage_client_mock, 'delete_from_tbl', return_value=del_value) as patch_delete_tbl:
                    resp = await client.delete('/fledge/ACL/{}'.format(acl_name))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'message': '{} ACL deleted successfully.'.format(acl_name)} == json_response
                delete_args, _ = patch_delete_tbl.call_args
                assert 'control_acl' == delete_args[0]
                assert delete_payload == json.loads(delete_args[1])

    async def test_bad_service_with_acl(self, client):
        svc_name = 'foo'
        result = {"count": 0, "rows": []}
        payload = {"acl_name": "testACL"}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        storage_client_mock = MagicMock(StorageClientAsync)
        message = "Schedule with name {} is not found.".format(svc_name)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.put('/fledge/service/{}/ACL'.format(svc_name), data=json.dumps(payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {'message': message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'schedules' == args[0]
            assert {"where": {"column": "schedule_name", "condition": "=", "value": svc_name}} == json.loads(args[1])

    @pytest.mark.parametrize("payload, message", [
        ({}, 'acl_name KV pair is missing.'),
        ({"acl_name": 1}, 'ACL must be a string.'),
        ({"acl_name": ""}, 'ACL cannot be empty.'),
    ])
    async def test_bad_attach_acl_to_service(self, client, payload, message):
        svc_name = 'foo'
        result = {"count": 1, "rows": [{"id": "3e84f179-874d-4a91-a524-15512172f8a2", "enabled": "true"}]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.put('/fledge/service/{}/ACL'.format(svc_name), data=json.dumps(payload))
                assert 400 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {'message': message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'schedules' == args[0]
            assert {"where": {"column": "schedule_name", "condition": "=", "value": svc_name}} == json.loads(args[1])

    async def test_acl_not_found_when_attach_to_service(self, client):
        svc_name = 'foo'
        acl_name = "testACL"
        req_payload = {"acl_name": acl_name}
        acl_result = {"count": 0, "rows": []}
        acl_query_payload = {"return": ["name", "service", "url"], "where": {"column": "name", "condition": "=",
                                                                             "value": acl_name}}
        sch_query_payload = {"where": {"column": "schedule_name", "condition": "=", "value": svc_name}}
        sch_result = {"count": 1, "rows": [{"id": "3e84f179-874d-4a91-a524-15512172f8a2", "enabled": "true"}]}
        message = "ACL with name {} is not found.".format(acl_name)

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            if table == 'schedules':
                assert sch_query_payload == json.loads(args[1])
                return sch_result
            elif table == 'control_acl':
                assert acl_query_payload == json.loads(args[1])
                return acl_result
            else:
                return {}

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                resp = await client.put('/fledge/service/{}/ACL'.format(svc_name), data=json.dumps(req_payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {'message': message} == json_response

    async def test_service_already_attached_to_acl(self, client):
        svc_name = 'foo'
        acl_name = "testACL"
        req_payload = {"acl_name": acl_name}
        acl_result = {"count": 1, "rows": [{"name": acl_name, "service": [], "url": []}]}
        acl_query_payload = {"return": ["name", "service", "url"], "where": {"column": "name", "condition": "=",
                                                                             "value": acl_name}}
        sch_query_payload = {"where": {"column": "schedule_name", "condition": "=", "value": svc_name}}
        sch_result = {"count": 1, "rows": [{"id": "3e84f179-874d-4a91-a524-15512172f8a2", "enabled": "true"}]}
        message = "Service {} already has an ACL object.".format(svc_name, acl_name)

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            if table == 'schedules':
                assert sch_query_payload == json.loads(args[1])
                return sch_result
            elif table == 'control_acl':
                assert acl_query_payload == json.loads(args[1])
                return acl_result
            else:
                return {}

        cat_info = {
                        "AuthenticatedCaller": {"description": "Caller authorisation is needed", "type": "boolean",
                                                "default": "false", "displayName": "Enable caller authorisation",
                                                "value": "false"},
                        "ACL": {
                            "description": "Service ACL for {}".format(svc_name), "type": "JSON",
                            "displayName": "Service ACL", "default": "[]", "value": "[]"
                        }
                }
        cat_value = await mock_coro(cat_info) if sys.version_info >= (3, 8) else \
            asyncio.ensure_future(mock_coro(cat_info))
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(c_mgr, 'get_category_all_items', return_value=cat_value) as patch_get_all_items:
                    resp = await client.put('/fledge/service/{}/ACL'.format(svc_name), data=json.dumps(req_payload))
                    assert 400 == resp.status
                    assert message == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'message': message} == json_response
                patch_get_all_items.assert_called_once_with("{}Security".format(svc_name))

    async def test_good_attach_acl_to_service(self, client):
        svc_name = 'foo'
        acl_name = "testACL"
        req_payload = {"acl_name": acl_name}
        acl_result = {"count": 1, "rows": [{"name": acl_name, "service": [], "url": []}]}
        acl_query_payload = {"return": ["name", "service", "url"], "where": {"column": "name", "condition": "=",
                                                                             "value": acl_name}}
        sch_query_payload = {"where": {"column": "schedule_name", "condition": "=", "value": svc_name}}
        sch_result = {"count": 1, "rows": [{"id": "3e84f179-874d-4a91-a524-15512172f8a2", "enabled": "true"}]}
        security_cat_name = "{}Security".format(svc_name)
        cat_child_result = {"children": [security_cat_name]}
        message = "ACL with name {} attached to {} service successfully.".format(acl_name, svc_name)

        acl_dict = {'ACL': acl_name}
        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            if table == 'schedules':
                assert sch_query_payload == json.loads(args[1])
                return sch_result
            elif table == 'control_acl':
                assert acl_query_payload == json.loads(args[1])
                return acl_result
            else:
                return {}

        if sys.version_info >= (3, 8):
            cat_value = await mock_coro(None)
            cat_child_value = await mock_coro(cat_child_result)
            update_bulk_value = await mock_coro(None)
        else:
            cat_value = asyncio.ensure_future(mock_coro(None))
            cat_child_value = asyncio.ensure_future(mock_coro(cat_child_result))
            update_bulk_value = asyncio.ensure_future(mock_coro(None))

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(c_mgr, 'get_category_all_items', return_value=cat_value) as patch_get_all_items:
                    with patch.object(c_mgr, 'create_category', return_value=cat_value) as patch_create_cat:
                        with patch.object(c_mgr, 'create_child_category',
                                          return_value=cat_child_value) as patch_create_child_cat:
                            with patch.object(c_mgr, 'update_configuration_item_bulk',
                                              return_value=update_bulk_value) as patch_update_bulk:
                                resp = await client.put('/fledge/service/{}/ACL'.format(svc_name),
                                                        data=json.dumps(req_payload))
                                assert 200 == resp.status
                                result = await resp.text()
                                json_response = json.loads(result)
                                assert {'message': message} == json_response
                            patch_update_bulk.assert_called_once_with(security_cat_name, acl_dict)
                        patch_create_child_cat.assert_called_once_with(svc_name, [security_cat_name])
                        patch_create_cat.assert_called()
                patch_get_all_items.assert_called_once_with(security_cat_name)

    async def test_bad_detach_acl_from_service(self, client):
        svc_name = 'foo'
        result = {"count": 0, "rows": []}
        payload = {"acl_name": "testACL"}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        storage_client_mock = MagicMock(StorageClientAsync)
        message = "Schedule with name {} is not found.".format(svc_name)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.delete('/fledge/service/{}/ACL'.format(svc_name), data=json.dumps(payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {'message': message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'schedules' == args[0]
            assert {"where": {"column": "schedule_name", "condition": "=", "value": svc_name}} == json.loads(args[1])

    async def test_no_acl_detach_from_service(self, client):
        svc_name = 'foo'
        sch_query_payload = {"where": {"column": "schedule_name", "condition": "=", "value": svc_name}}
        sch_result = {"count": 1, "rows": [{"id": "3e84f179-874d-4a91-a524-15512172f8a2", "enabled": "true"}]}
        message = "Nothing to delete as there is no ACL attached with {} service.".format(svc_name)
        if sys.version_info >= (3, 8):
            cat_value = await mock_coro(None)
            sch_value = await mock_coro(sch_result)
        else:
            cat_value = asyncio.ensure_future(mock_coro(None))
            sch_value = asyncio.ensure_future(mock_coro(sch_result))
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=sch_value) as patch_query_tbl:
                with patch.object(c_mgr, 'get_category_all_items', return_value=cat_value) as patch_get_all_items:
                    resp = await client.delete('/fledge/service/{}/ACL'.format(svc_name))
                    assert 400 == resp.status
                    assert message == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'message': message} == json_response
                patch_get_all_items.assert_called_once_with("{}Security".format(svc_name))
            args, _ = patch_query_tbl.call_args
            assert 'schedules' == args[0]
            assert sch_query_payload == json.loads(args[1])

    async def test_good_detach_acl_from_service(self, client):
        svc_name = 'foo'
        expected_result = {
                    "AuthenticatedCaller": {
                        "description": "Caller authorisation is needed",
                        "type": "boolean",
                        "default": "false",
                        "displayName": "Enable caller authorisation",
                    },
                    'ACL': {
                        'description': 'Service ACL for {}'.format(svc_name),
                        'type': 'ACL',
                        'displayName': 'Service ACL',
                        'default': ''}
            }
        security_cat = "{}Security".format(svc_name)
        sch_query_payload = {"where": {"column": "schedule_name", "condition": "=", "value": svc_name}}
        sch_result = {"count": 1, "rows": [{"id": "3e84f179-874d-4a91-a524-15512172f8a2", "enabled": "true"}]}
        cat_result = {"a": 1}
        message = "ACL is detached from {} service successfully.".format(svc_name)
        acl_dict = {'ACL': ''}

        if sys.version_info >= (3, 8):
            cat_value = await mock_coro(cat_result)
            sch_value = await mock_coro(sch_result)
            update_bulk_value = await mock_coro(None)
        else:
            cat_value = asyncio.ensure_future(mock_coro(cat_result))
            sch_value = asyncio.ensure_future(mock_coro(sch_result))
            update_bulk_value = asyncio.ensure_future(mock_coro(None))
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=sch_value) as patch_query_tbl:
                with patch.object(c_mgr, 'get_category_all_items', return_value=cat_value) as patch_get_all_items:
                    with patch.object(c_mgr, 'create_category', return_value=cat_value) as patch_create_cat:
                        with patch.object(c_mgr, 'update_configuration_item_bulk',
                                          return_value=update_bulk_value) as patch_update_bulk:
                            resp = await client.delete('/fledge/service/{}/ACL'.format(svc_name))
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert {'message': message} == json_response
                        patch_update_bulk.assert_called_once_with(security_cat, acl_dict)
                    patch_create_cat.assert_called_once_with(category_description='Security category for foo service',
                                                             category_name=security_cat,
                                                             category_value=expected_result)
                patch_get_all_items.assert_called_once_with(security_cat)
            args, _ = patch_query_tbl.call_args
            assert 'schedules' == args[0]
            assert sch_query_payload == json.loads(args[1])
