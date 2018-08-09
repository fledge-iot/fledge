# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
from unittest.mock import patch
import pytest
from aiohttp import web
from foglamp.services.core import routes
from foglamp.common.plugin_discovery import PluginDiscovery


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "plugin-discovery")
class TestPluginDiscoveryApi:
    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_plugins_installed(self, client):
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value={}) as patch_get_plugin_installed:
            resp = await client.get('/foglamp/plugins/installed')
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'plugins': {}} == json_response
        patch_get_plugin_installed.assert_called_once_with(None)

    @pytest.mark.parametrize("param", [
        "north",
        "south",
        "North",
        "South",
        "NORTH",
        "SOUTH"
    ])
    async def test_get_plugins_installed_by_params(self, client, param):
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value={}) as patch_get_plugin_installed:
            resp = await client.get('/foglamp/plugins/installed?type={}'.format(param))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'plugins': {}} == json_response
        patch_get_plugin_installed.assert_called_once_with(param.lower())

    async def test_bad_get_plugins_installed(self, client):
        resp = await client.get('/foglamp/plugins/installed?type=blah')
        assert 400 == resp.status
        assert "Invalid plugin type. Must be 'north' or 'south'." == resp.reason
