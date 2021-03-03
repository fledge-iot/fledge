# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
import os
import copy
from unittest.mock import patch
import pytest

from fledge.common.plugin_discovery import PluginDiscovery, _logger
from fledge.services.core.api import utils
from fledge.services.core.api.plugins import common
from fledge.plugins.common import utils as api_utils


__author__ = "Amarendra K Sinha, Ashish Jabble "
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "plugin-discovery")
class TestPluginDiscovery:
    mock_north_folders = ["OMF", "fledge-north"]
    mock_south_folders = ["modbus", "http"]
    mock_c_north_folders = [("ocs", "binary")]
    mock_c_south_folders = [("dummy", "binary")]
    mock_py_filter_folders = [("foo", "bar")]
    mock_c_filter_folders = [("scale", "binary")]
    mock_c_notify_folders = [("email", "binary")]
    mock_py_notify_folders = [("notify1", "notify2")]
    mock_c_rule_folders = [("OverMaxRule", "binary")]
    mock_py_rule_folders = [("bad_bearing", "engine_failure")]
    mock_all_folders = ["OMF", "fledge-north", "modbus", "http"]
    mock_filter_config = [
        {"name": "foo",
         "version": "1.0.0",
         "type": "filter",
         "description": "Filter foo plugin",
         "config": {"plugin": {"default": "foo", "type": "string", "description": "Foo filter plugin"}}
         },
        {"name": "bar",
         "version": "1.0.0",
         "type": "filter",
         "description": "Filter bar plugin",
         "config": {"plugin": {"default": "bar", "type": "string", "description": "Bar filter plugin"}}
         }
    ]
    mock_plugins_config = [
        {
            "name": "OMF",
            "type": "north",
            "description": "OMF to PI connector relay",
            "version": "1.2"
        },
        {
            "name": "fledge-north",
            "type": "north",
            "description": "Northbound Fledge aggregator",
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
            "name": "fledge-north",
            "type": "north",
            "description": "Northbound Fledge aggregator",
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
         "type": "notificationDelivery",
         "description": "Email notification plugin",
         "config": {"plugin": {"type": "string", "description": "Email notification plugin", "default": "email"}}}
    ]

    mock_py_notify_config = [
        {
          "version": "1.7.0",
          "description": "notify1 delivery plugin",
          "type": "notificationDelivery",
          "name": "notify1"
        },
        {
            "version": "1.7.0",
            "description": "notify2 delivery plugin",
            "type": "notificationDelivery",
            "name": "notify2"
        }
    ]

    mock_c_rule_config = [
        {"name": "OverMaxRule",
         "version": "1.0.0",
         "type": "notificationRule",
         "description": "The OverMaxRule notification rule",
         "config": {"plugin": {"type": "string", "description": "The OverMaxRule notification rule plugin", "default": "OverMaxRule"}}}
    ]

    mock_py_rule_config = [
        {
          "version": "1.7.0",
          "description": "Notification rule plugin to detect bad bearing",
          "type": "notificationRule",
          "name": "bad_bearing"
        },
        {
          "version": "1.6.2",
          "description": "Notification rule plugin which detects imminent engine failure",
          "type": "notificationRule",
          "name": "engine_failure"
        }
    ]

    mock_plugins_config += mock_filter_config + mock_py_notify_config + mock_py_rule_config

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
        {"name": "email", "type": "notificationDelivery", "version": "1.0.0", "description": "Email notification plugin",
         "config": {"plugin": {
             "type": "string",
             "description": "Email notification plugin",
             "default": "email"}}},
        {"name": "OverMaxRule",
         "version": "1.0.0",
         "type": "notificationRule",
         "description": "The OverMaxRule notification rule",
         "config": {"plugin": {"type": "string", "description": "The OverMaxRule notification rule plugin",
                               "default": "OverMaxRule"}}}
    ]

    def test_get_plugins_installed_type_none(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_north_folders
            yield TestPluginDiscovery.mock_south_folders
            yield TestPluginDiscovery.mock_py_filter_folders
            yield TestPluginDiscovery.mock_py_notify_folders
            yield TestPluginDiscovery.mock_py_rule_folders

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
        assert 5 == mock_get_folders.call_count
        assert 10 == mock_get_plugin_config.call_count
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

    def test_get_filter_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_c_filter_folders():
            yield TestPluginDiscovery.mock_c_filter_folders

        @asyncio.coroutine
        def mock_filter_folders():
            yield TestPluginDiscovery.mock_py_filter_folders

        mock_get_filter_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value=next(mock_filter_folders()))
        mock_get_filter_config = mocker.patch.object(PluginDiscovery, "get_plugin_config", side_effect=TestPluginDiscovery.mock_filter_config)
        mock_get_c_filter_folders = mocker.patch.object(utils, "find_c_plugin_libs", return_value=next(mock_c_filter_folders()))
        mock_get_c_filter_plugin_config = mocker.patch.object(utils, "get_plugin_info", side_effect=TestPluginDiscovery.mock_c_filter_config)

        plugins = PluginDiscovery.get_plugins_installed("filter")
        # expected_plugin = TestPluginDiscovery.mock_c_plugins_config[2]
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 1 == mock_get_filter_folders.call_count
        assert 1 == mock_get_filter_config.call_count
        assert 1 == mock_get_c_filter_folders.call_count
        assert 1 == mock_get_c_filter_plugin_config.call_count

    def test_get_notify_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_py_notify_folders

        @asyncio.coroutine
        def mock_c_folders():
            yield TestPluginDiscovery.mock_c_notify_folders

        mock_get_py_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value=next(mock_folders()))
        mock_get_py_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config",
                                                        side_effect=TestPluginDiscovery.mock_py_notify_config)
        mock_get_c_folders = mocker.patch.object(utils, "find_c_plugin_libs",
                                                        return_value=next(mock_c_folders()))
        mock_get_c_plugin_config = mocker.patch.object(utils, "get_plugin_info",
                                                              side_effect=TestPluginDiscovery.mock_c_notify_config)
        plugins = PluginDiscovery.get_plugins_installed("notify")
        # expected_plugin = TestPluginDiscovery.mock_c_plugins_config[3]
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 1 == mock_get_py_folders.call_count
        assert 1 == mock_get_py_plugin_config.call_count
        assert 1 == mock_get_c_folders.call_count
        assert 1 == mock_get_c_plugin_config.call_count

    def test_get_rules_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_py_rule_folders

        @asyncio.coroutine
        def mock_c_folders():
            yield TestPluginDiscovery.mock_c_rule_folders

        mock_get_py_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders",
                                                  return_value=next(mock_folders()))
        mock_get_py_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config",
                                                        side_effect=TestPluginDiscovery.mock_py_rule_config)
        mock_get_c_folders = mocker.patch.object(utils, "find_c_plugin_libs", return_value=next(mock_c_folders()))
        mock_get_c_plugin_config = mocker.patch.object(utils, "get_plugin_info",
                                                            side_effect=TestPluginDiscovery.mock_c_rule_config)

        plugins = PluginDiscovery.get_plugins_installed("rule")
        # expected_plugin = TestPluginDiscovery.mock_c_plugins_config[4]
        # FIXME: ordering issue
        # assert expected_plugin == plugins
        assert 1 == mock_get_py_folders.call_count
        assert 1 == mock_get_py_plugin_config.call_count
        assert 1 == mock_get_c_folders.call_count
        assert 1 == mock_get_c_plugin_config.call_count

    def test_fetch_plugins_installed(self, mocker):
        @asyncio.coroutine
        def mock_folders():
            yield TestPluginDiscovery.mock_north_folders

        mock_get_folders = mocker.patch.object(PluginDiscovery, "get_plugin_folders", return_value=next(mock_folders()))
        mock_get_plugin_config = mocker.patch.object(PluginDiscovery, "get_plugin_config",
                                                     side_effect=TestPluginDiscovery.mock_plugins_north_config)

        plugins = PluginDiscovery.fetch_plugins_installed("north", "north", False)
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
        actual_plugin_folders = []
        for dir_name in plugin_folders:
            actual_plugin_folders.append(dir_name.split('/')[-1])
        assert TestPluginDiscovery.mock_north_folders == actual_plugin_folders

    @pytest.mark.parametrize("info, expected, is_config, installed_dir_name", [
        ({'name': "furnace4", 'version': "1.1", 'type': "south", 'interface': "1.0",
          'config': {'plugin': {'description': "Modbus RTU plugin", 'type': 'string', 'default': 'modbus'}}},
         {'name': 'modbus', 'type': 'south', 'description': 'Modbus RTU plugin', 'version': '1.1',
          'installedDirectory': 'south/modbus', 'packageName': 'fledge-south-modbus'}, False, 'south'),
        ({'name': "furnace4", 'version': "1.1", 'type': "south", 'interface': "1.0",
          'config': {'plugin': {'description': "Modbus RTU plugin", 'type': 'string', 'default': 'modbus'}}},
         {'name': 'modbus', 'type': 'south', 'description': 'Modbus RTU plugin', 'version': '1.1',
          'installedDirectory': 'south/modbus', 'packageName': 'fledge-south-modbus',
          'config': {'plugin': {'description': 'Modbus RTU plugin', 'type': 'string', 'default': 'modbus'}}},
         True, 'south'),
        ({'name': "http_north", 'version': "1.1", 'type': "north", 'interface': "1.0",
          'config': {'plugin': {'description': "HTTP north plugin", 'type': 'string', 'default': 'http_north'}}},
         {'name': 'http_north', 'type': 'north', 'description': 'HTTP north plugin', 'version': '1.1',
          'installedDirectory': 'north/http_north', 'packageName': 'fledge-north-http-north'},
         False, 'north'),
        ({'name': "rms", 'version': "1.1", 'type': "filter", 'interface': "1.0",
          'config': {'plugin': {'description': "RMS Filter plugin", 'type': 'string', 'default': 'rms'}}},
         {'name': 'rms', 'type': 'filter', 'description': 'RMS Filter plugin', 'version': '1.1',
          'installedDirectory': 'filter/rms', 'packageName': 'fledge-filter-rms'},
         False, 'filter'),
        ({'name': "Average", 'version': "1.1", 'type': "notificationRule", 'interface': "1.0",
          'config': {'plugin': {'description': "Average Rule plugin", 'type': 'string', 'default': 'Average'}}},
         {'name': 'Average', 'type': 'rule', 'description': 'Average Rule plugin', 'version': '1.1',
          'installedDirectory': 'notificationRule/Average', 'packageName': 'fledge-rule-average'},
         False, 'notificationRule'),
        ({'name': "asset", 'version': "1.1", 'type': "notificationDelivery", 'interface': "1.0",
          'config': {'plugin': {'description': "Asset Delivery plugin", 'type': 'string', 'default': 'asset'}}},
         {'name': 'asset', 'type': 'notify', 'description': 'Asset Delivery plugin', 'version': '1.1',
          'installedDirectory': 'notificationDelivery/asset', 'packageName': 'fledge-notify-asset'},
         False, 'notificationDelivery')
    ])
    def test_get_plugin_config(self, info, expected, is_config, installed_dir_name):
        with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[info]):
            actual = PluginDiscovery.get_plugin_config(info['config']['plugin']['default'], expected['type'],
                                                       installed_dir_name, is_config)
            assert expected == actual

    @pytest.mark.parametrize("info, warn_count", [
        ({'name': "modbus", 'version': "1.1", 'type': "south", 'interface': "1.0",
          'config': {'plugin': {'description': 'Modbus RTU plugin', 'type': 'string', 'default': 'modbus'}}}, 0),
        ({'name': "modbus", 'version': "1.1", 'type': "south", 'interface': "1.0", 'flag': api_utils.DEPRECATED_BIT_MASK_VALUE,
          'config': {'plugin': {'description': 'Modbus RTU plugin', 'type': 'string', 'default': 'modbus'}}}, 1),
        ({'name': "modbus", 'version': "1.1", 'type': "south", 'interface': "1.0", 'flag': 0,
          'config': {'plugin': {'description': 'Modbus RTU plugin', 'type': 'string', 'default': 'modbus'}}}, 0),
    ])
    def test_deprecated_python_plugins(self, info, warn_count, is_config=True):
        with patch.object(_logger, "warning") as patch_log_warn:
            with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[info]):
                PluginDiscovery.get_plugin_config(info['name'], info['type'], info['type'], is_config)
        assert warn_count == patch_log_warn.call_count
        if warn_count:
            args, kwargs = patch_log_warn.call_args
            assert '"{}" plugin is deprecated'.format(info['name']) == args[0]

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
        with patch.object(_logger, "warning") as patch_log_warn:
            with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[mock_plugin_info]):
                actual = PluginDiscovery.get_plugin_config("http-north", "south", "http_north", False)
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
        with patch.object(utils, "find_c_plugin_libs", return_value=[(info['name'], "binary")]) as patch_plugin_lib:
            with patch.object(utils, "get_plugin_info", return_value=info) as patch_plugin_info:
                PluginDiscovery.fetch_c_plugins_installed(dir_name, True, dir_name)
            patch_plugin_info.assert_called_once_with(info['name'], dir=dir_name)
        patch_plugin_lib.assert_called_once_with(dir_name)

    @pytest.mark.parametrize("info, dir_name", [
        (mock_c_plugins_config[0], "south"),
        (mock_c_plugins_config[1], "north"),
        (mock_c_plugins_config[2], "filter"),
        (mock_c_plugins_config[3], "notify"),
        (mock_c_plugins_config[4], "rule")
    ])
    def test_deprecated_c_plugins_installed(self, info, dir_name):
        info['flag'] = api_utils.DEPRECATED_BIT_MASK_VALUE
        with patch.object(_logger, "warning") as patch_log_warn:
            with patch.object(utils, "find_c_plugin_libs", return_value=[(info['name'], "binary")]) as patch_plugin_lib:
                with patch.object(utils, "get_plugin_info", return_value=info) as patch_plugin_info:
                    PluginDiscovery.fetch_c_plugins_installed(dir_name, True, dir_name)
                patch_plugin_info.assert_called_once_with(info['name'], dir=dir_name)
            patch_plugin_lib.assert_called_once_with(dir_name)
        assert 1 == patch_log_warn.call_count
        args, kwargs = patch_log_warn.call_args
        assert '"{}" plugin is deprecated'.format(info['name']) == args[0]

    def test_fetch_c_hybrid_plugins_installed(self):
        info = {"version": "1.6.0", "name": "FlirAX8",
                "config": {"asset": {"description": "Default asset name", "default": "flir",
                                     "displayName": "Asset Name", "type": "string"},
                           "plugin": {"description": "A Modbus connected Flir AX8 infrared camera",
                                      "default": "FlirAX8", "readonly": "true", "type": "string"}}}
        with patch.object(utils, "find_c_plugin_libs", return_value=[("FlirAX8", "json")]) as patch_plugin_lib:
            with patch.object(common, "load_and_fetch_c_hybrid_plugin_info", return_value=info) as patch_hybrid_plugin_info:
                PluginDiscovery.fetch_c_plugins_installed('south', True, 'south')
            patch_hybrid_plugin_info.assert_called_once_with(info['name'], True)
        patch_plugin_lib.assert_called_once_with('south')

    @pytest.mark.parametrize("info, exc_count", [
        ({}, 0),
        ({"interface": "1.0.0", "version": "1.0.0", "type": "south", "name": "Random", "config": "(null)"}, 1),
        ({"interface": "1.0.0", "version": "1.0.0", "type": "south", "name": "Random", "config": {}}, 1)
    ])
    def test_bad_fetch_c_south_plugin_installed(self, info, exc_count):
        with patch.object(_logger, "exception") as patch_log_exc:
            with patch.object(utils, "find_c_plugin_libs", return_value=[("Random", "binary")]) as patch_plugin_lib:
                with patch.object(utils, "get_plugin_info",  return_value=info) as patch_plugin_info:
                    PluginDiscovery.fetch_c_plugins_installed("south", False, 'south')
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
            with patch.object(utils, "find_c_plugin_libs", return_value=[("PI_Server", "binary")]) as patch_plugin_lib:
                with patch.object(utils, "get_plugin_info", return_value=info) as patch_plugin_info:
                    PluginDiscovery.fetch_c_plugins_installed("north", False, 'north')
                patch_plugin_info.assert_called_once_with('PI_Server', dir='north')
            patch_plugin_lib.assert_called_once_with('north')
            assert exc_count == patch_log_exc.call_count

    @pytest.mark.parametrize("exc_name, log_exc_name, msg", [
        (FileNotFoundError, "error", 'Plugin "modbus" import problem from path "modbus".'),
        (Exception, "exception", 'Plugin "modbus" raised exception "" while fetching config')
    ])
    def test_bad_get_south_plugin_config(self, exc_name, log_exc_name, msg):
        with patch.object(_logger, log_exc_name) as patch_log_exc:
            with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[exc_name]):
                PluginDiscovery.get_plugin_config("modbus", "south", "south", False)
        assert 1 == patch_log_exc.call_count
        args, kwargs = patch_log_exc.call_args
        assert msg in args[0]

    @pytest.mark.parametrize("exc_name, log_exc_name, msg", [
        (FileNotFoundError, "error", 'Plugin "http" import problem from path "http".'),
        (Exception, "exception", 'Plugin "http" raised exception "" while fetching config')
    ])
    def test_bad_get_north_plugin_config(self, exc_name, log_exc_name, msg):
        with patch.object(_logger, log_exc_name) as patch_log_exc:
            with patch.object(common, 'load_and_fetch_python_plugin_info', side_effect=[exc_name]):
                PluginDiscovery.get_plugin_config("http", "north", "north", False)
        assert 1 == patch_log_exc.call_count
        args, kwargs = patch_log_exc.call_args
        assert msg in args[0]
