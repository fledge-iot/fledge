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
import asyncio

from fledge.common import logger
from fledge.common.common import _FLEDGE_ROOT
from fledge.services.core.api.plugins import common

_LOGGER = logger.setup(__name__, level=logging.WARN)
_plugin = None

_LOGGER.info("Loading shim layer for python plugin '{}' ".format(sys.argv[1]))


def _plugin_obj():
    plugin = sys.argv[1]
    plugin_type = "north"
    plugin_module_path = "{}/python/fledge/plugins/{}/{}".format(_FLEDGE_ROOT, plugin_type, plugin)
    _plugin=common.load_python_plugin(plugin_module_path, plugin, plugin_type)
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
    #if _plugin.plugin_start:
    #    return _plugin.plugin_start(handle)
    #else:
    #    return None
    return None


def plugin_send(handle, readings):
    _LOGGER.info("plugin_send")

    # Create loop object
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Just pass a fake id as thrird parameter
    coroObj = _plugin.plugin_send(handle, readings, "000001")

    # Set coroutine to wait for
    futures = [coroObj]
    done, result = loop.run_until_complete(asyncio.wait(futures))

    numSent = 0
    for t in done:
        # Fetch done task result
        retCode, lastId, numSent = t.result()

    return numSent

def _revised_config_for_json_item(config):
    # North C server sends "config" argument as string in which all JSON type items' components,
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
