# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""shim layer between Python and C++"""

import sys
import json

from foglamp.common import logger

_LOGGER = logger.setup(__name__, level=20)
_LOGGER.info("Loading shim layer for python plugin '{}' ".format(sys.argv[1]))

_plugin = None

def _plugin_obj():
    plugin = sys.argv[1]  #'sinusoid' #sys.argv[1]
    service_type = 'south'
    try:
        plugin_module_path = "foglamp.plugins.south" if service_type == 'south' else "foglamp.plugins.north"
        import_file_name = "{path}.{dir}.{file}".format(path=plugin_module_path, dir=plugin, file=plugin)
        _plugin = __import__(import_file_name, fromlist=[''])
        #_LOGGER.info("import succeeded")
    except ImportError as ex:
        _LOGGER.info("exception 1")
    except Exception as ex:
        _LOGGER.info("exception 2")
    return _plugin

_plugin = _plugin_obj()

def plugin_info():
    #return json.dumps({"plugin":"test"})
    #_plugin = _plugin_obj()
    #_LOGGER.info("plugin_info called")
    handle = _plugin.plugin_info()
    handle['config'] = json.dumps(handle['config'])
    #_LOGGER.info("info dict = {}".format(json.dumps(handle)))
    return handle

def plugin_init(config):
    #_plugin = _plugin_obj()
    #_LOGGER.info("plugin_init called")
    return json.dumps(_plugin.plugin_init(json.loads(config)))

def plugin_poll(handle):
    #_plugin = _plugin_obj()
    #_LOGGER.info("plugin_poll called")
    _read = _plugin.plugin_poll(json.loads(handle))
    reading = {
            'asset_code': _read['asset'],
            'user_ts': _read['timestamp'],
            'read_key': _read['key'],
            'reading': _read['readings']
        }
    #_LOGGER.info("Reading = {}".format(json.dumps(reading)))
    return reading

def plugin_reconfigure(handle, new_config):
    #_plugin = _plugin_obj()
    #_LOGGER.info("plugin_reconfigure called")
    new_handle = _plugin.plugin_reconfigure(json.loads(handle),json.loads(new_config))
    return json.dumps(new_handle)

def plugin_shutdown(handle):
    #_plugin = _plugin_obj()
    #_LOGGER.info("plugin_shutdown called")
    return json.dumps(_plugin.plugin_shutdown(json.loads(handle)))

if __name__ == '__main__':
    print("Main called")
    _LOGGER.info("main called")
    _plugin = _plugin_obj()
    print(_plugin.plugin_info())
