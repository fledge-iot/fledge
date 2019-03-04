# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""shim layer between Python and C++"""

import sys
import json
import logging

from foglamp.common import logger

_LOGGER = logger.setup(__name__, level=logging.WARN)
_plugin = None

_LOGGER.info("Loading shim layer for python plugin '{}' ".format(sys.argv[1]))

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
    _LOGGER.info("plugin_info called")
    handle = _plugin.plugin_info()
    handle['config'] = json.dumps(handle['config'])
    return handle


def plugin_init(config):
    _LOGGER.info("plugin_init called")
    handle = _plugin.plugin_init(json.loads(config))
    # TODO: FOGL-1827 - Config item value must be respected as per type given
    revised_handle = _revised_config_for_json_item(handle)
    return revised_handle


def plugin_poll(handle):
    reading = _plugin.plugin_poll(handle)
    return reading


def plugin_reconfigure(handle, new_config):
    _LOGGER.info("plugin_reconfigure")
    new_handle = _plugin.plugin_reconfigure(handle, json.loads(new_config))
    # TODO: FOGL-1827 - Config item value must be respected as per type given
    revised_handle = _revised_config_for_json_item(new_handle)
    return revised_handle


def plugin_shutdown(handle):
    _LOGGER.info("plugin_shutdown")
    return _plugin.plugin_shutdown(handle)


def plugin_start(handle):
    _LOGGER.info("plugin_start")
    return _plugin.plugin_start(handle)


def plugin_register_ingest(handle, callback, ingest_ref):
    _LOGGER.info("plugin_register_ingest")
    return _plugin.plugin_register_ingest(handle, callback, ingest_ref)


def _revised_config_for_json_item(config):
    # South C server sends "config" argument as string in which all JSON type items' components,
    # 'default' and 'value', gets converted to dict during json.loads(). Hence we need to restore
    # them to str, which is the required format for configuration items.
    revised_config_handle = {}
    for k, v in config.items():
        if isinstance(v, dict):
            if 'type' in v and v['type'] == 'JSON':
                if isinstance(v['default'], dict):
                    v['default'] = json.dumps(v['default'])
                if isinstance(v['value'], dict):
                    v['value'] = json.dumps(v['value'])
        revised_config_handle.update({k: v})
    return revised_config_handle
