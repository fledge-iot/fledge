# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Plugin Discovery Class"""

import os
from foglamp.common import logger
from foglamp.services.core.api import utils

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)


class PluginDiscovery(object):
    def __init__(self):
        pass

    @classmethod
    def get_plugins_installed(cls, plugin_type=None):
        if plugin_type is None:
            plugins_list = []
            plugins_list_north = cls.fetch_plugins_installed("north")
            plugins_list_south = cls.fetch_plugins_installed("south")
            plugins_list_c_north = cls.fetch_c_plugins_installed("north")
            plugins_list_c_south = cls.fetch_c_plugins_installed("south")
            plugins_list.extend(plugins_list_north)
            plugins_list.extend(plugins_list_c_north)
            plugins_list.extend(plugins_list_south)
            plugins_list.extend(plugins_list_c_south)
        else:
            plugins_list = cls.fetch_plugins_installed(plugin_type)
            plugins_list.extend(cls.fetch_c_plugins_installed(plugin_type))
        return plugins_list

    @classmethod
    def fetch_plugins_installed(cls, plugin_type):
        directories = cls.get_plugin_folders(plugin_type)
        configs = []
        for d in directories:
            plugin_config = cls.get_plugin_config(d, plugin_type)
            if plugin_config is not None:
                configs.append(plugin_config)
        return configs

    @classmethod
    def get_plugin_folders(cls, plugin_type):
        directories = []
        dir_name = utils._FOGLAMP_ROOT + "/python/foglamp/plugins/" + plugin_type
        try:
            directories = [d for d in os.listdir(dir_name) if os.path.isdir(dir_name + "/" + d) and
                           not d.startswith("__") and d != "empty" and d != "common"]
        except FileNotFoundError:
            pass
        else:
            return directories

    @classmethod
    def fetch_c_plugins_installed(cls, plugin_type):
        libs = utils.find_c_plugin_libs(plugin_type)
        configs = []
        for l in libs:
            jdoc = utils.get_plugin_info(l)
            if jdoc is not None:
                plugin_config = {'name': l,
                                 'type': plugin_type,
                                 'description': jdoc['config']['plugin']['description'],
                                 'version': jdoc['version']
                                 }
                configs.append(plugin_config)
        return configs

    @classmethod
    def get_plugin_config(cls, plugin_dir, plugin_type):
        plugin_module_path = "foglamp.plugins.south" if plugin_type == 'south' else "foglamp.plugins.north"
        plugin_config = None

        # Now load the plugin to fetch its configuration
        try:
            plugin_module_name = plugin_dir
            import_file_name = "{path}.{dir}.{file}".format(path=plugin_module_path, dir=plugin_dir, file=plugin_module_name)
            _plugin = __import__(import_file_name, fromlist=[''])

            # Fetch configuration from the configuration defined in the plugin
            plugin_info = _plugin.plugin_info()
            plugin_config = {
                'name': plugin_info['config']['plugin']['default'],
                'type': plugin_info['type'],
                'description': plugin_info['config']['plugin']['description'],
                'version': plugin_info['version']
            }
        except ImportError as ex:
            _logger.error('Plugin "{}" import problem from path "{}". {}'.format(plugin_dir, plugin_module_path, str(ex)))
        except Exception as ex:
            _logger.exception('Plugin "{}" raised exception "{}" while fetching config'.format(plugin_dir, str(ex)))

        return plugin_config
