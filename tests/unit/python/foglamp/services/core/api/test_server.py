# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from unittest.mock import patch
from aiohttp import web
import pytest

from foglamp.services.common.microservice_management import routes as management_routes
from foglamp.services.core.server import Server
from foglamp.common.web import middleware
from foglamp.services.core.api import configuration as conf_api

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "server")
class TestServer:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(middlewares=[middleware.error_middleware])
        management_routes.setup(app, Server, True)
        return loop.run_until_complete(test_client(app))

    async def test_get_configuration_categories(self, client):
        async def async_mock():
            return web.json_response({'categories': "test"})

        result = {'categories': "test"}
        with patch.object(conf_api, 'get_categories', return_value=async_mock()) as patch_get_all_categories:
            resp = await client.get('/foglamp/service/category')
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_get_all_categories.call_count

    async def test_get_configuration_category(self, client):
        async def async_mock():
            return web.json_response("test")

        result = "test"
        with patch.object(conf_api, 'get_category', return_value=async_mock()) as patch_category:
            resp = await client.get('/foglamp/service/category/{}'.format("test_category"))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_category.call_count

    async def test_create_configuration_category(self, client):
        async def async_mock():
            return web.json_response({"key": "test_name",
                                      "description": "test_category_desc",
                                      "value": "test_category_info"})

        result = {"key": "test_name", "description": "test_category_desc", "value": "test_category_info"}
        with patch.object(conf_api, 'create_category', return_value=async_mock()) as patch_create_category:
            resp = await client.post('/foglamp/service/category')
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_create_category.call_count

    async def test_get_configuration_item(self, client):
        async def async_mock():
            return web.json_response("test")

        result = "test"
        with patch.object(conf_api, 'get_category_item', return_value=async_mock()) as patch_category_item:
            resp = await client.get('/foglamp/service/category/{}/{}'.format("test_category", "test_item"))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_category_item.call_count

    async def test_update_configuration_item(self, client):
        async def async_mock():
            return web.json_response("test")

        result = "test"
        with patch.object(conf_api, 'set_configuration_item', return_value=async_mock()) as patch_update_category_item:
            resp = await client.put('/foglamp/service/category/{}/{}'.format("test_category", "test_item"))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_update_category_item.call_count

    async def test_delete_configuration_item(self, client):
        async def async_mock():
            return web.json_response("ok")

        result = "ok"
        with patch.object(conf_api, 'delete_configuration_item_value', return_value=async_mock()) as patch_del_category_item:
            resp = await client.delete('/foglamp/service/category/{}/{}/value'.format("test_category", "test_item"))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_del_category_item.call_count
