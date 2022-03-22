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
from fledge.services.core import server
from fledge.services.core.scheduler.scheduler import Scheduler

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]


@pytest.allure.feature("unit")
@pytest.allure.story("api", "script-management")
class TestScriptManagement:
    """ Automation script API tests
    """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_all_scripts(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 2, "rows": [
            {"name": "demoScript", "steps": [{"delay": {"order": 0, "duration": 9003}}], "acl": ""},
            {"name": "testScript", "steps": [{"write": {"order": 0, "speed": 420}}], "acl": "testACL"}]}
        payload = {"return": ["name", "steps", "acl"]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/control/script')
                assert 200 == resp.status
                result = await resp.text()
                assert 'scripts' in result
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert payload == json.loads(args[1])

    async def test_bad_get_script_by_name(self, client):
        script_name = 'blah'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 0, "rows": []}
        payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=", "value": "blah"}}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        message = "Script with name {} is not found.".format(script_name)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/control/script/{}'.format(script_name))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert payload == json.loads(args[1])

    async def test_good_get_script_by_name(self, client):
        script_name = 'demoScript'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 0, "rows": [
            {"name": script_name, "steps": [{"delay": {"order": 0, "duration": 9003}}], "acl": ""}]}
        payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=",
                                                                 "value": script_name}}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/control/script/{}'.format(script_name))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert script_name == json_response['name']
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.parametrize("payload, message", [
        ({}, "Script name is required."),
        ({"name": 1}, "Script name must be a string."),
        ({"name": ""}, "Script name cannot be empty."),
        ({"name": "test"}, "steps parameter is required."),
        ({"name": "test", "steps": 1}, "steps must be a list."),
        ({"name": "test", "steps": [], "acl": 1}, "ACL name must be a string."),
        ({"name": "test", "steps": [{"a": 1}]}, "a is an invalid step. Supported step types are ['configure', 'delay', "
                                                "'operation', 'script', 'write'] with case-sensitive."),
        ({"name": "test", "steps": [1, 2]}, "Steps should be in list of dictionaries."),
        ({"name": "test", "steps": [{"delay": 1}]}, "For delay step nested elements should be in dictionary."),
        ({"name": "test", "steps": [{"delay": {}}]}, "order key is missing for delay step."),
        ({"name": "test", "steps": [{"delay": {"order": "1"}}]}, "order should be an integer for delay step."),
        ({"name": "test", "steps": [{"delay": {"order": 1}, "write": {}}]}, "order key is missing for write step."),
        ({"name": "test", "steps": [{"delay": {"order": 1}, "write": {"order": "1"}}]},
         "order should be an integer for write step."),
        ({"name": "test", "steps": [{"delay": {"order": 1}, "write": {"order": 1}}]},
         "order with value 1 is also found in write. It should be unique for each step item.")
    ])
    async def test_bad_add_script(self, client, payload, message):
        resp = await client.post('/fledge/control/script', data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    async def test_duplicate_add_script(self, client):
        script_name = "test"
        request_payload = {"name": script_name, "steps": []}
        result = {"count": 1, "rows": [{"name": script_name, "steps": [{"write": {"order": 1, "speed": 420}}]}]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        message = "Script with name {} already exists.".format(script_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                assert 409 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_bad_add_script_with_acl(self, client):
        script_name = "test"
        acl_name = "blah"
        request_payload = {"name": script_name, "steps": [], "acl": acl_name}
        script_result = {"count": 0, "rows": []}
        acl_result = {"count": 0, "rows": []}
        script_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        acl_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_acl':
                assert acl_query_payload == json.loads(payload)
                return script_result
            elif table == 'control_script':
                assert script_query_payload == json.loads(payload)
                return acl_result
            else:
                return {}

        message = "ACL with name {} is not found.".format(acl_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response

    async def test_good_add_script(self, client):
        script_name = "test"
        request_payload = {"name": script_name, "steps": []}
        result = {"count": 0, "rows": []}
        insert_result = {"response": "inserted", "rows_affected": 1}
        script_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
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
                    resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'name': script_name, 'steps': []} == json_response
                args, _ = insert_tbl_patch.call_args_list[0]
                assert 'control_script' == args[0]
                expected = json.loads(args[1])
                assert {'name': script_name, 'steps': '[]'} == expected
            args, _ = query_tbl_patch.call_args_list[0]
            assert 'control_script' == args[0]
            expected = json.loads(args[1])
            assert script_query_payload == expected

    async def test_good_add_script_with_acl(self, client):
        script_name = "test"
        acl_name = "blah"
        request_payload = {"name": script_name, "steps": [], "acl": acl_name}
        script_result = {"count": 0, "rows": []}
        acl_result = {"count": 1, "rows": [{"name": acl_name, "service": [], "url": []}]}
        insert_result = {"response": "inserted", "rows_affected": 1}
        script_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        acl_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        insert_value = await mock_coro(insert_result) if sys.version_info >= (3, 8) else \
            asyncio.ensure_future(mock_coro(insert_result))

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_acl':
                assert acl_query_payload == json.loads(payload)
                return acl_result
            elif table == 'control_script':
                assert script_query_payload == json.loads(payload)
                return script_result
            else:
                return {}

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=insert_value
                                  ) as insert_tbl_patch:
                    resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'acl': acl_name, 'name': script_name, 'steps': []} == json_response
                insert_args, _ = insert_tbl_patch.call_args_list[0]
                assert 'control_script' == insert_args[0]
                expected = json.loads(insert_args[1])
                assert {'name': script_name, 'steps': '[]', 'acl': acl_name} == expected

    @pytest.mark.parametrize("payload, message", [
        ({}, "Nothing to update for the given payload."),
        ({"steps": 1}, "steps must be a list."),
        ({"acl": 1}, "ACL must be a string."),
        ({"steps": [{"a": 1}]}, "a is an invalid step. Supported step types are "
                                "['configure', 'delay', 'operation', 'script', 'write'] with case-sensitive."),
        ({"steps": [1, 2]}, "Steps should be in list of dictionaries."),
        ({"steps": [{"delay": 1}]}, "For delay step nested elements should be in dictionary."),
        ({"steps": [{"delay": {}}]}, "order key is missing for delay step."),
        ({"steps": [{"delay": {"order": "1"}}]}, "order should be an integer for delay step."),
        ({"steps": [{"delay": {"order": 1}, "write": {}}]}, "order key is missing for write step."),
        ({"steps": [{"delay": {"order": 1}, "write": {"order": "1"}}]},
         "order should be an integer for write step."),
        ({"steps": [{"delay": {"order": 1}, "write": {"order": 1}}]},
         "order with value 1 is also found in write. It should be unique for each step item.")
    ])
    async def test_bad_update_script(self, client, payload, message):
        script_name = "testScript"
        resp = await client.put('/fledge/control/script/{}'.format(script_name), data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    async def test_update_script_not_found(self, client):
        script_name = "test"
        req_payload = {"steps": []}
        result = {"count": 0, "rows": []}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        message = "No such {} script found.".format(script_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.put('/fledge/control/script/{}'.format(script_name), data=json.dumps(req_payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_update_script_when_acl_not_found(self, client):
        script_name = "test"
        acl_name = "blah"
        payload = {"steps": [{"write": {"order": 1, "speed": 420}}], "acl": acl_name}
        script_result = {"count": 1, "rows": [{"name": script_name, "steps": [{"write": {"order": 1, "speed": 420}}]}]}
        script_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        acl_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        acl_result = {"count": 0, "rows": []}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            if table == 'control_acl':
                assert acl_query_payload == json.loads(args[1])
                return acl_result
            elif table == 'control_script':
                assert script_query_payload == json.loads(args[1])
                return script_result
            else:
                return {}

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                resp = await client.put('/fledge/control/script/{}'.format(script_name), data=json.dumps(payload))
                assert 404 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": "ACL with name {} is not found.".format(acl_name)} == json_response

    @pytest.mark.parametrize("payload", [
        {"steps": []},
        {"steps": [], "acl": ""},
        {"steps": [], "acl": "testACL"}
    ])
    async def test_update_script(self, client, payload):
        script_name = "test"
        acl_name = "testACL"
        script_result = {"count": 1, "rows": [{"name": script_name, "steps": [{"write": {"order": 1, "speed": 420}}]}]}
        update_result = {"response": "updated", "rows_affected": 1}
        steps_payload = payload["steps"]
        update_value = await mock_coro(update_result) if sys.version_info >= (3, 8) else \
            asyncio.ensure_future(mock_coro(update_result))
        script_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        acl_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        acl_result = {"count": 1, "rows": [{"name": acl_name, "service": [], "url": []}]}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            if table == 'control_acl':
                assert acl_query_payload == json.loads(args[1])
                return acl_result
            elif table == 'control_script':
                assert script_query_payload == json.loads(args[1])
                return script_result
            else:
                return {}

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'update_tbl', return_value=update_value) as patch_update_tbl:
                    resp = await client.put('/fledge/control/script/{}'.format(script_name), data=json.dumps(payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": "Control script {} updated successfully.".format(script_name)} == json_response
                update_args, _ = patch_update_tbl.call_args
                assert 'control_script' == update_args[0]
                update_payload = {"values": payload, "where": {"column": "name", "condition": "=",
                                                               "value": script_name}}
                update_payload["values"]["steps"] = str(steps_payload)
                assert update_payload == json.loads(update_args[1])

    async def test_delete_script_not_found(self, client):
        script_name = "test"
        req_payload = {"steps": []}
        result = {"count": 0, "rows": []}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        message = "No such {} script found.".format(script_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.delete('/fledge/control/script/{}'.format(script_name),
                                           data=json.dumps(req_payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_delete_script(self, client):
        script_name = 'demoScript'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 0, "rows": [
            {"name": script_name, "steps": [{"delay": {"order": 0, "duration": 9003}}], "acl": ""}]}
        payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        delete_payload = {"where": {"column": "name", "condition": "=", "value": script_name}}
        delete_result = {"response": "deleted", "rows_affected": 1}
        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            del_value = await mock_coro(delete_result)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            del_value = asyncio.ensure_future(mock_coro(delete_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                with patch.object(storage_client_mock, 'delete_from_tbl', return_value=del_value) as patch_delete_tbl:
                    resp = await client.delete('/fledge/control/script/{}'.format(script_name))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'message': '{} script deleted successfully.'.format(script_name)} == json_response
                delete_args, _ = patch_delete_tbl.call_args
                assert 'control_script' == delete_args[0]
                assert delete_payload == json.loads(delete_args[1])
            args, _ = query_tbl_patch.call_args
            assert 'control_script' == args[0]
            assert payload == json.loads(args[1])

    async def test_schedule_script_not_found(self, client):
        script_name = "test"
        req_payload = {"steps": []}
        result = {"count": 0, "rows": []}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=",
                                                                       "value": script_name}}
        message = "Script with name {} is not found.".format(script_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.post('/fledge/control/script/{}/schedule'.format(script_name),
                                         data=json.dumps(req_payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_schedule_script(self, client):
        script_name = 'demoScript'
        result = {"count": 0, "rows": [{"name": script_name, "steps": [
            {"write": {"order": 0, "service": "sine", "values": {"sinusoid": "1.2"}}}], "acl": ""}]}
        cat_child_result = {'children': ['DispatcherAdvanced', script_name]}
        server.Server.scheduler = Scheduler(None, None)
        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            sch = await mock_coro("")
            queue = await mock_coro(True)
            cat = await mock_coro(None)
            child = await mock_coro(cat_child_result)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            sch = asyncio.ensure_future(mock_coro(""))
            queue = asyncio.ensure_future(mock_coro(True))
            cat = asyncio.ensure_future(mock_coro(None))
            child = asyncio.ensure_future(mock_coro(cat_child_result))
        query_payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=",
                                                                       "value": script_name}}
        message = "Schedule and configuration is created for an automation script with name {}".format(script_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                with patch.object(server.Server.scheduler, 'save_schedule', return_value=sch) as patch_save_schedule:
                    with patch.object(server.Server.scheduler, 'queue_task', return_value=queue) as patch_queue_task:
                        with patch.object(c_mgr, 'create_category', return_value=cat) as patch_create_cat:
                            with patch.object(c_mgr, 'create_child_category', return_value=child) \
                                    as patch_create_child_cat:
                                resp = await client.post('/fledge/control/script/{}/schedule'.format(script_name))
                                assert 200 == resp.status
                                result = await resp.text()
                                json_response = json.loads(result)
                                assert {"message": message} == json_response
                            patch_create_child_cat.assert_called_once_with('Dispatcher', [script_name])
                        assert 1 == patch_create_cat.call_count
                    patch_queue_task.assert_called_once_with(None)
                patch_save_schedule.assert_called_once()
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])
