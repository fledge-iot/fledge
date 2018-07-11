# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import os
import copy
from unittest.mock import MagicMock, patch
import pytest
from foglamp.common.plugin_discovery import PluginDiscovery


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "plugin-discovery")
class TestPluginDiscovery:
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

    def test_get_plugins_installed_type_none(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_north_folders
            yield TestPluginDiscovery.mock_south_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value = next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config", side_effect= TestPluginDiscovery.mock_plugins_config)

        plugins = PluginDiscovery.get_plugins_installed()
        assert TestPluginDiscovery.mock_plugins_config == plugins
        assert 2 == mock_get_folders.call_count
        assert 4 == mock_get_plugin_config.call_count

    def test_get_plugins_installed_type_north(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_north_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value = next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config", side_effect= TestPluginDiscovery.mock_plugins_north_config)

        plugins = PluginDiscovery.get_plugins_installed("north")
        assert TestPluginDiscovery.mock_plugins_north_config == plugins
        assert 1 == mock_get_folders.call_count
        assert 2 == mock_get_plugin_config.call_count

    def test_get_plugins_installed_type_south(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_south_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value = next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config", side_effect= TestPluginDiscovery.mock_plugins_south_config)

        plugins = PluginDiscovery.get_plugins_installed("south")
        assert TestPluginDiscovery.mock_plugins_south_config == plugins
        assert 1 == mock_get_folders.call_count
        assert 2 == mock_get_plugin_config.call_count

    def test_fetch_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_north_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value = next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config", side_effect= TestPluginDiscovery.mock_plugins_north_config)

        plugins = PluginDiscovery.fetch_plugins_installed("north")
        assert TestPluginDiscovery.mock_plugins_north_config == plugins
        assert 1 == mock_get_folders.call_count
        assert 2 == mock_get_plugin_config.call_count

    def test_get_plugin_folders(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            listdir = copy.deepcopy(TestPluginDiscovery.mock_north_folders)
            listdir.extend(["__init__", "empty", "common"])
            yield listdir

        mock_os_listdir = mocker.patch.object(os, "listdir", return_value = next(mock_folders()))
        mock_os_isdir = mocker.patch.object(os.path, "isdir", return_value = True)

        plugin_folders = PluginDiscovery.get_plugin_folders("north")
        assert TestPluginDiscovery.mock_north_folders == plugin_folders

    def test_get_plugin_config(self):
        mock_plugin_info = {
                'name': "furnace4",
                'version': "1.1",
                'type': "south",
                'interface': "1.0",
                'config': {
                            'plugin': {
                                'description': "Modbus RTU plugin",
                                'type': 'string',
                                'default': 'modbus'
                            }
            }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)

        with patch('builtins.__import__', return_value=mock):
            actual = PluginDiscovery.get_plugin_config("modbus", "south")
            expected = TestPluginDiscovery.mock_plugins_south_config[0]
            # TODO: Investigate why import json at module top is not working and also why
            #       assert expected == actual is not working
            import json
            assert json.loads(expected) == json.loads(actual)
