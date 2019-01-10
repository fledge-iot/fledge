# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""shim layer between Python and C++"""

import sys
import json
import logging

from foglamp.common import logger

_LOGGER = logger.setup(__name__, level=logging.INFO)
_plugin = None


def _plugin_obj():
    plugin = sys.argv[1]
    plugin_module_path = "foglamp.plugins.south"
    try:
        import_file_name = "{path}.{dir}.{file}".format(path=plugin_module_path, dir=plugin, file=plugin)
        _plugin = __import__(import_file_name, fromlist=[''])
    except ImportError as ex:
        _LOGGER.exception("Plugin %s import problem from path %s. %s", plugin, plugin_module_path, str(ex))
    except Exception as ex:
        _LOGGER.exception("Failed to load plugin. %s", str(ex))
    return _plugin


_plugin = _plugin_obj()


def plugin_info():
    handle = _plugin.plugin_info()
    handle['config'] = json.dumps(handle['config'])
    return handle


def plugin_init(config):
    handle = _plugin.plugin_init(json.loads(config))
    return handle


def plugin_poll(handle):
    reading = _plugin.plugin_poll(handle)
    return reading


def plugin_reconfigure(handle, new_config):
    new_handle = _plugin.plugin_reconfigure(handle, json.loads(new_config))
    return new_handle


def plugin_shutdown(handle):
    return _plugin.plugin_shutdown(handle)
