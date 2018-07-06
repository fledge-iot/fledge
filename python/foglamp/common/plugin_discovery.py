# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Plugin Discovery Class"""

import os
from foglamp.common import logger

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)

_FOGLAMP_DATA = os.getenv("FOGLAMP_DATA", default=None)
_FOGLAMP_ROOT = os.getenv("FOGLAMP_ROOT", default='/usr/local/foglamp')

class PluginDiscoveryInstalled(object):
    @classmethod
    def get_plugins(cls, plugin_type):
        directories = cls.get_plugin_folders(plugin_type)
        configs = []
        for d in directories:
            configs.append(cls.get_plugin_config(d, plugin_type))
        return configs

    @classmethod
    def get_plugin_folders(cls, plugin_type):
        directories = []
        try:
            directories = [d for d in os.listdir(_FOGLAMP_ROOT + "/python/foglamp/plugins/"+plugin_type)
                           if os.path.isdir(_FOGLAMP_ROOT + "/python/foglamp/plugins/" + plugin_type + "/" + d) and
                           not d.startswith("__") and d != "empty" and d != "common"]
        except FileNotFoundError:
            pass
        return directories

    @classmethod
    def get_plugin_config(cls, plugin_name, plugin_type):
        plugin_module_path = "foglamp.plugins.south" if plugin_type == 'south' else "foglamp.plugins.north"

        # Now load the plugin to fetch its configuration
        try:
            # "plugin_module_path" is fixed by design. It is MANDATORY to keep the plugin in the exactly similar named
            # folder, within the plugin_module_path.
            import_file_name = "{path}.{dir}.{file}".format(path=plugin_module_path, dir=plugin_name, file=plugin_name)
            _plugin = __import__(import_file_name, fromlist=[''])

            # Fetch configuration from the configuration defined in the plugin
            plugin_info = _plugin.plugin_info()
            plugin_config =  {
                'name': plugin_info['name'],
                'type': plugin_info['type'],
                'description': plugin_info['config']['plugin']['description'],
                'version': plugin_info['version']
            }
        except ImportError as ex:
            plugin_config = {
                'name': plugin_name,
                'description': 'Plugin "{}" import problem from path "{}". {}'.format(plugin_name, plugin_module_path, str(ex))
            }
        except Exception as ex:
            plugin_config = {
                'name': plugin_name,
                'description': 'Plugin "{}" raised exception "{}" while fetching config'.format(plugin_name, str(ex))
            }

        return plugin_config
