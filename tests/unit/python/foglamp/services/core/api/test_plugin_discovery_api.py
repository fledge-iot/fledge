# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import json
from unittest.mock import MagicMock, patch
import pytest
from aiohttp import web
from foglamp.services.core import routes
from foglamp.common.plugin_discovery import PluginDiscovery


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "plugin-discovery")
class TestPluginDiscoveryApi:
    mock_north_folders = ["OMF", "foglamp-north"]
    mock_south_folders = ["modbus", "http"]
    mock_all_folders = ["OMF", "foglamp-north", "modbus", "http"]
    mock_plugins_config = [
        {
            "name": "OMF",
            "type": "north",
            "description": "OMF to PI connector relay",
            "version": "1.2"
        },
        {
            "name": "foglamp-north",
            "type": "north",
            "description": "Northbound FogLAMP aggregator",
            "version": "1.0"
        },
        {
            "name": "modbus",
            "type": "south",
            "description": "Modbus RTU plugin",
            "version": "1.1"
        },
        {
            "name": "http",
            "type": "south",
            "description": "HTTP request plugin",
            "version": "1.4"
        }
    ]
    mock_plugins_north_config = [
        {
            "name": "OMF",
            "type": "north",
            "description": "OMF to PI connector relay",
            "version": "1.2"
        },
        {
            "name": "foglamp-north",
            "type": "north",
            "description": "Northbound FogLAMP aggregator",
            "version": "1.0"
        }
    ]
    mock_plugins_south_config = [
        {
            "name": "modbus",
            "type": "south",
            "description": "Modbus RTU plugin",
            "version": "1.1"
        },
        {
            "name": "http",
            "type": "south",
            "description": "HTTP request plugin",
            "version": "1.4"
        }
    ]
    mock_north_plugins = {
        "plugins": [
            {
                "name": "OMF",
                "type": "north",
                "description": "OMF to PI connector relay",
                "version": "1.2"
            },
            {
                "name": "foglamp-north",
                "type": "north",
                "description": "Northbound FogLAMP aggregator",
                "version": "1.0"
            }
        ]
    }
    mock_south_plugins = {
        "plugins": [
            {
                "name": "modbus",
                "type": "south",
                "description": "Modbus RTU plugin",
                "version": "1.1"
            },
            {
                "name": "http",
                "type": "south",
                "description": "HTTP request plugin",
                "version": "1.4"
            }
        ]
    }
    mock_all_plugins = {
        "plugins": [
            {
                "name": "OMF",
                "type": "north",
                "description": "OMF to PI connector relay",
                "version": "1.2"
            },
            {
                "name": "foglamp-north",
                "type": "north",
                "description": "Northbound FogLAMP aggregator",
                "version": "1.0"
            },
            {
                "name": "modbus",
                "type": "south",
                "description": "Modbus RTU plugin",
                "version": "1.1"
            },
            {
                "name": "http",
                "type": "south",
                "description": "HTTP request plugin",
                "version": "1.4"
            }
        ]
    }

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_plugins_installed(self, client, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscoveryApi.mock_north_folders
            yield TestPluginDiscoveryApi.mock_south_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value = next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config", side_effect= TestPluginDiscoveryApi.mock_plugins_config)

        resp = await client.get('/foglamp/plugins/installed')
        assert 200 == resp.status
        res = await resp.json()

        assert TestPluginDiscoveryApi.mock_all_plugins == res

    async def test_get_plugins_installed_north(self, client, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscoveryApi.mock_north_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value = next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config", side_effect= TestPluginDiscoveryApi.mock_plugins_north_config)

        resp = await client.get("/foglamp/plugins/installed?type=north")
        assert 200 == resp.status
        res = await resp.json()

        assert TestPluginDiscoveryApi.mock_north_plugins == res

    async def test_get_plugins_installed_south(self, client, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscoveryApi.mock_south_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value = next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config", side_effect= TestPluginDiscoveryApi.mock_plugins_south_config)

        resp = await client.get("/foglamp/plugins/installed?type=south")
        assert 200 == resp.status
        res = await resp.json()

        assert TestPluginDiscoveryApi.mock_south_plugins == res

    # TODO: Add negative tests after __import__ mocking is resolved.
