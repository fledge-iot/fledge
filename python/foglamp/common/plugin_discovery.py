# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Plugin Discovery Class"""

import os
from foglamp.common import logger
from foglamp.services.core.api import utils
from foglamp.services.core.api.plugins import common
from foglamp.plugins.common import utils as api_utils


__author__ = "Amarendra K Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)


class PluginDiscovery(object):
    def __init__(self):
        pass

    @classmethod
    def get_plugins_installed(cls, plugin_type=None, is_config=False):
        if plugin_type is None:
            plugins_list = []
            plugins_list_north = cls.fetch_plugins_installed("north", is_config)
            plugins_list_south = cls.fetch_plugins_installed("south", is_config)
            plugins_list_c_north = cls.fetch_c_plugins_installed("north", is_config)
            plugins_list_c_south = cls.fetch_c_plugins_installed("south", is_config)
            plugins_list_c_filter = cls.fetch_c_plugins_installed("filter", is_config)
            plugins_list_c_notify = cls.fetch_c_plugins_installed("notificationDelivery", is_config)
            plugins_list_c_rule = cls.fetch_c_plugins_installed("notificationRule", is_config)
            plugins_list.extend(plugins_list_north)
            plugins_list.extend(plugins_list_c_north)
            plugins_list.extend(plugins_list_south)
            plugins_list.extend(plugins_list_c_south)
            plugins_list.extend(plugins_list_c_filter)
            plugins_list.extend(plugins_list_c_notify)
            plugins_list.extend(plugins_list_c_rule)
        elif plugin_type in ['filter', 'notificationDelivery', 'notificationRule']:
            plugins_list = cls.fetch_c_plugins_installed(plugin_type, is_config)
        else:
            plugins_list = cls.fetch_plugins_installed(plugin_type, is_config)
            plugins_list.extend(cls.fetch_c_plugins_installed(plugin_type, is_config))
        return plugins_list

    @classmethod
    def fetch_plugins_installed(cls, plugin_type, is_config):
        directories = cls.get_plugin_folders(plugin_type)
        configs = []
        for d in directories:
            plugin_config = cls.get_plugin_config(d, plugin_type, is_config)
            if plugin_config is not None:
                configs.append(plugin_config)
        return configs

    @classmethod
    def get_plugin_folders(cls, plugin_type):
        directories = []
        dir_name = utils._FOGLAMP_ROOT + "/python/foglamp/plugins/" + plugin_type
        dir_path = []
        l1 = [plugin_type]
        if utils._FOGLAMP_PLUGIN_PATH:
            my_list = utils._FOGLAMP_PLUGIN_PATH.split(";")
            for l in my_list:
                dir_found = os.path.isdir(l)
                if dir_found:
                    subdirs = [dirs for x, dirs, files in os.walk(l)]
                    if subdirs[0]:
                        result = any(elem in l1 for elem in subdirs[0])
                        if result:
                            dir_path.append(l)
                    else:
                        _logger.warning("{} subdir type not found".format(l))
                else:
                    _logger.warning("{} dir path not found".format(l))
        try:
            directories = [dir_name + '/' + d for d in os.listdir(dir_name) if os.path.isdir(dir_name + "/" + d) and
                           not d.startswith("__") and d != "empty" and d != "common"]
            if dir_path:
                temp_list = []
                for fp in dir_path:
                    for root, dirs, files in os.walk(fp + "/" + plugin_type):
                        for name in dirs:
                            if not name.startswith("__"):
                                # temp_list.append(name)
                                p = os.path.join(root, name)
                                temp_list.append(p)
                directories = directories + temp_list
        except FileNotFoundError:
            pass
        else:
            return directories

    @classmethod
    def fetch_c_plugins_installed(cls, plugin_type, is_config):
        libs = utils.find_c_plugin_libs(plugin_type)
        configs = []
        for name, _type in libs:
            try:
                if _type == 'binary':
                    jdoc = utils.get_plugin_info(name, dir=plugin_type)
                    if jdoc:
                        if 'flag' in jdoc:
                            if api_utils.bit_at_given_position_set_or_unset(jdoc['flag'], api_utils.DEPRECATED_BIT_POSITION):
                                raise DeprecationWarning
                        plugin_config = {'name': name,
                                         'type': plugin_type,
                                         'description': jdoc['config']['plugin']['description'],
                                         'version': jdoc['version']
                                         }
                        if is_config:
                            plugin_config.update({'config': jdoc['config']})
                        configs.append(plugin_config)
                else:
                    # for c-hybrid plugin
                    hybrid_plugin_config = common.load_and_fetch_c_hybrid_plugin_info(name, is_config)
                    if hybrid_plugin_config:
                        configs.append(hybrid_plugin_config)
            except DeprecationWarning:
                _logger.warning('"{}" plugin is deprecated'.format(name))
            except Exception as ex:
                _logger.exception(ex)

        return configs

    @classmethod
    def get_plugin_config(cls, plugin_dir, plugin_type, is_config):
        plugin_module_path = plugin_dir
        plugin_config = None

        # Now load the plugin to fetch its configuration
        try:
            plugin_info = common.load_and_fetch_python_plugin_info(plugin_module_path,  plugin_module_path.split('/')[-1], plugin_type)
            # Fetch configuration from the configuration defined in the plugin
            if plugin_info['type'] == plugin_type:
                if 'flag' in plugin_info:
                    if api_utils.bit_at_given_position_set_or_unset(plugin_info['flag'], api_utils.DEPRECATED_BIT_POSITION):
                        raise DeprecationWarning
                plugin_config = {
                    'name': plugin_info['config']['plugin']['default'],
                    'type': plugin_info['type'],
                    'description': plugin_info['config']['plugin']['description'],
                    'version': plugin_info['version']
                }
            else:
                _logger.warning("Plugin {} is discarded due to invalid type".format(plugin_dir))

            if is_config:
                plugin_config.update({'config': plugin_info['config']})
        except DeprecationWarning:
            _logger.warning('"{}" plugin is deprecated'.format(plugin_dir.split('/')[-1]))
        except FileNotFoundError as ex:
            _logger.error('Plugin "{}" import problem from path "{}". {}'.format(plugin_dir, plugin_module_path, str(ex)))
        except Exception as ex:
            _logger.exception('Plugin "{}" raised exception "{}" while fetching config'.format(plugin_dir, str(ex)))

        return plugin_config

