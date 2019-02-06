# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import os
import copy
from unittest.mock import MagicMock, patch
import pytest

from foglamp.common.plugin_discovery import PluginDiscovery, _logger
from foglamp.services.core.api import utils

__author__ = "Amarendra K Sinha, Ashish Jabble "
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "plugin-discovery")
class TestPluginDiscovery:
    mock_north_folders = ["OMF", "foglamp-north"]
    mock_south_folders = ["modbus", "http"]
    mock_c_north_folders = ["ocs"]
    mock_c_south_folders = ["dummy"]
    mock_c_filter_folders = ["scale"]
    mock_c_notify_folders = ["email"]
    mock_c_rule_folders = ["OverMaxRule"]
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
    mock_c_plugins_north_config = [
        {"interface": "1.0.0",
         "name": "OCS",
         "version": "1.0.0",
         "config": {
             "plugin": {
                 "default": "ocs",
                 "type": "string",
                 "description": "OCS North C Plugin"
             }
         }
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

    mock_c_plugins_south_config = [
        {"interface": "1.0.0",
         "version": "1.0.0",
         "type": "south",
         "name": "Dummy",
         "config": {"plugin": {"type": "string", "description": "Dummy C south plugin", "default": "dummy"}}
         }
    ]

    mock_c_filter_config = [
        {"name": "scale",
         "version": "1.0.0",
         "type": "filter",
         "description": "Filter Scale plugin",
         "config": {"plugin": {"default": "scale", "type": "string", "description": "Scale filter plugin"}}}
    ]

    mock_c_notify_config = [
        {"name": "email",
         "version": "1.0.0",
         "type": "notify",
         "description": "Email notification plugin",
         "config": {"plugin": {"type": "string", "description": "Email notification plugin", "default": "email"}}}
    ]

    mock_c_rule_config = [
        {"name": "OverMaxRule",
         "version": "1.0.0",
         "type": "rule",
         "description": "The OverMaxRule notification rule",
         "config": {"plugin": {"type": "string", "description": "The OverMaxRule notification rule plugin", "default": "OverMaxRule"}}}
    ]
    mock_c_plugins_config = [
        {"interface": "1.0.0",
         "version": "1.0.0",
         "type": "south",
         "name": "Dummy",
         "config": {"plugin": {"type": "string", "description": "Dummy C south plugin", "default": "dummy"}}
         },
        {"interface": "1.0.0",
         "name": "OCS",
         "version": "1.0.0",
         "config": {
             "plugin": {
                 "default": "ocs",
                 "type": "string",
                 "description": "OMF North C Plugin"
             }
         }
         },
        {"name": "scale", "version": "1.0.0", "type": "filter", "description": "Filter Scale plugin",
         "config": {
             "plugin": {
                 "default": "scale",
                 "type": "string",
                 "description": "Scale filter plugin"}}},
        {"name": "email", "type": "notify", "version": "1.0.0", "description": "Email notification plugin",
         "config": {"plugin": {
             "type": "string",
             "description": "Email notification plugin",
             "default": "email"}}},
        {"name": "OverMaxRule",
         "version": "1.0.0",
         "type": "rule",
         "description": "The OverMaxRule notification rule",
         "config": {"plugin": {"type": "string", "description": "The OverMaxRule notification rule plugin",
                               "default": "OverMaxRule"}}}
    ]

    def test_get_plugins_installed_type_none(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_north_folders
            yield TestPluginDiscovery.mock_south_folders

        @asyncio.coroutine
        def mock_c_folders():
            yield TestPluginDiscovery.mock_c_north_folders
            yield TestPluginDiscovery.mock_c_south_folders
            yield TestPluginDiscovery.mock_c_filter_folders
            yield TestPluginDiscovery.mock_c_notify_folders
            yield TestPluginDiscovery.mock_c_rule_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value=next(mock_folders()))
        mock_get_c_folders = mocker.patch.object(utils, "find_c_plugin_libs", return_value=next(mock_c_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config",
                                                     side_effect=TestPluginDiscovery.mock_plugins_config)
        mock_get_c_plugin_config = mocker.patch.object(utils, "get_plugin_info",
                                                       side_effect=TestPluginDiscovery.mock_c_plugins_config)

        plugins = PluginDiscovery.get_plugins_installed()
        expected_plugin = TestPluginDiscovery.mock_plugins_config
        expected_plugin.extend(TestPluginDiscovery.mock_c_plugins_config)
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 2 == mock_get_folders.call_count
        assert 4 == mock_get_plugin_config.call_count
        assert 5 == mock_get_c_folders.call_count
        assert 5 == mock_get_c_plugin_config.call_count

    def test_get_plugins_installed_type_north(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_north_folders

        @asyncio.coroutine
        def mock_c_folders():
            yield TestPluginDiscovery.mock_c_north_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value=next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config",
                                                     side_effect=TestPluginDiscovery.mock_plugins_north_config)
        mock_get_c_folders = mocker.patch.object(utils, "find_c_plugin_libs", return_value=next(mock_c_folders()))
        mock_get_c_plugin_config = mocker.patch.object(utils, "get_plugin_info",
                                                       side_effect=TestPluginDiscovery.mock_c_plugins_north_config)

        plugins = PluginDiscovery.get_plugins_installed("north")
        expected_plugin = TestPluginDiscovery.mock_plugins_north_config
        expected_plugin.extend(TestPluginDiscovery.mock_c_plugins_north_config)
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 1 == mock_get_folders.call_count
        assert 2 == mock_get_plugin_config.call_count
        assert 1 == mock_get_c_folders.call_count
        assert 1 == mock_get_c_plugin_config.call_count

    def test_get_plugins_installed_type_south(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_south_folders

        @asyncio.coroutine
        def mock_c_folders():
            yield TestPluginDiscovery.mock_c_south_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value=next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config",
                                                     side_effect=TestPluginDiscovery.mock_plugins_south_config)
        mock_get_c_folders = mocker.patch.object(utils, "find_c_plugin_libs", return_value=next(mock_c_folders()))
        mock_get_c_plugin_config = mocker.patch.object(utils, "get_plugin_info",
                                                       side_effect=TestPluginDiscovery.mock_c_plugins_south_config)

        plugins = PluginDiscovery.get_plugins_installed("south")
        expected_plugin = TestPluginDiscovery.mock_plugins_south_config
        expected_plugin.extend(TestPluginDiscovery.mock_c_plugins_south_config)
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 1 == mock_get_folders.call_count
        assert 2 == mock_get_plugin_config.call_count
        assert 1 == mock_get_c_folders.call_count
        assert 1 == mock_get_c_plugin_config.call_count

    def test_get_c_filter_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_filter_folders():
            yield TestPluginDiscovery.mock_c_filter_folders

        mock_get_c_filter_folders = mocker.patch.object(utils, "find_c_plugin_libs", return_value=next(mock_filter_folders()))
        mock_get_c_filter_plugin_config = mocker.patch.object(utils, "get_plugin_info", side_effect=TestPluginDiscovery.mock_c_filter_config)

        plugins = PluginDiscovery.get_plugins_installed("filter")
        # expected_plugin = TestPluginDiscovery.mock_c_plugins_config[2]
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 1 == mock_get_c_filter_folders.call_count
        assert 1 == mock_get_c_filter_plugin_config.call_count

    def test_get_c_notify_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_notify_folders():
            yield TestPluginDiscovery.mock_c_notify_folders

        mock_get_c_notify_folders = mocker.patch.object(utils, "find_c_plugin_libs", return_value=next(mock_notify_folders()))
        mock_get_c_notify_plugin_config = mocker.patch.object(utils, "get_plugin_info", side_effect=TestPluginDiscovery.mock_c_notify_config)

        plugins = PluginDiscovery.get_plugins_installed("notify")
        # expected_plugin = TestPluginDiscovery.mock_c_plugins_config[3]
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 1 == mock_get_c_notify_folders.call_count
        assert 1 == mock_get_c_notify_plugin_config.call_count

    def test_get_c_rules_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_rule_folders():
            yield TestPluginDiscovery.mock_c_rule_folders

        mock_get_c_rule_folders = mocker.patch.object(utils, "find_c_plugin_libs", return_value=next(mock_rule_folders()))
        mock_get_c_rule_plugin_config = mocker.patch.object(utils, "get_plugin_info", side_effect=TestPluginDiscovery.mock_c_rule_config)

        plugins = PluginDiscovery.get_plugins_installed("rule")
        # expected_plugin = TestPluginDiscovery.mock_c_plugins_config[4]
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 1 == mock_get_c_rule_folders.call_count
        assert 1 == mock_get_c_rule_plugin_config.call_count

    def test_fetch_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_north_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value=next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config",
                                                     side_effect=TestPluginDiscovery.mock_plugins_north_config)

        plugins = PluginDiscovery.fetch_plugins_installed("north", False)
        # FIXME: below line is failing when in suite
        # assert TestPluginDiscovery.mock_plugins_north_config == plugins
        assert 1 == mock_get_folders.call_count
        assert 2 == mock_get_plugin_config.call_count

    def test_get_plugin_folders(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            listdir = copy.deepcopy(TestPluginDiscovery.mock_north_folders)
            listdir.extend(["__init__", "empty", "common"])
            yield listdir

        mocker.patch.object(os, "listdir", return_value=next(mock_folders()))
        mocker.patch.object(os.path, "isdir", return_value=True)
        plugin_folders = PluginDiscovery.get_plugin_folders("north")
        assert TestPluginDiscovery.mock_north_folders == plugin_folders

    @pytest.mark.parametrize("info, expected, is_config", [
        ({'name': "furnace4", 'version': "1.1", 'type': "south", 'interface': "1.0",
          'config': {'plugin': {'description': "Modbus RTU plugin", 'type': 'string', 'default': 'modbus'}}},
         {'name': 'modbus', 'type': 'south', 'description': 'Modbus RTU plugin', 'version': '1.1'}, False),
        ({'name': "furnace4", 'version': "1.1", 'type': "south", 'interface': "1.0",
          'config': {'plugin': {'description': "Modbus RTU plugin", 'type': 'string', 'default': 'modbus'}}},
         {'name': 'modbus', 'type': 'south', 'description': 'Modbus RTU plugin', 'version': '1.1',
          'config': {'plugin': {'description': 'Modbus RTU plugin', 'type': 'string', 'default': 'modbus'}}}, True)
    ])
    def test_get_plugin_config(self, info, expected, is_config):
        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [info]}
        mock.configure_mock(**attrs)
        with patch('builtins.__import__', return_value=mock):
            actual = PluginDiscovery.get_plugin_config("modbus", "south", is_config)
            assert expected == actual

    def test_bad_get_plugin_config(self):
        mock_plugin_info = {
                'name': "HTTP",
                'version': "1.0.0",
                'type': "north",
                'interface': "1.0.0",
                'config': {
                            'plugin': {
                                'description': "HTTP north plugin",
                                'type': 'string',
                                'default': 'http-north'
                            }
                }
        }

        mock = MagicMock()
        attrs = {"plugin_info.side_effect": [mock_plugin_info]}
        mock.configure_mock(**attrs)
        with patch.object(_logger, "warning") as patch_log_warn:
            with patch('builtins.__import__', return_value=mock):
                actual = PluginDiscovery.get_plugin_config("http-north", "south", False)
                assert actual is None
        patch_log_warn.assert_called_once_with('Plugin http-north is discarded due to invalid type')

    @pytest.mark.parametrize("info, dir_name", [
        (mock_c_plugins_config[0], "south"),
        (mock_c_plugins_config[1], "north"),
        (mock_c_plugins_config[2], "filter"),
        (mock_c_plugins_config[3], "notify"),
        (mock_c_plugins_config[4], "rule")
    ])
    def test_fetch_c_plugins_installed(self, info, dir_name):
        with patch.object(utils, "find_c_plugin_libs", return_value=[info['name']]) as patch_plugin_lib:
            with patch.object(utils, "get_plugin_info", return_value=info) as patch_plugin_info:
                PluginDiscovery.fetch_c_plugins_installed(dir_name, True)
            patch_plugin_info.assert_called_once_with(info['name'], dir=dir_name)
        patch_plugin_lib.assert_called_once_with(dir_name)

    @pytest.mark.parametrize("info, exc_count", [
        ({}, 0),
        ({"interface": "1.0.0", "version": "1.0.0", "type": "south", "name": "Random", "config": "(null)"}, 1),
        ({"interface": "1.0.0", "version": "1.0.0", "type": "south", "name": "Random", "config": {}}, 1)
    ])
    def test_bad_fetch_c_south_plugin_installed(self, info, exc_count):
        with patch.object(_logger, "exception") as patch_log_exc:
            with patch.object(utils, "find_c_plugin_libs", return_value=["Random"]) as patch_plugin_lib:
                with patch.object(utils, "get_plugin_info",  return_value=info) as patch_plugin_info:
                    PluginDiscovery.fetch_c_plugins_installed("south", False)
                patch_plugin_info.assert_called_once_with('Random', dir='south')
            patch_plugin_lib.assert_called_once_with('south')
            assert exc_count == patch_log_exc.call_count

    @pytest.mark.parametrize("info, exc_count", [
        ({}, 0),
        ({"interface": "1.0.0", "version": "1.0.0", "type": "north", "name": "PI_Server", "config": "(null)"}, 1),
        ({"interface": "1.0.0", "version": "1.0.0", "type": "north", "name": "PI_Server", "config": {}}, 1)
    ])
    def test_bad_fetch_c_north_plugin_installed(self, info, exc_count):
        with patch.object(_logger, "exception") as patch_log_exc:
            with patch.object(utils, "find_c_plugin_libs", return_value=["PI_Server"]) as patch_plugin_lib:
                with patch.object(utils, "get_plugin_info", return_value=info) as patch_plugin_info:
                    PluginDiscovery.fetch_c_plugins_installed("north", False)
                patch_plugin_info.assert_called_once_with('PI_Server', dir='north')
            patch_plugin_lib.assert_called_once_with('north')
            assert exc_count == patch_log_exc.call_count

    @pytest.mark.parametrize("exc_name, log_exc_name, msg", [
        (ImportError, "error", 'Plugin "modbus" import problem from path "foglamp.plugins.south".'),
        (Exception, "exception", 'Plugin "modbus" raised exception "" while fetching config')
    ])
    def test_bad_get_south_plugin_config(self, exc_name, log_exc_name, msg):
        mock = MagicMock()
        attrs = {"plugin_info.side_effect": exc_name}
        mock.configure_mock(**attrs)

        with patch.object(_logger, log_exc_name) as patch_log_exc:
            with patch('builtins.__import__', return_value=mock):
                PluginDiscovery.get_plugin_config("modbus", "south", False)
        assert 1 == patch_log_exc.call_count
        args, kwargs = patch_log_exc.call_args
        assert msg in args[0]

    @pytest.mark.parametrize("exc_name, log_exc_name, msg", [
        (ImportError, "error", 'Plugin "http" import problem from path "foglamp.plugins.north".'),
        (Exception, "exception", 'Plugin "http" raised exception "" while fetching config')
    ])
    def test_bad_get_north_plugin_config(self, exc_name, log_exc_name, msg):
        mock = MagicMock()
        attrs = {"plugin_info.side_effect": exc_name}
        mock.configure_mock(**attrs)

        with patch.object(_logger, log_exc_name) as patch_log_exc:
            with patch('builtins.__import__', return_value=mock):
                PluginDiscovery.get_plugin_config("http", "north", False)
        assert 1 == patch_log_exc.call_count
        args, kwargs = patch_log_exc.call_args
        assert msg in args[0]
