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
from foglamp.common.configuration_manager import ConfigurationManager

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
        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
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

        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
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

        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
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

        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
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

        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
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

        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
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
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            resp = await client.put('/foglamp/category/{}/{}'.format(category_name, item_name),
                                    data=json.dumps(payload))
            assert 400 == resp.status
            assert 'Missing required value for {}'.format(item_name) == resp.reason

    async def test_set_config_item_not_found(self, client, category_name='rest_api', item_name='http_port'):
        async def async_mock():
            return None

        payload = {"value": '8082'}
        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock()) as patch_set_entry:
                with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                    resp = await client.put('/foglamp/category/{}/{}'.format(category_name, item_name),
                                            data=json.dumps(payload))
                    assert 404 == resp.status
                    assert "No detail found for the category_name: {} and config_item: {}".format(category_name, item_name) == resp.reason
                patch_get_cat_item.assert_called_once_with(category_name, item_name)
            patch_set_entry.assert_called_once_with(category_name, item_name, payload['value'])

    async def test_delete_config_item(self, client, category_name='rest_api', item_name='http_port'):
        result = {'value': '', 'type': 'integer', 'default': '8081',
                  'description': 'The port to accept HTTP connections on'}

        async def async_mock_set_item():
            return None

        async def async_mock():
            return result

        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock_set_item()) as patch_set_entry:
                with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                    resp = await client.delete('/foglamp/category/{}/{}/value'.format(category_name, item_name))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    assert result == json_response
                patch_get_cat_item.assert_called_once_with(category_name, item_name)
            patch_set_entry.assert_called_once_with(category_name, item_name, '')

    async def test_delete_config_item_not_found(self, client, category_name='rest_api', item_name='http_port'):
        async def async_mock():
            return None

        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(c_mgr, 'set_category_item_value_entry', return_value=async_mock()) as patch_set_entry:
                with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_get_cat_item:
                    resp = await client.delete('/foglamp/category/{}/{}/value'.format(category_name, item_name))
                    assert 404 == resp.status
                    assert "No detail found for the category_name: {} and config_item: {}".format(category_name, item_name) == resp.reason
                patch_get_cat_item.assert_called_once_with(category_name, item_name)
            patch_set_entry.assert_called_once_with(category_name, item_name, '')

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
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
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

        storage_client_mock = MagicMock(StorageClient)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
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

    async def test_create_category_http_exception(self, client, name="test_cat", desc="Test desc"):
        info = {'info': {'type': 'boolean', 'value': 'False', 'description': 'Test', 'default': 'False'}}
        payload = {"key": name, "description": desc, "value": info}
        resp = await client.post('/foglamp/category', data=json.dumps(payload))
        assert 500 == resp.status
        assert 'Internal Server Error' == resp.reason
