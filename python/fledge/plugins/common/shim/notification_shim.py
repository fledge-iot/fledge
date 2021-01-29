# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""shim layer between Python and C++"""

import os
import importlib.util
import sys
import json
import logging

from fledge.common import logger
from fledge.common.common import _FLEDGE_ROOT
from fledge.services.core.api.plugins import common

_LOGGER = logger.setup(__name__, level=logging.WARN)
_plugin = None

_LOGGER.info("Loading shim layer for python plugin '{}', type '{}' ".format(sys.argv[1], sys.argv[2]))

def _plugin_obj():
    global _plugin
    plugin = sys.argv[1]
    plugin_type = sys.argv[2]
    plugin_module_path = "{}/python/fledge/plugins/{}/{}".format(_FLEDGE_ROOT, plugin_type, plugin)
    _plugin = common.load_python_plugin(plugin_module_path, plugin, plugin_type)
    return _plugin

_plugin = _plugin_obj()

def plugin_info():
    global _plugin
    handle = _plugin.plugin_info()
    handle['config'] = json.dumps(handle['config'])
    return handle

def plugin_init(config):
    global _plugin
    handle = _plugin.plugin_init(json.loads(config))
    # TODO: FOGL-1827 - Config item value must be respected as per type given
    revised_handle = _revised_config_for_json_item(handle)
    return revised_handle

def plugin_reason(handle):
    global _plugin
    return json.dumps(_plugin.plugin_reason(handle))

def plugin_eval(handle, data):
    global _plugin
    # data is a C string
    return _plugin.plugin_eval(handle, data)

def plugin_triggers(handle):
    global _plugin
    return json.dumps(_plugin.plugin_triggers(handle))

def plugin_deliver(handle, deliveryName, notificationName, triggerReason, customMessage):
    global _plugin
    return _plugin.plugin_deliver(handle, deliveryName, notificationName, triggerReason, customMessage)

def plugin_reconfigure(handle, new_config):
    global _plugin
    new_handle = _plugin.plugin_reconfigure(handle, json.loads(new_config))
    # TODO: FOGL-1827 - Config item value must be respected as per type given
    revised_handle = _revised_config_for_json_item(new_handle)
    return revised_handle

def plugin_shutdown(handle):
    global _plugin
    return _plugin.plugin_shutdown(handle)

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
