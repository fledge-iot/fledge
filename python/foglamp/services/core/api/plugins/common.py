# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Definitions"""
import logging
import os
import json
import importlib.util
from typing import Dict

from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_ROOT, _FOGLAMP_PLUGIN_PATH
from foglamp.services.core.api import utils


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=logging.INFO)


def load_python_plugin(plugin_module_path: str, plugin: str, _type: str) -> Dict:
    _plugin = None
    try:
        spec = importlib.util.spec_from_file_location("module.name", "{}/{}.py".format(plugin_module_path, plugin))
        _plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_plugin)
    except FileNotFoundError:
        if _FOGLAMP_PLUGIN_PATH:
            plugin_paths = _FOGLAMP_PLUGIN_PATH.split(";")
            for pp in plugin_paths:
                if os.path.isdir(pp):
                    plugin_module_path = "{}/{}/{}".format(pp, _type, plugin)
                    spec = importlib.util.spec_from_file_location("module.name", "{}/{}.py".format(
                        plugin_module_path, plugin))
                    _plugin = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(_plugin)

    return _plugin


def load_and_fetch_python_plugin_info(plugin_module_path: str, plugin: str, _type: str) -> Dict:
    _plugin = load_python_plugin(plugin_module_path, plugin, _type)
    # Fetch configuration from the configuration defined in the plugin
    try:
        plugin_info = _plugin.plugin_info()
        if plugin_info['type'] != _type:
            msg = "Plugin of {} type is not supported".format(plugin_info['type'])
            raise TypeError(msg)
    except Exception as ex:
        _logger.warning("Python plugin not found......{}, try C-plugin".format(ex))
        raise FileNotFoundError
    return plugin_info


def load_and_fetch_c_hybrid_plugin_info(plugin_name: str, is_config: bool, plugin_type='south') -> Dict:
    plugin_info = None
    if plugin_type == 'south':
        plugin_dir = _FOGLAMP_ROOT + '/' + 'plugins' + '/' + plugin_type
        if _FOGLAMP_PLUGIN_PATH:
            plugin_paths = _FOGLAMP_PLUGIN_PATH.split(";")
            for pp in plugin_paths:
                if os.path.isdir(pp):
                    plugin_dir = pp + '/' + plugin_type
        if not os.path.isdir(plugin_dir + '/' + plugin_name):
            plugin_dir = _FOGLAMP_ROOT + '/' + 'plugins' + '/' + plugin_type

        file_name = plugin_dir + '/' + plugin_name + '/' + plugin_name + '.json'
        with open(file_name) as f:
            data = json.load(f)
            json_file_keys = ('connection', 'name', 'defaults', 'description')
            if all(k in data for k in json_file_keys):
                connection_name = data['connection']
                if _FOGLAMP_ROOT + '/' + 'plugins' + '/' + plugin_type or os.path.isdir(plugin_dir + '/' + connection_name):
                    jdoc = utils.get_plugin_info(connection_name, dir=plugin_type)
                    if jdoc:
                        plugin_info = {'name': plugin_name, 'type': plugin_type,
                                       'description': data['description'],
                                       'version': jdoc['version']}
                        keys_a = set(jdoc['config'].keys())
                        keys_b = set(data['defaults'].keys())
                        intersection = keys_a & keys_b
                        # Merge default configuration of both connection plugin and hybrid plugin with intersection of 'config' keys
                        # Use Hybrid Plugin name and description defined in json file
                        temp = jdoc['config']
                        temp['plugin']['default'] = plugin_name
                        temp['plugin']['description'] = data['description']
                        for _key in intersection:
                            temp[_key]['default'] = json.dumps(data['defaults'][_key]['default']) if temp[_key]['type'] == 'JSON' else str(data['defaults'][_key]['default'])
                        if is_config:
                            plugin_info.update({'config': temp})
                    else:
                        _logger.warning("{} hybrid plugin is not installed which is required for {}".format(connection_name, plugin_name))
                else:
                    _logger.warning("{} hybrid plugin is not installed which is required for {}".format(connection_name, plugin_name))
            else:
                raise Exception('Required {} keys are missing for json file'.format(json_file_keys))
    return plugin_info
