import asyncio
import json
import sys
import uuid

from unittest.mock import MagicMock, patch
import pytest
from aiohttp import web

from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.web import middleware
from fledge.services.core import connect
from fledge.services.core import routes
from fledge.services.core import server
from fledge.services.core.scheduler.entities import ManualSchedule
from fledge.services.core.scheduler.scheduler import Scheduler

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]


async def mock_schedule(name):
    schedules = []
    schedule = ManualSchedule()
    schedule.repeat = None
    schedule.time = None
    schedule.day = None
    schedule.schedule_id = "0c6fbbfd-8b36-4d6d-8fcb-5389436aa0fe"
    schedule.exclusive = True
    schedule.enabled = True
    schedule.name = name
    schedule.process_name = "automation_script"
    schedules.append(schedule)
    return schedules


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
        c_mgr = ConfigurationManager(storage_client_mock)
        server.Server.scheduler = Scheduler(None, None)
        acl_name = "testACL"
        script_name = "demoScript"
        cat_name = "{}-automation-script".format(script_name)
        result = {"count": 1, "rows": [
            {"name": script_name, "steps": [{"write": {"order": 0, "service": "mod", "values": {"humidity": "12"}}}],
             "acl": acl_name, "configuration": {}, "schedule": {}}]}
        payload = {"return": ["name", "steps", "acl"]}
        cat_info = {'write': {'default': '[{"order": 0, "service": "mod", "values": {"humidity": "12"}}]',
                              'description': 'Dispatcher write operation using automation script', 'type': 'string',
                              'value': '[{"order": 0, "service": "mod", "values": {"humidity": "12"}}]'}}
        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            get_sch = await mock_schedule(script_name)
            get_cat = await mock_coro(cat_info)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            get_sch = asyncio.ensure_future(mock_schedule(script_name))
            get_cat = asyncio.ensure_future(mock_coro(cat_info))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                with patch.object(server.Server.scheduler, 'get_schedules',
                                  return_value=get_sch) as patch_get_schedules:
                    with patch.object(c_mgr, 'get_category_all_items', return_value=get_cat) as patch_get_all_items:
                        resp = await client.get('/fledge/control/script')
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert 'scripts' in json_response
                        assert 'acl' in json_response['scripts'][0]
                        assert acl_name == json_response['scripts'][0]['acl']
                        assert 'configuration' in json_response['scripts'][0]
                        assert len(json_response['scripts'][0]['configuration'])
                        assert cat_name == json_response['scripts'][0]['configuration']['categoryName']
                        assert 'schedule' in json_response['scripts'][0]
                        assert len(json_response['scripts'][0]['schedule'])
                        assert script_name == json_response['scripts'][0]['schedule']['name']
                        assert "automation_script" == json_response['scripts'][0]['schedule']['processName']
                    patch_get_all_items.assert_called_once_with(cat_name)
                patch_get_schedules.assert_called_once_with()
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
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        server.Server.scheduler = Scheduler(None, None)
        script_name = 'demoScript'
        cat_name = "{}-automation-script".format(script_name)
        result = {"count": 1, "rows": [{"name": script_name, "steps": [
            {"write": {"order": 0, "service": "mod", "values": {"humidity": "12"}}}], "acl": ""}]}
        payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=",
                                                                 "value": script_name}}
        cat_info = {'write': {'default': '[{"order": 0, "service": "mod", "values": {"humidity": "12"}}]',
                              'description': 'Dispatcher write operation using automation script', 'type': 'string',
                              'value': '[{"order": 0, "service": "mod", "values": {"humidity": "12"}}]'}}

        async def mock_manual_schedule(name):
            schedule = ManualSchedule()
            schedule.repeat = None
            schedule.time = None
            schedule.day = None
            schedule.schedule_id = "0c6fbbfd-8b36-4d6d-8fcb-5389436aa0fe"
            schedule.exclusive = True
            schedule.enabled = True
            schedule.name = name
            schedule.process_name = "automation_script"
            return schedule

        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            get_cat = await mock_coro(cat_info)
            get_sch = await mock_manual_schedule(script_name)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            get_cat = asyncio.ensure_future(mock_coro(cat_info))
            get_sch = asyncio.ensure_future(mock_manual_schedule(script_name))

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                with patch.object(c_mgr, 'get_category_all_items', return_value=get_cat) as patch_get_all_items:
                    with patch.object(server.Server.scheduler, 'get_schedule_by_name',
                                      return_value=get_sch) as patch_get_schedule_by_name:
                        resp = await client.get('/fledge/control/script/{}'.format(script_name))
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert script_name == json_response['name']
                        assert 'acl' in json_response
                        assert "" == json_response['acl']
                        assert 'configuration' in json_response
                        assert len(json_response['configuration'])
                        assert cat_name == json_response['configuration']['categoryName']
                        assert 'schedule' in json_response
                        assert len(json_response['schedule'])
                        assert script_name == json_response['schedule']['name']
                        assert "automation_script" == json_response['schedule']['processName']
                    patch_get_schedule_by_name.assert_called_once_with(script_name)
                patch_get_all_items.assert_called_once_with(cat_name)
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
            elif table == "acl_usage":
                return {"count": 0, "rows": []}
            else:
                return {}

        @asyncio.coroutine
        def i_result(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_script':
                assert {'name': script_name, 'steps': '[]', 'acl': acl_name} == json.loads(payload)
                return insert_result
            elif table == "acl_usage":
                assert {'name': acl_name, 'entity_type': 'script',
                        'entity_name': script_name} == json.loads(payload)
                return insert_result

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=i_result
                                  ) as insert_tbl_patch:
                    resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                    assert 200 == resp.status

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
        insert_result = {"response": "inserted", "rows_affected": 1}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            if table == 'control_acl':
                assert acl_query_payload == json.loads(args[1])
                return acl_result
            elif table == 'control_script':
                assert script_query_payload == json.loads(args[1])
                return script_result
            elif table == "acl_usage":
                return {"count": 0, "rows": []}
            else:
                return {}

        @asyncio.coroutine
        def i_result(*args):
            table = args[0]
            payload_ins = args[1]
            if table == "acl_usage":
                assert {'name': acl_name, 'entity_type': 'script',
                        'entity_name': script_name} == json.loads(payload_ins)
                return insert_result

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'update_tbl', return_value=update_value) as patch_update_tbl:
                    with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=i_result):
                        resp = await client.put('/fledge/control/script/{}'.format(script_name),
                                                data=json.dumps(payload))
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert {"message": "Control script {} updated successfully.".format(script_name)}\
                               == json_response
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

    async def test_delete_script_along_with_category_and_schedule(self, client):
        script_name = 'demoScript'
        schedule_cat_name = "{}-automation-script".format(script_name)
        schedule_id = "0c6fbbfd-8b36-4d6d-8fcb-5389436aa0fe"
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        q_result = {"count": 0, "rows": [
            {"name": script_name, "steps": [{"delay": {"order": 0, "duration": 9003}}], "acl": ""}]}
        q_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        delete_payload = {"where": {"column": "name", "condition": "=", "value": script_name}}
        delete_result = {"response": "deleted", "rows_affected": 1}
        disable_sch_result = (True, "Schedule successfully disabled")
        delete_sch_result = (True, 'Schedule deleted successfully.')
        message = '{} script deleted successfully.'.format(script_name)

        @asyncio.coroutine
        def query_schedule(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_script':
                assert q_payload == json.loads(payload)
                return q_result
            elif table == "acl_usage":
                return {"count": 0, "rows": []}

        @asyncio.coroutine
        def d_schedule(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_script':
                assert delete_payload == json.loads(payload)
                return delete_result
            elif table == "acl_usage":
                return delete_result

        if sys.version_info >= (3, 8):
            del_cat_and_child = await mock_coro(delete_result)
            get_sch = await mock_schedule(script_name)
            disable_sch = await mock_coro(disable_sch_result)
            delete_sch = await mock_coro(delete_sch_result)
        else:
            del_cat_and_child = asyncio.ensure_future(mock_coro(delete_result))
            get_sch = asyncio.ensure_future(mock_schedule(script_name))
            disable_sch = asyncio.ensure_future(mock_coro(disable_sch_result))
            delete_sch = asyncio.ensure_future(mock_coro(delete_sch_result))

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'delete_category_and_children_recursively',
                              return_value=del_cat_and_child) as patch_delete_cat_and_child:
                with patch.object(server.Server.scheduler, 'get_schedules',
                                  return_value=get_sch) as patch_get_schedules:
                    with patch.object(server.Server.scheduler, 'disable_schedule',
                                      return_value=disable_sch) as patch_disable_sch:
                        with patch.object(server.Server.scheduler, 'delete_schedule',
                                          return_value=delete_sch) as patch_delete_sch:
                            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                              side_effect=query_schedule) as patch_query_tbl:
                                with patch.object(storage_client_mock, 'delete_from_tbl',
                                                  side_effect=d_schedule) as patch_delete_tbl:
                                    resp = await client.delete('/fledge/control/script/{}'.format(script_name))
                                    assert 200 == resp.status
                                    result = await resp.text()
                                    json_response = json.loads(result)
                                    assert {'message': message} == json_response
                        patch_delete_sch.assert_called_once_with(uuid.UUID(schedule_id))
                    patch_disable_sch.assert_called_once_with(uuid.UUID(schedule_id))
                patch_get_schedules.assert_called_once_with()
            patch_delete_cat_and_child.assert_called_once_with(schedule_cat_name)

    async def test_delete_script_acl_not_attached(self, client):
        script_name = 'demoScript'
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        q_result = {"count": 1, "rows": [
            {"name": script_name, "steps": [{"delay": {"order": 0, "duration": 9003}}], "acl": ""}]}
        q_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        delete_payload = {"where": {"column": "name", "condition": "=", "value": script_name}}
        delete_result = {"response": "deleted", "rows_affected": 1}

        @asyncio.coroutine
        def query_result(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_script':
                assert q_payload == json.loads(payload)
                return q_result
            elif table == "acl_usage":
                return {"count": 0, "rows": []}

        @asyncio.coroutine
        def d_result(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_script':
                assert delete_payload == json.loads(payload)
                return delete_result
            elif table == "acl_usage":
                return delete_result

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'delete_category_and_children_recursively', side_effect=Exception):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  side_effect=query_result) as patch_query_tbl:
                    with patch.object(storage_client_mock, 'delete_from_tbl',
                                      side_effect=d_result) as patch_delete_tbl:
                        resp = await client.delete('/fledge/control/script/{}'.format(script_name))
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert {'message': '{} script deleted successfully.'.format(script_name)} == json_response

    @pytest.mark.parametrize("payload, message", [
        ({}, "parameters field is required."),
        ({"parameters": 1}, "parameters must be a dictionary."),
        ({"parameters": {}}, "parameters cannot be an empty."),
    ])
    async def test_bad_schedule_script_with_parameters(self, client, payload, message):
        resp = await client.post('/fledge/control/script/{}/schedule', data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    @pytest.mark.parametrize("code, message, get_script_result, payload", [
        (404, "Script with name test is not found.", {"count": 0, "rows": []}, None),
        (400, "write steps KV pair is missing for test script.", {"count": 1, "rows": [
            {"name": "test", "steps": [{"delay": {"order": 0, "duration": 9003}}]}]}, {"parameters": {"foobar": 1}}),
        (404, "foo param is not found in write steps for test script.", {"count": 1, "rows": [
            {"name": "test", "steps": [{"write": {"order": 0, "service": "rand",
                                                  "values": {"random": "49", "sine": "$foobar$"}}}]}]},
         {"parameters": {"foo": 1}}),
        (404, "foo param is not found in write steps for test script.", {"count": 1, "rows": [
            {"name": "test", "steps": [{"delay": {"order": 0, "duration": 9003}},
                                       {"write": {"order": 0, "service": "rand", "values": {
                                           "random": "49", "sine": "$foobar$"}}}]}]},
         {"parameters": {"foo": 1}}),
        (404, "bar param is not found in write steps for test script.", {"count": 1, "rows": [
            {"name": "test", "steps": [{"delay": {"order": 0, "duration": 9003}},
                                       {"write": {"order": 0, "service": "rand", "values": {
                                           "random": "$foo$", "sine": "$foobar$"}}}]}]},
         {"parameters": {"foo": "1", "bar": "blah"}}),
        (400, "Value should be in string for foo param.", {"count": 1, "rows": [
            {"name": "test", "steps": [{"delay": {"order": 0, "duration": 9003}},
                                       {"write": {"order": 0, "service": "rand", "values": {
                                           "random": "$foo$", "sine": "$foobar$"}}}]}]},
         {"parameters": {"foo": 1}}),
        (400, "Value should be in string for foobar param.", {"count": 1, "rows": [
            {"name": "test", "steps": [{"delay": {"order": 0, "duration": 9003}},
                                       {"write": {"order": 0, "service": "rand", "values": {
                                           "random": "$foo$", "sine": "$foobar$"}}}]}]},
         {"parameters": {"foo": "1", "foobar": 13}})
    ])
    async def test_schedule_script_not_found(self, client, code, message, get_script_result, payload):
        script_name = "test"
        value = await mock_coro(get_script_result) if sys.version_info >= (3, 8) else \
            asyncio.ensure_future(mock_coro(get_script_result))
        query_payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=",
                                                                       "value": script_name}}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.post('/fledge/control/script/{}/schedule'.format(script_name),
                                         data=json.dumps(payload))
                assert code == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_schedule_found_for_configuration_script(self, client):
        script_name = 'demoScript'
        result = {"count": 1, "rows": [{"name": script_name, "steps": [
            {"write": {"order": 0, "service": "sine", "values": {"sinusoid": "1.2"}}}], "acl": ""}]}
        server.Server.scheduler = Scheduler(None, None)
        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            get_sch = await mock_schedule(script_name)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            get_sch = asyncio.ensure_future(mock_schedule(script_name))

        query_payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=",
                                                                       "value": script_name}}
        message = "{} schedule already exists.".format(script_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                with patch.object(server.Server.scheduler, 'get_schedules',
                                  return_value=get_sch) as patch_get_schedules:
                    resp = await client.post('/fledge/control/script/{}/schedule'.format(script_name))
                    assert 400 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": message} == json_response
                patch_get_schedules.assert_called_once_with()
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_schedule_configuration_for_script(self, client):
        script_name = "demoScript"
        schedule_cat_name = "{}-automation-script".format(script_name)
        sch_name = "foo"
        result = {"count": 1, "rows": [{"name": script_name, "steps": [
            {"write": {"order": 0, "service": "sine", "values": {"sinusoid": "1.2"}}}], "acl": ""}]}
        cat_child_result = {'children': ['dispatcherAdvanced', schedule_cat_name]}
        server.Server.scheduler = Scheduler(None, None)
        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            sch = await mock_coro("")
            queue = await mock_coro(True)
            cat = await mock_coro(None)
            child = await mock_coro(cat_child_result)
            get_sch = await mock_schedule(sch_name)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            sch = asyncio.ensure_future(mock_coro(""))
            queue = asyncio.ensure_future(mock_coro(True))
            cat = asyncio.ensure_future(mock_coro(None))
            child = asyncio.ensure_future(mock_coro(cat_child_result))
            get_sch = asyncio.ensure_future(mock_schedule(sch_name))

        query_payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=",
                                                                       "value": script_name}}
        message = "Schedule and configuration is created for an automation script with name {}".format(script_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                with patch.object(server.Server.scheduler, 'get_schedules',
                                  return_value=get_sch) as patch_get_schedules:
                    with patch.object(c_mgr, 'create_category', return_value=cat) as patch_create_cat:
                        with patch.object(c_mgr, 'create_child_category',
                                          return_value=child) as patch_create_child_cat:
                            with patch.object(server.Server.scheduler, 'save_schedule',
                                              return_value=sch) as patch_save_schedule:
                                with patch.object(server.Server.scheduler, 'queue_task',
                                                  return_value=queue) as patch_queue_task:
                                    resp = await client.post('/fledge/control/script/{}/schedule'.format(script_name))
                                    assert 200 == resp.status
                                    result = await resp.text()
                                    json_response = json.loads(result)
                                    assert {"message": message} == json_response
                                patch_queue_task.assert_called_once_with(None)
                            patch_save_schedule.assert_called_once()
                        patch_create_child_cat.assert_called_once_with('dispatcher', [schedule_cat_name])
                    assert 1 == patch_create_cat.call_count
                patch_get_schedules.assert_called_once_with()
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])
