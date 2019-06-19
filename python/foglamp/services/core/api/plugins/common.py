# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Definitions"""
import logging
import os
import platform
import subprocess
import json
import importlib.util
from typing import Dict

from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_ROOT, _FOGLAMP_DATA, _FOGLAMP_PLUGIN_PATH
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
                        # Merge default and other configuration fields of both connection plugin and hybrid plugin with intersection of 'config' keys
                        # Use Hybrid Plugin name and description defined in json file
                        temp = jdoc['config']
                        temp['plugin']['default'] = plugin_name
                        temp['plugin']['description'] = data['description']
                        for _key in intersection:
                            config_item_keys_a = set(temp[_key].keys())
                            config_item_keys_b = set(data['defaults'][_key].keys())
                            config_item_intersection = config_item_keys_a & config_item_keys_b
                            for _config_key in config_item_intersection:
                                if temp[_key]['type'] == 'JSON':
                                    temp[_key][_config_key] = json.dumps(data['defaults'][_key][_config_key])
                                elif temp[_key]['type'] == 'enumeration':
                                    temp[_key][_config_key] = data['defaults'][_key][_config_key]
                                else:
                                    temp[_key][_config_key] = str(data['defaults'][_key][_config_key])
                        if is_config:
                            plugin_info.update({'config': temp})
                    else:
                        _logger.warning("{} hybrid plugin is not installed which is required for {}".format(connection_name, plugin_name))
                else:
                    _logger.warning("{} hybrid plugin is not installed which is required for {}".format(connection_name, plugin_name))
            else:
                raise Exception('Required {} keys are missing for json file'.format(json_file_keys))
    return plugin_info


def fetch_available_packages(package_type: str = "") -> list:
    plugins = []
    plugin_dir = '/plugins/'
    _PATH = _FOGLAMP_DATA + plugin_dir if _FOGLAMP_DATA else _FOGLAMP_ROOT + '/data{}'.format(plugin_dir)
    stdout_file_name = "output.txt"
    stdout_file_path = "/{}/{}".format(_PATH, stdout_file_name)

    if not os.path.exists(_PATH):
        os.makedirs(_PATH)

    _platform = platform.platform()

    pkg_type = "" if package_type is None else package_type
    if 'centos' in _platform or 'redhat' in _platform:
        cmd = "sudo yum list available foglamp-{}\* | grep foglamp | cut -d . -f1 > {} 2>&1".\
            format(pkg_type, stdout_file_path)
    else:
        cmd = "sudo apt list | grep foglamp-{} | grep -v installed | cut -d / -f1  > {} 2>&1".\
            format(pkg_type, stdout_file_path)

    ret_code = os.system(cmd)
    if ret_code != 0:
        raise ValueError

    with open("{}".format(stdout_file_path), 'r') as fh:
        for line in fh:
            line = line.rstrip("\n")
            plugins.append(line)

    # Remove stdout file
    arg1 = utils._find_c_util('cmdutil')
    # FIXME:(low priority)special case for cmdutil when FOGLAMP_DATA we do not need absolute path for filename deletion
    # and cmdutil commands only works with make install
    # arg2 = plugin_dir if _FOGLAMP_DATA else '/data{}'.format(plugin_dir)
    arg2 = '/data{}'.format(plugin_dir)
    cmd = "{} rm {}{}".format(arg1, arg2, stdout_file_name)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    return plugins
