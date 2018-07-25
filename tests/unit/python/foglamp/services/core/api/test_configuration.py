# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.audit_logger import AuditLogger

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

    async def test_get_categories(self, client):
        async def async_mock():
            return [('rest_api', 'User REST API'), ('service', 'Service configuration')]

        result = {'categories': [{'key': 'rest_api', 'description': 'User REST API'},
                                 {'key': 'service', 'description': 'Service configuration'}]}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_all_category_names', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/foglamp/category')
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_get_all_items.assert_called_once_with()

    async def test_get_category_not_found(self, client, category_name='blah'):
        async def async_mock():
            return None

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/foglamp/category/{}'.format(category_name))
                assert 404 == resp.status
                assert 'No such Category found for {}'.format(category_name) == resp.reason
            patch_get_all_items.assert_called_once_with(category_name)

    async def test_get_category(self, client, category_name='rest_api'):
        result = {'httpPort': {'default': '8081', 'value': '8081', 'type': 'integer',
                               'description': 'The port to accept HTTP connections on'},
                  'certificateName': {'default': 'foglamp', 'value': 'foglamp', 'type': 'string',
                                      'description': 'Certificate file name'}}

        async def async_mock():
            return result

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_get_all_items:
                resp = await client.get('/foglamp/category/{}'.format(category_name))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_get_all_items.assert_called_once_with(category_name)

    async def test_get_category_item_not_found(self, client, category_name='rest_api', item_name='blah'):
        async def async_mock():
            return None

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                resp = await client.get('/foglamp/category/{}/{}'.format(category_name, item_name))
                assert 404 == resp.status
                assert 'No such Category item found for {}'.format(item_name) == resp.reason
            patch_get_cat_item.assert_called_once_with(category_name, item_name)

    async def test_get_category_item(self, client, category_name='rest_api', item_name='http_port'):
        result = {'value': '8081', 'type': 'integer', 'default': '8081',
                  'description': 'The port to accept HTTP connections on'}

        async def async_mock():
            return result

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                resp = await client.get('/foglamp/category/{}/{}'.format(category_name, item_name))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result == json_response
            patch_get_cat_item.assert_called_once_with(category_name, item_name)

    async def test_set_config_item(self, client, category_name='rest_api', item_name='http_port'):
        payload = {"value": '8082'}
        result = {'value': '8082', 'type': 'integer', 'default': '8081',
                  'description': 'The port to accept HTTP connections on'}

        async def async_mock_set_item():
            return None

        async def async_mock():
            return result

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock_set_item()) as patch_set_entry:
                with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                    resp = await client.put('/foglamp/category/{}/{}'.format(category_name, item_name),
                                            data=json.dumps(payload))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    assert result == json_response
                patch_get_cat_item.assert_called_once_with(category_name, item_name)
            patch_set_entry.assert_called_once_with(category_name, item_name, payload['value'])

    async def test_set_config_item_bad_request(self, client, category_name='rest_api', item_name='http_port'):
        payload = {"valu": '8082'}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            resp = await client.put('/foglamp/category/{}/{}'.format(category_name, item_name),
                                    data=json.dumps(payload))
            assert 400 == resp.status
            assert 'Missing required value for {}'.format(item_name) == resp.reason

    async def test_set_config_item_not_found(self, client, category_name='rest_api', item_name='http_port'):
        async def async_mock():
            return None

        payload = {"value": '8082'}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock()) as patch_set_entry:
                with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                    resp = await client.put('/foglamp/category/{}/{}'.format(category_name, item_name),
                                            data=json.dumps(payload))
                    assert 404 == resp.status
                    assert "No detail found for the category_name: {} and config_item: {}".format(category_name, item_name) == resp.reason
                patch_get_cat_item.assert_called_once_with(category_name, item_name)
            patch_set_entry.assert_called_once_with(category_name, item_name, payload['value'])

    async def test_set_config_item_exception(self, client, category_name='rest_api', item_name='http_port'):
        payload = {"value": '8082'}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_category_item_value_entry', side_effect=ValueError) as patch_set_entry:
                resp = await client.put('/foglamp/category/{}/{}'.format(category_name, item_name), data=json.dumps(payload))
                assert 404 == resp.status
                assert "No detail found for the category_name: {} and config_item: {}".format(category_name, item_name) == resp.reason
            patch_set_entry.assert_called_once_with(category_name, item_name, payload['value'])

    async def test_delete_config_item(self, client, category_name='rest_api', item_name='http_port'):
        result = {'value': '8081', 'type': 'integer', 'default': '8081',
                  'description': 'The port to accept HTTP connections on'}

        async def async_mock_set_item():
            return None

        async def async_mock():
            return result

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', side_effect=[async_mock(), async_mock()]) as patch_get_cat_item:
                with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock_set_item()) as patch_set_entry:
                    resp = await client.delete('/foglamp/category/{}/{}/value'.format(category_name, item_name))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    assert result == json_response
                patch_set_entry.assert_called_once_with(category_name, item_name, result['default'])
            assert 2 == patch_get_cat_item.call_count
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
                resp = await client.delete('/foglamp/category/{}/{}/value'.format(category_name, item_name))
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
                    resp = await client.delete('/foglamp/category/{}/{}/value'.format(category_name, item_name))
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
    ])
    async def test_create_category_bad_request(self, client, payload, message):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            resp = await client.post('/foglamp/category', data=json.dumps(payload))
            assert 400 == resp.status
            assert message == resp.reason

    async def test_create_category(self, client, name="test_cat", desc="Test desc"):
        info = {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        payload = {"key": name, "description": desc, "value": info}

        async def async_mock_create_cat():
            return None

        async def async_mock():
            return info

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'create_category', return_value=async_mock_create_cat()) as patch_create_cat:
                with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_cat_all_item:
                    resp = await client.post('/foglamp/category', data=json.dumps(payload))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    assert payload == json_response
                patch_cat_all_item.assert_called_once_with(category_name=name)
            patch_create_cat.assert_called_once_with(category_name=name, category_description=desc,
                                                     category_value=info, keep_original_items=False)

    async def test_create_category_invalid_key(self, client, name="test_cat", desc="Test desc"):
        info = {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        payload = {"key": name, "description": desc, "value": info, "keep_original_items": "bla"}

        storage_client_mock = MagicMock(StorageClientAsync)
        ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            resp = await client.post('/foglamp/category', data=json.dumps(payload))
            assert 400 == resp.status
            assert "Specifying value_name and value_val for item_name info is not allowed if desired behavior is to use default_val as value_val" == resp.reason

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
                    resp = await client.post('/foglamp/category', data=json.dumps(payload))
                    assert 404 == resp.status
                    assert 'No such test_cat found' == resp.reason
                patch_cat_all_item.assert_called_once_with(category_name=name)
            patch_create_cat.assert_called_once_with(category_name=name, category_description=desc,
                                                     category_value=info, keep_original_items=False)

    async def test_create_category_http_exception(self, client, name="test_cat", desc="Test desc"):
        info = {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        payload = {"key": name, "description": desc, "value": info}
        with patch.object(connect, 'get_storage_async', side_effect=Exception):
            resp = await client.post('/foglamp/category', data=json.dumps(payload))
            assert 500 == resp.status
            assert 'Internal Server Error' == resp.reason

    @pytest.mark.parametrize("payload, message", [
        # FIXME: keys order mismatch assertion
        # ({"default": "1"}, "Missing entry_name"),
        # ({"value": "0"}, "Missing entry_name"),
        # ({"description": "1", "type": "Integer"}, "Invalid entry_val for entry_name \"type\" for item_name info. valid: ['IPv4', 'IPv6', 'JSON', 'X509 certificate', 'boolean', 'integer', 'password', 'string']")
        ("blah", "Data payload must be a dictionary"),
        ({}, "entry_val must be a string for item_name info and entry_name value"),
        ({"description": "Test desc"}, "entry_val must be a string for item_name info and entry_name value"),
        ({"type": "integer"}, "entry_val must be a string for item_name info and entry_name value"),
        ({"default": "1", "description": "Test desc"}, "Missing entry_name type for item_name info"),
        ({"default": "1", "type": "integer"}, "Missing entry_name description for item_name info"),
        ({"description": "1", "type": "integer"}, "entry_val must be a string for item_name info and entry_name value")
    ])
    async def test_validate_data_for_add_config_item(self, client, payload, message, loop):
        @asyncio.coroutine
        def async_mock():
            return message

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              return_value=asyncio.ensure_future(async_mock(), loop=loop)) as log_code_patch:
                resp = await client.post('/foglamp/category/{}/{}'.format("cat", "info"), data=json.dumps(payload))
                assert 400 == resp.status
                assert message == resp.reason

    async def test_invalid_cat_for_add_config_item(self, client):
        async def async_mock():
            return None

        category_name = 'blah'
        payload = {"default": "1", "description": "Test description", "type": "integer"}
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=async_mock()) as patch_get_all_items:
                resp = await client.post('/foglamp/category/{}/{}'.format(category_name, "info"), data=json.dumps(payload))
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
                resp = await client.post('/foglamp/category/{}/{}'.format(category_name, "info"), data=json.dumps(payload))
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
                            resp = await client.post('/foglamp/category/{}/{}'.format(category_name, new_config_item), data=json.dumps(data))
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
        with patch.object(connect, 'get_storage_async', side_effect=Exception):
            resp = await client.post('/foglamp/category/{}/{}'.format("blah", "blah"), data=json.dumps(data))
            assert 500 == resp.status
            assert 'Internal Server Error' == resp.reason
