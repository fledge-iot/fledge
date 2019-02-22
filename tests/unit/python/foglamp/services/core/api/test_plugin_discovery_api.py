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

    @pytest.mark.parametrize("method, result, is_config", [
        ("/foglamp/plugins/installed", {"name": "sinusoid", "version": "1.0", "type": "south", "description": "sinusoid plugin"}, False),
        ("/foglamp/plugins/installed?config=true",
         {"name": "sinusoid", "version": "1.0", "type": "south", "description": "sinusoid plugin", "config": {
             "plugin": {"description": "sinusoid plugin", "type": "string", "default": "sinusoid", "readonly": "true"}}}, True),
        ("/foglamp/plugins/installed?config=false", {"name": "sinusoid", "version": "1.0", "type": "south", "description": "sinusoid plugin"}, False)
    ])
    async def test_get_plugins_installed(self, client, method, result, is_config):
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=result) as patch_get_plugin_installed:
            resp = await client.get('{}'.format(method))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'plugins': result} == json_response
        patch_get_plugin_installed.assert_called_once_with(None, is_config)

    @pytest.mark.parametrize("param", [
        "north",
        "south",
        "North",
        "South",
        "NORTH",
        "SOUTH",
        "filter",
        "Filter",
        "FILTER",
        "notify",
        "NOTIFY",
        "rule",
        "Rule",
        "RULE"
    ])
    async def test_get_plugins_installed_by_params(self, client, param):
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value={}) as patch_get_plugin_installed:
            resp = await client.get('/foglamp/plugins/installed?type={}'.format(param))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'plugins': {}} == json_response
        patch_get_plugin_installed.assert_called_once_with(param.lower(), False)

    @pytest.mark.parametrize("param, direction, result, is_config", [
        ("?type=north&config=false", "north", {"name": "http", "version": "1.0.0", "type": "north", "description": "HTTP North-C plugin"}, False),
        ("?type=south&config=false", "south", {"name": "sinusoid", "version": "1.0", "type": "south", "description": "sinusoid plugin"}, False),
        ("?type=filter&config=false", "filter", {"name": "scale", "version": "1.0.0", "type": "filter", "description": "Filter Scale plugin"}, False),
        ("?type=notify&config=false", "notify", {"name": "email", "version": "1.0.0", "type": "notify", "description": "Email notification plugin"}, False),
        ("?type=rule&config=false", "rule", {"name": "OverMaxRule", "version": "1.0.0", "type": "rule", "description": "The OverMaxRule notification rule plugin"}, False),
        ("?type=north&config=true", "north", {"name": "http", "version": "1.0.0", "type": "north", "description": "HTTP North-C plugin",
                                              "config": {"plugin": {"description": "HTTP North-C plugin", "type": "string", "default": "http-north"}}}, True),
        ("?type=south&config=true", "south", {"name": "sinusoid", "version": "1.0", "type": "south", "description": "sinusoid plugin",
                                              "config": {"plugin": {"description": "sinusoid plugin", "type": "string", "default": "sinusoid", "readonly": "true"}}}, True),
        ("?type=filter&config=true", "filter", {"name": "scale", "version": "1.0.0", "type": "filter", "description": "Filter Scale plugin",
                                                "config": {"offset": {"default": "0.0", "type": "float", "description": "A constant offset"}, "factor": {"default": "100.0", "type": "float", "description": "Scale factor for a reading."}, "plugin": {"default": "scale", "type": "string", "description": "Scale filter plugin"}, "enable": {"default": "false", "type": "boolean", "description": "A switch that can be used to enable or disable."}}}, True),
        ("?type=notify&config=true", "notify", {"name": "email", "version": "1.0.0", "type": "notify", "description": "Email notification plugin",
                                                "config": {"plugin": {"type": "string", "description": "Email notification plugin", "default": "email"}}}, True),
        ("?type=rule&config=true", "rule", {"name": "OverMaxRule", "version": "1.0.0", "type": "rule", "description": "The OverMaxRule notification rule plugin",
                                            "config": {"plugin": {"type": "string", "description": "The OverMaxRule notification rule plugin", "default": "OverMaxRule"}}}, True)
    ])
    async def test_get_plugins_installed_by_type_and_config(self, client, param, direction, result, is_config):
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=result) as patch_get_plugin_installed:
            resp = await client.get('/foglamp/plugins/installed{}'.format(param))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'plugins': result} == json_response
        patch_get_plugin_installed.assert_called_once_with(direction, is_config)

    @pytest.mark.parametrize("param, message", [
        ("?type=blah", "Invalid plugin type. Must be 'north' or 'south' or 'filter' or 'notify' or 'rule'."),
        ("?config=blah", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=False", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=True", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=f", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=t", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=1", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=Y", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=Yes", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=No&type=north", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?config=TRUE&type=south", 'Only "true", "false", true, false are allowed for value of config.'),
        ("?type=south&config=0", 'Only "true", "false", true, false are allowed for value of config.')
    ])
    async def test_bad_get_plugins_installed(self, client, param, message):
        resp = await client.get('/foglamp/plugins/installed{}'.format(param))
        assert 400 == resp.status
        assert message == resp.reason
