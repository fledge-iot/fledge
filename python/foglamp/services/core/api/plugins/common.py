# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Definitions"""
import logging
import os
import importlib.util
from typing import Dict

from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_PLUGIN_PATH

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
