# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import copy
import asyncio
import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest

from fledge.services.core import routes
from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.configuration_manager import ConfigurationManager, ConfigurationManagerSingleton, _logger
from fledge.common.audit_logger import AuditLogger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "configuration")
class TestConfiguration:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.fixture()
    def reset_singleton(self):
        # executed before each test
        ConfigurationManagerSingleton._shared_state = {}
        yield
        ConfigurationManagerSingleton._shared_state = {}

    async def test_get_categories(self, client):
        async def async_mock():
            return [('rest_api', 'User REST API', 'API'), ('service', 'Service configuration', 'SERV')]

        result = {'categories': [{'key': 'rest_api', 'description': 'User REST API', 'displayName': 'API'},
                                 {'key': 'service', 'description': 'Service configuration', 'displayName': 'SERV'}]}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_all_category_names', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/fledge/category')
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_get_all_items.assert_called_once_with()

    @pytest.mark.parametrize("value", [
        "True", "true", "trUe", "TRUE"
    ])
    async def test_get_categories_with_root_true(self, client, value):
        async def async_mock():
            return [('General', 'General', 'GEN'), ('Advanced', 'Advanced', 'ADV')]

        result = {'categories': [{'key': 'General', 'description': 'General', 'displayName': 'GEN'},
                                 {'key': 'Advanced', 'description': 'Advanced', 'displayName': 'ADV'}]}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_all_category_names', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/fledge/category?root={}'.format(value))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_get_all_items.assert_called_once_with(root=True)

    @pytest.mark.parametrize("value", [
        "False", "false", "fAlsE", "FALSE"
    ])
    async def test_get_categories_with_root_false(self, client, value):
        async def async_mock():
            return [('service', 'Fledge Service', 'SERV'), ('rest_api', 'Fledge Admin and User REST API', 'API'),
                    ('SMNTR', 'Service Monitor', 'Monitor'), ('SCHEDULER', 'Scheduler configuration', 'SCH')]

        result = {'categories': [{'key': 'service', 'description': 'Fledge Service', 'displayName': 'SERV'},
                                 {'key': 'rest_api', 'description': 'Fledge Admin and User REST API', 'displayName': 'API'},
                                 {'key': 'SMNTR', 'description': 'Service Monitor', 'displayName': 'Monitor'},
                                 {'key': 'SCHEDULER', 'description': 'Scheduler configuration', 'displayName': 'SCH'}]}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_all_category_names', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/fledge/category?root={}'.format(value))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_get_all_items.assert_called_once_with(root=False)

    async def test_get_categories_with_root_and_children(self, client):
        d = [{'children': [{'key': 'rest_api',
                            'description': 'REST API'},
                           {'key': 'Security',
                            'description': 'Microservices Security'},
                           {'key': 'service', 'description': 'Fledge Service'}],
              'key': 'General', 'description': 'General'},
             {'children': [], 'key': 'test', 'description': 'test'}]

        async def async_mock():
            return d

        result = {'categories': d}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_all_category_names', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/fledge/category?root=true&children=true')
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_get_all_items.assert_called_once_with(root=True, children=True)

    async def test_get_categories_with_non_root_and_children(self, client):
        d = [{'children': [], 'key': 'General', 'description': 'General'},
             {'children': [], 'key': 'test', 'description': 'test'}]

        async def async_mock():
            return d

        result = {'categories': d}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_all_category_names', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/fledge/category?root=false&children=true')
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_get_all_items.assert_called_once_with(root=False, children=True)

    async def test_get_category_not_found(self, client, category_name='blah'):
        async def async_mock():
            return None

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/fledge/category/{}'.format(category_name))
                assert 404 == resp.status
                assert 'No such Category found for {}'.format(category_name) == resp.reason
            patch_get_all_items.assert_called_once_with(category_name)

    @pytest.mark.parametrize("expected_result, hide_password", [
        ({'httpPort': {'default': '8081', 'value': '8081', 'type': 'integer', 'description': 'The port to accept HTTP'},
          'certificateName': {'default': 'fledge', 'value': 'fledge', 'type': 'string', 
                              'description': 'Certificate file name'}}, False),
        ({"p2": {"type": "password", "description": "Test Password", "default": "fledge", "value": "Fledge"}}, True)
    ])
    async def test_get_category(self, client, expected_result, hide_password, category_name='rest_api'):
        async def async_mock():
            return expected_result
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/fledge/category/{}'.format(category_name))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                if hide_password:
                    expected_result[list(expected_result.keys())[0]]['value'] = "****"
                assert expected_result == json_response
            patch_get_all_items.assert_called_once_with(category_name)

    async def test_get_category_item_not_found(self, client, category_name='rest_api', item_name='blah'):
        async def async_mock():
            return None

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                resp = await client.get('/fledge/category/{}/{}'.format(category_name, item_name))
                assert 404 == resp.status
                assert 'No such Category item found for {}'.format(item_name) == resp.reason
            patch_get_cat_item.assert_called_once_with(category_name, item_name)

    @pytest.mark.parametrize("expected_result, hide_password", [
        ({'value': '8081', 'type': 'integer', 'default': '8081', 'description': 'Port to accept HTTP conn on'}, False),
        ({'type': 'password', 'description': 'Test Password', 'default': 'fledge', 'value': 'Fledge'}, True)
    ])
    async def test_get_category_item(self, client, expected_result, hide_password, category_name='rest_api',
                                     item_name='http_port'):
        async def async_mock():
            return expected_result
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                resp = await client.get('/fledge/category/{}/{}'.format(category_name, item_name))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                if hide_password:
                    expected_result['value'] = "****"
                assert expected_result == json_response
            patch_get_cat_item.assert_called_once_with(category_name, item_name)

    @pytest.mark.parametrize("expected_result, hide_password", [
        ({'value': '8082', 'type': 'integer', 'default': '8081', 'description': 'Port to accept HTTP conn on'}, False),
        ({'type': 'password', 'description': 'Test Password', 'default': 'fledge', 'value': 'Fledge'}, True)
    ])
    async def test_set_config_item(self, client, expected_result, hide_password, category_name='rest_api',
                                   item_name='http_port'):
        async def async_mock(return_value):
            return return_value
        payload = {"value": expected_result['value']}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock(None)) as patch_set_entry:
                with patch.object(c_mgr, 'get_category_item', side_effect=[async_mock(expected_result), async_mock(expected_result)]) as patch_get_cat_item:
                    resp = await client.put('/fledge/category/{}/{}'.format(category_name, item_name),
                                            data=json.dumps(payload))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    if hide_password:
                        expected_result['value'] = "****"
                    assert expected_result == json_response
                assert 2 == patch_get_cat_item.call_count
                calls = patch_get_cat_item.call_args_list
                args, kwargs = calls[0]
                assert category_name == args[0]
                assert item_name == args[1]
                args, kwargs = calls[1]
                assert category_name == args[0]
                assert item_name == args[1]
            patch_set_entry.assert_called_once_with(category_name, item_name, payload['value'])

    @pytest.mark.parametrize("payload, message", [
        ({"valu": '8082'}, "Missing required value for http_port"),
        ({"valu": 8082}, "Missing required value for http_port"),
        ({"value": 8082}, "8082 should be a string literal, in double quotes")
    ])
    async def test_set_config_item_bad_request(self, client, payload, message, category_name='rest_api', item_name='http_port'):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            resp = await client.put('/fledge/category/{}/{}'.format(category_name, item_name),
                                    data=json.dumps(payload))
            assert 400 == resp.status
            assert message == resp.reason

    async def test_set_config_item_not_found(self, client, category_name='rest_api', item_name='http_port'):
        async def async_mock(return_value):
            return return_value

        payload = {"value": '8082'}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        storage_value_entry = {'value': '8082', 'type': 'integer', 'default': '8081',
                               'description': 'The port to accept HTTP connections on'}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock(None)) as patch_set_entry:
                with patch.object(c_mgr, 'get_category_item', side_effect=[async_mock(storage_value_entry), async_mock(None)]) as patch_get_cat_item:
                    resp = await client.put('/fledge/category/{}/{}'.format(category_name, item_name),
                                            data=json.dumps(payload))
                    assert 404 == resp.status
                    assert "No detail found for the category_name: {} and config_item: {}".format(category_name, item_name) == resp.reason
                assert 2 == patch_get_cat_item.call_count
                calls = patch_get_cat_item.call_args_list
                args, kwargs = calls[0]
                assert category_name == args[0]
                assert item_name == args[1]
                args, kwargs = calls[1]
                assert category_name == args[0]
                assert item_name == args[1]
            patch_set_entry.assert_called_once_with(category_name, item_name, payload['value'])

    @pytest.mark.parametrize("payload, optional_item, message", [
        ({"value": '8082'}, "readonly", "Update not allowed for {} item_name as it has readonly attribute set")
    ])
    async def test_set_config_item_not_allowed(self, client, payload, message, optional_item, category_name='rest_api', item_name='http_port'):
        async def async_mock(return_value):
            return return_value
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        storage_value_entry = {'value': '8082', 'type': 'integer', 'default': '8081',
                               'description': 'The port to accept HTTP connections on', optional_item: 'true'}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock(storage_value_entry)) as patch_get_cat:
                resp = await client.put('/fledge/category/{}/{}'.format(category_name, item_name), data=json.dumps(payload))
                assert 400 == resp.status
                assert message.format(item_name) == resp.reason
            patch_get_cat.assert_called_once_with(category_name, item_name)

    @pytest.mark.parametrize("value", [
        '',
        'false',
        'true'
    ])
    async def test_set_optional_in_config_item(self, client, value, category_name='rest_api', item_name='http_port', optional_key='readonly'):
        async def async_mock(return_value):
            return return_value

        payload = {optional_key: value}
        result = {optional_key: 'false', 'value': '8082', 'type': 'integer', 'default': '8081',
                  'description': 'The port to accept HTTP connections on'}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_optional_value_entry', return_value=async_mock(None)) as patch_set_entry:
                with patch.object(c_mgr, 'get_category_item', return_value=async_mock(result)) as patch_get_cat_item:
                    resp = await client.put('/fledge/category/{}/{}'.format(category_name, item_name),
                                            data=json.dumps(payload))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    assert result == json_response
                patch_get_cat_item.assert_called_once_with(category_name, item_name)
            patch_set_entry.assert_called_once_with(category_name, item_name, optional_key, payload[optional_key])

    async def test_set_optional_in_config_item_exception(self, client, category_name='rest_api', item_name='http_port'):
        optional_key = 'readonly'
        payload = {optional_key: '8082'}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_optional_value_entry', side_effect=ValueError) as patch_set_entry:
                resp = await client.put('/fledge/category/{}/{}'.format(category_name, item_name), data=json.dumps(payload))
                assert 400 == resp.status
                assert resp.reason is ''
            patch_set_entry.assert_called_once_with(category_name, item_name, optional_key, payload[optional_key])

    @pytest.mark.parametrize("expected_result, hide_password", [
        ({'value': '8082', 'type': 'integer', 'default': '8081', 'description': 'Port to accept HTTP conn on'}, False),
        ({'type': 'password', 'description': 'Test Password', 'default': 'fledge', 'value': 'Fledge'}, True)
    ])
    async def test_delete_config_item(self, client, expected_result, hide_password, category_name='rest_api',
                                      item_name='http_port'):
        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', side_effect=[async_mock(expected_result), async_mock(expected_result)]) as patch_get_cat_item:
                with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock(None)) as patch_set_entry:
                    resp = await client.delete('/fledge/category/{}/{}/value'.format(category_name, item_name))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    if hide_password:
                        expected_result['value'] = "****"
                    assert expected_result == json_response
                patch_set_entry.assert_called_once_with(category_name, item_name, expected_result['default'])
            assert 2 == patch_get_cat_item.call_count
            args, kwargs = patch_get_cat_item.call_args
            assert category_name == args[0]
            assert item_name == args[1]

    async def test_delete_config_item_not_allowed(self, client, category_name='rest_api', item_name='http_port'):
        result = {'value': '8081', 'type': 'integer', 'default': '8081',
                  'description': 'The port to accept HTTP connections on', 'readonly': 'true'}

        async def async_mock():
            return result

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', side_effect=[async_mock()]) as patch_get_cat_item:
                resp = await client.delete('/fledge/category/{}/{}/value'.format(category_name, item_name))
                assert 400 == resp.status
                assert 'Delete not allowed for {} item_name as it has readonly attribute set'.format(item_name) == resp.reason
            assert 1 == patch_get_cat_item.call_count
            args, kwargs = patch_get_cat_item.call_args
            assert category_name == args[0]
            assert item_name == args[1]

    async def test_delete_config_item_not_found_before_set_config(self, client, category_name='rest_api', item_name='http_port'):
        async def async_mock():
            return None

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                resp = await client.delete('/fledge/category/{}/{}/value'.format(category_name, item_name))
                assert 404 == resp.status
                assert "No detail found for the category_name: {} and config_item: {}".format(category_name, item_name) == resp.reason
            assert 1 == patch_get_cat_item.call_count
            args, kwargs = patch_get_cat_item.call_args
            assert category_name == args[0]
            assert item_name == args[1]

    async def test_delete_config_not_found_after_set_config(self, client, category_name='rest_api', item_name='http_port'):
        result = {'value': '8081', 'type': 'integer', 'default': '8081',
                  'description': 'The port to accept HTTP connections on'}

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', side_effect=[async_mock(result), async_mock(None)]) as patch_get_cat_item:
                with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock(None)) as patch_set_entry:
                    resp = await client.delete('/fledge/category/{}/{}/value'.format(category_name, item_name))
                    assert 404 == resp.status
                    assert "No detail found for the category_name: {} and config_item: {}".format(category_name, item_name) == resp.reason
                patch_set_entry.assert_called_once_with(category_name, item_name, result['default'])
            assert 2 == patch_get_cat_item.call_count
            args, kwargs = patch_get_cat_item.call_args
            assert category_name == args[0]
            assert item_name == args[1]

    @pytest.mark.parametrize("payload, message", [
        ("blah", "Data payload must be a dictionary"),
        ({}, "\"'key' param required to create a category\""),
        ({"key": "test"}, "\"'description' param required to create a category\""),
        ({"description": "test"}, "\"'key' param required to create a category\""),
        ({"value": "test"}, "\"'key' param required to create a category\""),
        ({"key": "test", "description": "des"}, "\"'value' param required to create a category\""),
        ({"key": "test", "value": "val"}, "\"'description' param required to create a category\""),
        ({"description": "desc", "value": "val"}, "\"'key' param required to create a category\""),
        ({"key":"test", "description":"test", "value": {"test1": {"type": "string", "description": "d", "default": "",
                                                                  "mandatory": "true"}}},
         "For test category, A default value must be given for test1"),
        ({"key": "", "description": "test", "value": "val"}, "Key should not be empty"),
        ({"key": " ", "description": "test", "value": "val"}, "Key should not be empty")
    ])
    async def test_create_category_bad_request(self, client, payload, message):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            resp = await client.post('/fledge/category', data=json.dumps(payload))
            assert 400 == resp.status
            assert message == resp.reason

    @pytest.mark.parametrize("payload, hide_password", [
        ({"key": "T1", "description": "Test"}, False),
        ({"key": "T2", "description": "Test 2", "display_name": "Test Display"}, False),
        ({"key": "T3", "description": "Test 3"}, True),
        ({"key": "T4", "description": "Test 4", "display_name": ""}, False),
        ({"key": "T5", "description": "Test 5", "display_name": " "}, True)
    ])
    async def test_create_category(self, client, reset_singleton, payload, hide_password):
        info = {'p1': {'type': 'password', 'description': 'P1', 'default': 'P1', 'value': 'P1'}} if hide_password else {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        new_info = copy.deepcopy(info)
        payload["value"] = new_info

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        if 'display_name' in payload:
            if not len(payload['display_name'].strip()):
                payload.pop('display_name')
                payload['displayName'] = payload['key']
            else:
                payload['displayName'] = payload.pop('display_name')
        else:
            payload.update({'displayName': payload['key']})

        c_mgr._cacheManager.update(payload['key'], payload['description'], new_info, payload['displayName'])
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'create_category', return_value=async_mock(None)) as patch_create_cat:
                with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock(new_info)) as patch_cat_all_item:
                    resp = await client.post('/fledge/category', data=json.dumps(payload))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    if hide_password:
                        payload['value'][list(payload['value'].keys())[0]]['value'] = "****"
                    assert payload == json_response
                patch_cat_all_item.assert_called_once_with(category_name=payload['key'])
            patch_create_cat.assert_called_once_with(category_name=payload['key'], category_description=payload['description'],
                                                     category_value=info, keep_original_items=False, display_name=None)

    async def test_create_category_invalid_key(self, client, name="test_cat", desc="Test desc"):
        info = {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        payload = {"key": name, "description": desc, "value": info, "keep_original_items": "bla"}

        storage_client_mock = MagicMock(StorageClientAsync)
        ConfigurationManager(storage_client_mock)
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                resp = await client.post('/fledge/category', data=json.dumps(payload))
                assert 400 == resp.status
                assert "Specifying value_name and value_val for item_name info is not allowed if desired behavior is to use default_val as value_val" == resp.reason
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to create new category based on category_name %s and category_description %s and category_json_schema %s', 'test_cat', 'Test desc', '')

    async def test_create_category_invalid_category(self, client, name="test_cat", desc="Test desc"):
        info = {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        payload = {"key": name, "description": desc, "value": info}

        async def async_mock_create_cat():
            return None

        async def async_mock():
            return None

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'create_category', return_value=async_mock_create_cat()) as patch_create_cat:
                with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_cat_all_item:
                    resp = await client.post('/fledge/category', data=json.dumps(payload))
                    assert 404 == resp.status
                    assert 'No such test_cat found' == resp.reason
                patch_cat_all_item.assert_called_once_with(category_name=name)
            patch_create_cat.assert_called_once_with(category_name=name, category_description=desc,
                                                     category_value=info, keep_original_items=False, display_name=None)

    async def test_create_category_http_exception(self, client, name="test_cat", desc="Test desc"):
        info = {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        payload = {"key": name, "description": desc, "value": info}
        msg = 'Something went wrong'
        with patch.object(connect, 'get_storage_async', side_effect=Exception(msg)):
            resp = await client.post('/fledge/category', data=json.dumps(payload))
            assert 500 == resp.status
            assert msg == resp.reason

    @pytest.mark.parametrize("payload, message", [
        # FIXME: keys order mismatch assertion
        # ({"default": "1"}, "Missing entry_name"),
        # ({"value": "0"}, "Missing entry_name"),
        # ({"description": "1", "type": "Integer"}, "Invalid entry_val for entry_name \"type\" for item_name info. valid: ['IPv4', 'IPv6', 'JSON', 'X509 certificate', 'boolean', 'integer', 'password', 'string']")
        # ("blah", "Data payload must be a dictionary"),
        ({}, "entry value must be a string for item name info and entry name value; got <class 'NoneType'>"),
        ({"description": "Test desc"}, "entry value must be a string for item name info and entry name value; got <class 'NoneType'>"),
        ({"type": "integer"}, "entry value must be a string for item name info and entry name value; got <class 'NoneType'>"),
        ({"default": "1", "description": "Test desc"}, "missing entry name type for item name info"),
        ({"default": "1", "type": "integer"}, "missing entry name description for item name info"),
        ({"description": "1", "type": "integer"}, "entry value must be a string for item name info and entry name value; got <class 'NoneType'>")
    ])
    async def test_validate_data_for_add_config_item(self, client, payload, message, loop):
        @asyncio.coroutine
        def async_mock():
            return message

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              return_value=asyncio.ensure_future(async_mock(), loop=loop)) as log_code_patch:
                resp = await client.post('/fledge/category/{}/{}'.format("cat", "info"), data=json.dumps(payload))
                assert 400 == resp.status
                assert "For cat category, {}".format(message) == resp.reason

    async def test_invalid_cat_for_add_config_item(self, client):
        async def async_mock():
            return None

        category_name = 'blah'
        payload = {"default": "1", "description": "Test description", "type": "integer"}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_get_all_items:
                resp = await client.post('/fledge/category/{}/{}'.format(category_name, "info"), data=json.dumps(payload))
                assert 404 == resp.status
                assert 'No such Category found for {}'.format(category_name) == resp.reason
            patch_get_all_items.assert_called_once_with(category_name)

    async def test_config_item_in_use_for_add_config_item(self, client):
        async def async_mock():
            return {"info": {"default": "1", "description": "Test description", "type": "integer"}}

        category_name = 'cat'
        payload = {"default": "1", "description": "Test description", "type": "integer"}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_get_all_items:
                resp = await client.post('/fledge/category/{}/{}'.format(category_name, "info"), data=json.dumps(payload))
                assert 400 == resp.status
                assert "'Config item is already in use for {}'".format(category_name) == resp.reason
            patch_get_all_items.assert_called_once_with(category_name)

    @pytest.mark.parametrize("data, payload", [
        ({"default": "true", "description": "Test description", "type": "boolean"}, '{"values": {"value": {"info": {"default": "1", "type": "integer", "description": "Test description"}, "info1": {"value": "true", "default": "true", "type": "boolean", "description": "Test description"}}}, "where": {"column": "key", "condition": "=", "value": "cat"}}'),
        ({"default": "true", "description": "Test description", "type": "boolean", "value": "false"}, '{"values": {"value": {"info": {"default": "1", "type": "integer", "description": "Test description"}, "info1": {"value": "false", "default": "true", "type": "boolean", "description": "Test description"}}}, "where": {"column": "key", "condition": "=", "value": "cat"}}')
    ])
    async def test_add_config_item(self, client, data, payload, loop):
        @asyncio.coroutine
        def async_mock():
            return {"info": {"default": "1", "description": "Test description", "type": "integer"}}

        @asyncio.coroutine
        def async_audit_mock(return_value):
            return return_value

        @asyncio.coroutine
        def async_mock_expected():
            expected = {'rows_affected': 1, "response": "updated"}
            return expected

        category_name = 'cat'
        new_config_item = 'info1'
        result = {'message': '{} config item has been saved for {} category'.format(new_config_item, category_name)}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=asyncio.ensure_future(async_mock(), loop=loop)) as patch_get_all_items:
                with patch.object(storage_client_mock, 'update_tbl', return_value=asyncio.ensure_future(async_mock_expected(), loop=loop)) as update_tbl_patch:
                    with patch.object(AuditLogger, '__init__', return_value=None):
                        with patch.object(AuditLogger, 'information', return_value=asyncio.ensure_future(async_audit_mock(None), loop=loop)) as audit_info_patch:
                            resp = await client.post('/fledge/category/{}/{}'.format(category_name, new_config_item), data=json.dumps(data))
                            assert 200 == resp.status
                            r = await resp.text()
                            json_response = json.loads(r)
                            assert result == json_response

                    if 'value' not in data:
                        data.update({'value': data.get('default')})
                    val = {new_config_item: data}
                    audit_details = {'category': category_name, 'item': new_config_item, 'value': val}
                    args, kwargs = audit_info_patch.call_args
                    assert 'CONAD' == args[0]
                    assert audit_details == args[1]
                args1, kwargs1 = update_tbl_patch.call_args
                assert 'configuration' == args1[0]
                assert json.loads(payload) == json.loads(args1[1])
            patch_get_all_items.assert_called_once_with(category_name)

    async def test_unknown_exception_for_add_config_item(self, client):
        data = {"default": "d", "description": "Test description", "type": "boolean"}
        msg = 'Internal Server Error'
        with patch.object(connect, 'get_storage_async', side_effect=Exception(msg)):
            resp = await client.post('/fledge/category/{}/{}'.format("blah", "blah"), data=json.dumps(data))
            assert 500 == resp.status
            assert msg == resp.reason

    async def test_get_child_category(self, client):
        @asyncio.coroutine
        def async_mock():
            return []

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_child', return_value=async_mock()) as patch_get_child_cat:
                resp = await client.get('/fledge/category/south/children')
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert {"categories": []} == json_response
        patch_get_child_cat.assert_called_once_with('south')

    async def test_create_child_category(self, client):
        data = {"children": ["coap", "http", "sinusoid"]}
        result = {"children": data["children"]}

        @asyncio.coroutine
        def async_mock():
            return result

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'create_child_category', return_value=async_mock()) as patch_create_child_cat:
                resp = await client.post('/fledge/category/{}/children'.format("south"), data=json.dumps(data))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_create_child_cat.assert_called_once_with('south', data['children'])

    async def test_delete_child_category(self, client):
        @asyncio.coroutine
        def async_mock():
            return ["http", "sinusoid"]

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'delete_child_category', return_value=async_mock()) as patch_delete_child_cat:
                resp = await client.delete('/fledge/category/{}/children/{}'.format("south", "coap"))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert {"children": ["http", "sinusoid"]} == json_response
            patch_delete_child_cat.assert_called_once_with('south', 'coap')

    async def test_delete_parent_category(self, client):
        @asyncio.coroutine
        def async_mock():
            return None

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'delete_parent_category', return_value=async_mock()) as patch_delete_parent_cat:
                resp = await client.delete('/fledge/category/{}/parent'.format("south"))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert {'message': 'Parent-child relationship for the parent-south is deleted'} == json_response
            patch_delete_parent_cat.assert_called_once_with('south')

    async def test_create_category_with_children(self, client, reset_singleton, name="test_cat", desc="Test desc"):
        info = {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        children = ["child1", "child2"]
        payload = {"key": name, "description": desc, "value": info, "children": children}

        async def async_mock_create_cat():
            return None

        async def async_mock():
            return info

        async def async_mock2():
            return {"children": children}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        c_mgr._cacheManager.update(name, desc, info, name)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'create_category', return_value=async_mock_create_cat()) as patch_create_cat:
                with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_cat_all_item:
                    with patch.object(c_mgr, 'create_child_category', return_value=async_mock2()) as patch_create_child:
                        resp = await client.post('/fledge/category', data=json.dumps(payload))
                        assert 200 == resp.status
                        r = await resp.text()
                        json_response = json.loads(r)
                        payload.update({'displayName': name})
                        assert payload == json_response
                    patch_create_child.assert_called_once_with(name, payload["children"])
                patch_cat_all_item.assert_called_once_with(category_name=name)
            patch_create_cat.assert_called_once_with(category_name=name, category_description=desc,
                                                     category_value=info, keep_original_items=False, display_name=None)

    async def test_update_bulk_config_bad_request(self, client, category_name='rest_api'):
        resp = await client.put('/fledge/category/{}'.format(category_name), data=json.dumps({}))
        assert 400 == resp.status
        assert 'Nothing to update' == resp.reason

    @pytest.mark.parametrize("code, exception_name", [
        (404, [NameError, KeyError]),
        (400, [ValueError, TypeError]),
        (500, Exception)
    ])
    async def test_update_bulk_config_exception(self, client,  code, exception_name, category_name='rest_api'):
        config_item_name = "authentication"
        payload = {config_item_name: "required"}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', side_effect=exception_name) as patch_get_cat_item:
                resp = await client.put('/fledge/category/{}'.format(category_name), data=json.dumps(payload))
                assert code == resp.status
                assert resp.reason is ''
            patch_get_cat_item.assert_called_once_with(category_name, config_item_name)

    async def test_update_bulk_config_item_not_found(self, client, category_name='rest_api'):
        async def async_mock(return_value):
            return return_value

        config_item_name = "https"
        payload = {config_item_name: "8082"}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock(None)) as patch_get_cat_item:
                resp = await client.put('/fledge/category/{}'.format(category_name), data=json.dumps(payload))
                assert 404 == resp.status
                assert "'{} config item not found'".format(config_item_name) == resp.reason
            patch_get_cat_item.assert_called_once_with(category_name, config_item_name)

    @pytest.mark.parametrize("payload, optional_item, message", [
        ({"http_port": '8082'}, "readonly", "Bulk update not allowed for {} item_name as it has readonly attribute set")
    ])
    async def test_update_bulk_config_not_allowed(self, client, payload, optional_item, message,
                                                  category_name='rest_api'):
        async def async_mock(return_value):
            return return_value

        config_item_name = list(payload)[0]
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        storage_value_entry = {'description': 'Port to accept HTTP connections on', 'displayName': 'HTTP Port',
                               'value': '8081', 'default': '8081', 'order': '2', 'type': 'integer', optional_item: 'true'}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock(storage_value_entry)) as patch_get_cat_item:
                resp = await client.put('/fledge/category/{}'.format(category_name), data=json.dumps(payload))
                assert 400 == resp.status
                assert message.format(config_item_name) == resp.reason
            patch_get_cat_item.assert_called_once_with(category_name, config_item_name)

    @pytest.mark.parametrize("category_name", [
        "rest_api", "Rest $API"
    ])
    async def test_update_bulk_config(self, client, category_name):
        async def async_mock(return_value):
            return return_value

        response = {"response": "updated", "rows_affected": 1}
        result = {'authentication': {'options': ['mandatory', 'optional'], 'description': 'API Call Authentication', 'displayName': 'Authentication', 'value': 'mandatory', 'default': 'optional', 'order': '5', 'type': 'enumeration'},
                  'enableHttp': {'description': 'Enable HTTP (disable to use HTTPS)', 'displayName': 'Enable HTTP', 'value': 'true', 'default': 'true', 'order': '1', 'type': 'boolean'},
                  'httpPort': {'description': 'Port to accept HTTP connections on', 'displayName': 'HTTP Port', 'value': '8082', 'default': '8081', 'order': '2', 'type': 'integer'}}

        payload = {"http_port": "8082", "authentication": "mandatory"}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        storage_value_entry1 = {'description': 'Port to accept HTTP connections on', 'displayName': 'HTTP Port', 'value': '8081', 'default': '8081', 'order': '2', 'type': 'integer'}
        storage_value_entry2 = {'options': ['mandatory', 'optional'], 'description': 'API Call Authentication', 'displayName': 'Authentication', 'value': 'optional', 'default': 'optional', 'order': '5', 'type': 'enumeration'}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', side_effect=[async_mock(storage_value_entry1), async_mock(storage_value_entry2)]) as patch_get_cat_item:
                with patch.object(c_mgr, 'update_configuration_item_bulk', return_value=async_mock(response)) as patch_update_bulk:
                    with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock(result)) as patch_get_all_items:
                        resp = await client.put('/fledge/category/{}'.format(category_name), data=json.dumps(payload))
                        assert 200 == resp.status
                        r = await resp.text()
                        json_response = json.loads(r)
                        assert result == json_response
                    patch_get_all_items.assert_called_once_with(category_name)
                patch_update_bulk.assert_called_once_with(category_name, payload)
            assert 2 == patch_get_cat_item.call_count

    async def test_delete_configuration(self, client, category_name='rest_api'):
        result = {'result': 'Category {} deleted successfully.'.format(category_name)}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'delete_category_and_children_recursively', return_value=asyncio.sleep(.1)) as patch_delete_cat:
                resp = await client.delete('/fledge/category/{}'.format(category_name))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            assert 1 == patch_delete_cat.call_count
            args, kwargs = patch_delete_cat.call_args
            assert category_name == args[0]
