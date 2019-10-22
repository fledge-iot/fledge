# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Definitions"""
import logging
import os
import platform
import json
import glob
import importlib.util
from typing import Dict
from datetime import datetime

from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_ROOT, _FOGLAMP_DATA, _FOGLAMP_PLUGIN_PATH
from foglamp.services.core.api import utils
from foglamp.services.core.api.plugins.exceptions import *
from foglamp.services.core import server

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=logging.INFO)
_NO_OF_FILES_TO_RETAIN = 10


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
        config_items = ['default', 'type', 'description']
        optional_items = ['readonly', 'order', 'length', 'maximum', 'minimum', 'rule', 'deprecated', 'displayName', 'options']
        config_items.extend(optional_items)
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
                            config_item_keys = set(data['defaults'][_key].keys())
                            for _config_key in config_item_keys:
                                if _config_key in config_items:
                                    if temp[_key]['type'] == 'JSON' and _config_key == 'default':
                                        temp[_key][_config_key] = json.dumps(data['defaults'][_key][_config_key])
                                    elif temp[_key]['type'] == 'enumeration' and _config_key == 'default':
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


async def fetch_available_packages(package_type: str = "") -> tuple:
    available_packages = []
    stdout_file_path = create_log_file()
    tmp_log_output_fp = stdout_file_path.split('logs/')[:1][0] + "logs/output.txt"
    _platform = platform.platform()
    pkg_type = "" if package_type is None else package_type
    pkg_mgt = 'apt'
    ret_code = 0
    category = await server.Server._configuration_manager.get_category_all_items("Installation")
    max_update_cat_item = category['maxUpdate']
    pkg_cache_mgr = server.Server._package_cache_manager
    last_accessed_time = pkg_cache_mgr['update']['last_accessed_time']
    now = datetime.now()
    then = last_accessed_time if last_accessed_time else now
    duration_in_sec = (now - then).total_seconds()
    # If max update per day is set to 1, then an update can not occurs until 24 hours after the last accessed update.
    # If set to 2 then this drops to 12 hours between updates, 3 would result in 8 hours between calls and so on.
    if duration_in_sec > (24 / int(max_update_cat_item['value'])) * 60 * 60 or duration_in_sec == 0.0:
        _logger.info("Attempting update on {}".format(now))
        cmd = "sudo {} -y update > {} 2>&1".format(pkg_mgt, stdout_file_path)
        if 'centos' in _platform or 'redhat' in _platform:
            pkg_mgt = 'yum'
            cmd = "sudo {} check-update > {} 2>&1".format(pkg_mgt, stdout_file_path)

        ret_code = os.system(cmd)
        if ret_code == 0:
            pkg_cache_mgr['update']['last_accessed_time'] = now
    else:
        _logger.warning("Maximum update exceeds the limit for the day")

    # TODO: lru cache for below code
    # sudo apt/yum -y install only happens when update is without any error
    if ret_code == 0:
        open(tmp_log_output_fp, "w").close()
        if pkg_mgt == 'yum':
            cmd = "sudo yum list available foglamp-{}\* | grep foglamp | cut -d . -f1 > {} 2>&1".format(
                pkg_type, tmp_log_output_fp)
        else:
            cmd = "sudo apt list | grep foglamp-{} | grep -v installed | cut -d / -f1  > {} 2>&1".format(
                pkg_type, tmp_log_output_fp)
        ret_code = os.system(cmd)

        # Below temporary file is for Output of above command which is needed to return in API response
        with open("{}".format(tmp_log_output_fp), 'r') as fh:
            for line in fh:
                line = line.rstrip("\n")
                available_packages.append(line)

    # combine above output in logs file
    with open("{}".format(stdout_file_path), 'a') as fh:
        fh.write(" \n".join(available_packages))

    # Remove tmp_log_output_fp
    if os.path.isfile(tmp_log_output_fp):
        os.remove(tmp_log_output_fp)

    # relative log file link
    link = "log/" + stdout_file_path.split("/")[-1]
    if ret_code != 0:
        raise PackageError(link)
    return available_packages, link


def create_log_file(plugin_name: str = "") -> str:
    logs_dir = '/logs/'
    _PATH = _FOGLAMP_DATA + logs_dir if _FOGLAMP_DATA else _FOGLAMP_ROOT + '/data{}'.format(logs_dir)
    # YYMMDD-HH-MM-SS-{plugin_name}.log
    file_spec = datetime.now().strftime('%y%m%d-%H-%M-%S')
    log_file_name = "{}-{}.log".format(file_spec, plugin_name) if plugin_name else "{}.log".format(file_spec)

    if not os.path.exists(_PATH):
        os.makedirs(_PATH)

    # Create empty log file name
    open(_PATH + log_file_name, "w").close()

    # A maximum of _NO_OF_FILES_TO_RETAIN log files will be maintained.
    # When it exceeds the limit the very first log file will be removed on the basis of creation time
    files = glob.glob("{}*.log".format(_PATH))
    files.sort(key=os.path.getctime)
    if len(files) > _NO_OF_FILES_TO_RETAIN:
        for f in files[:-_NO_OF_FILES_TO_RETAIN]:
            if os.path.isfile(f):
                os.remove(f)

    return _PATH + log_file_name
