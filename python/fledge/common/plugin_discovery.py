# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Common Plugin Discovery Class"""

import os
from fledge.common import logger
from fledge.services.core.api import utils
from fledge.services.core.api.plugins import common
from fledge.plugins.common import utils as common_utils


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
            plugins_list_north = cls.fetch_plugins_installed(plugin_type="north", installed_dir_name="north",
                                                             is_config=is_config)
            plugins_list_south = cls.fetch_plugins_installed(plugin_type="south", installed_dir_name="south",
                                                             is_config=is_config)
            plugins_list_filter = cls.fetch_plugins_installed(plugin_type="filter", installed_dir_name="filter",
                                                              is_config=is_config)
            plugins_list_notify = cls.fetch_plugins_installed(
                plugin_type="notify", installed_dir_name="notificationDelivery", is_config=is_config)
            plugins_list_rule = cls.fetch_plugins_installed(
                plugin_type="rule", installed_dir_name="notificationRule", is_config=is_config)
            plugins_list_c_north = cls.fetch_c_plugins_installed(plugin_type="north", is_config=is_config,
                                                                 installed_dir_name="north")
            plugins_list_c_south = cls.fetch_c_plugins_installed(plugin_type="south", is_config=is_config,
                                                                 installed_dir_name="south")
            plugins_list_c_filter = cls.fetch_c_plugins_installed(plugin_type="filter", is_config=is_config,
                                                                  installed_dir_name="filter")
            plugins_list_c_notify = cls.fetch_c_plugins_installed(plugin_type="notify", is_config=is_config,
                                                                  installed_dir_name="notificationDelivery")
            plugins_list_c_rule = cls.fetch_c_plugins_installed(plugin_type="rule", is_config=is_config,
                                                                installed_dir_name="notificationRule")
            plugins_list.extend(plugins_list_north)
            plugins_list.extend(plugins_list_c_north)
            plugins_list.extend(plugins_list_south)
            plugins_list.extend(plugins_list_c_south)
            plugins_list.extend(plugins_list_filter)
            plugins_list.extend(plugins_list_c_filter)
            plugins_list.extend(plugins_list_notify)
            plugins_list.extend(plugins_list_c_notify)
            plugins_list.extend(plugins_list_rule)
            plugins_list.extend(plugins_list_c_rule)
        else:
            if plugin_type == 'notify':
                installed_dir_name = 'notificationDelivery'
            elif plugin_type == 'rule':
                installed_dir_name = 'notificationRule'
            else:
                installed_dir_name = plugin_type
            plugins_list = cls.fetch_plugins_installed(plugin_type=plugin_type,
                                                       installed_dir_name=installed_dir_name, is_config=is_config)
            plugins_list.extend(cls.fetch_c_plugins_installed(plugin_type=plugin_type, is_config=is_config,
                                                              installed_dir_name=installed_dir_name))
        return plugins_list

    @classmethod
    def fetch_plugins_installed(cls, plugin_type, installed_dir_name, is_config):
        directories = cls.get_plugin_folders(installed_dir_name)
        # Check is required only for notificationDelivery & notificationRule python plugins as NS is an external service
        # Hence we are not creating empty directories, as we had for south & filters
        if directories is None:
            directories = []
        configs = []
        for d in directories:
            plugin_config = cls.get_plugin_config(d, plugin_type, installed_dir_name, is_config)
            if plugin_config is not None:
                configs.append(plugin_config)
        return configs

    @classmethod
    def get_plugin_folders(cls, plugin_type):
        directories = []
        dir_name = utils._FLEDGE_ROOT + "/python/fledge/plugins/" + plugin_type
        dir_path = []
        l1 = [plugin_type]
        if utils._FLEDGE_PLUGIN_PATH:
            my_list = utils._FLEDGE_PLUGIN_PATH.split(";")
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
    def fetch_c_plugins_installed(cls, plugin_type, is_config, installed_dir_name):
        libs = utils.find_c_plugin_libs(installed_dir_name)
        configs = []
        for name, _type in libs:
            try:
                if _type == 'binary':
                    jdoc = utils.get_plugin_info(name, dir=installed_dir_name)
                    if jdoc:
                        if 'flag' in jdoc:
                            if common_utils.bit_at_given_position_set_or_unset(jdoc['flag'],
                                                                               common_utils.DEPRECATED_BIT_POSITION):
                                raise DeprecationWarning
                        plugin_config = {'name': name,
                                         'type': plugin_type,
                                         'description': jdoc['config']['plugin']['description'],
                                         'version': jdoc['version'],
                                         'installedDirectory': '{}/{}'.format(installed_dir_name, name),
                                         'packageName': 'fledge-{}-{}'.format(plugin_type,
                                                                              name.lower().replace("_", "-"))
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
    def get_plugin_config(cls, plugin_dir, plugin_type, installed_dir_name, is_config):
        plugin_module_path = plugin_dir
        plugin_config = None
        # Now load the plugin to fetch its configuration
        try:
            plugin_info = common.load_and_fetch_python_plugin_info(
                plugin_module_path, plugin_module_path.split('/')[-1], installed_dir_name)
            # Fetch configuration from the configuration defined in the plugin
            if plugin_info['type'] == installed_dir_name:
                if 'flag' in plugin_info:
                    if common_utils.bit_at_given_position_set_or_unset(plugin_info['flag'],
                                                                       common_utils.DEPRECATED_BIT_POSITION):
                        raise DeprecationWarning
                plugin_config = {
                    'name': plugin_info['config']['plugin']['default'],
                    'type': plugin_type,
                    'description': plugin_info['config']['plugin']['description'],
                    'version': plugin_info['version'],
                    'installedDirectory': '{}/{}'.format(installed_dir_name,
                                                         plugin_info['config']['plugin']['default']),
                    'packageName': 'fledge-{}-{}'.format(
                        plugin_type, plugin_info['config']['plugin']['default'].lower().replace("_", "-"))
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

