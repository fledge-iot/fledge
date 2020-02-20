# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

import platform
import os
from aiohttp import web
import logging
from fledge.common import logger
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.services.core.api.plugins import common
from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.common import _FLEDGE_PLUGIN_PATH, _FLEDGE_ROOT

__author__ = "Rajesh Kumar"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__, level=logging.INFO)

valid_plugin = ['north', 'south', 'filter', 'notificationDelivery', 'notificationRule']
PYTHON_PLUGIN_PATH = _FLEDGE_ROOT+'/python/fledge/plugins/'
C_PLUGINS_PATH = _FLEDGE_ROOT+'/plugins/'

async def plugin_delete(request):
    """
    Remove plugin from fledge

    '''
    EndPoint: curl -X DELETE http://host-ip:port/fledge/plugins/{type}/{name}
    '''
    Example:
        curl -X DELETE http://host-ip:port/fledge/plugins/south/sinusoid
        curl -X DELETE http://host-ip:port/fledge/plugins/north/http_north
        curl -X DELETE http://host-ip:port/fledge/plugins/filter/expression
        curl -X DELETE http://host-ip:port/fledge/plugins/notificationDelivery/alexa
        curl -X DELETE http://host-ip:port/fledge/plugins/notificationRule/Average
    """
    plugin_type = request.match_info.get('type', None)
    name = request.match_info.get('name', None)
    try:
        plugin_type = str(plugin_type).lower() if not str(plugin_type).startswith('notification') else plugin_type
        if plugin_type not in valid_plugin:
            raise ValueError("Invalid plugin type.Please provide valid type:{}".format(valid_plugin))
        installed_plugin = PluginDiscovery.get_plugins_installed(plugin_type, False)
        _logger.info(f"installed plugin:{installed_plugin}")
        if name not in [plugin['name'] for plugin in installed_plugin]:
            raise KeyError("Invalid {} plugin name or plugin is not installed.".format(name))
        if plugin_type in ['notificationDelivery', 'notificationRule']:
            plugin_type = 'notify' if plugin_type == 'notificationDelivery' else 'rule'
        get_tracked_plugins = await check_service_is_enabled_or_disabled(plugin_type, name)
        _logger.info(get_tracked_plugins)
        if get_tracked_plugins:
            _logger.error("{} is being used.Purge is not possible in plugin enable state.".format(name))
            raise RuntimeError("{} is being used.Purge is not possible in plugin enable state.".format(name))
        res, log_path = purge_plugin(plugin_type, name)
        if res != 0:
            _logger.error("Something went wrong.Please check log:-{}".format(log_path))
            raise RuntimeError("Something went wrong.Please check log:-{}".format(log_path))
    except ValueError as ex:
        return web.json_response({'error': '{}'.format(ex)}, status=400)
    except KeyError as ex:
        return web.json_response({'error': '{}'.format(ex)}, status=400)
    except RuntimeError as ex:
        return web.json_response({'error': '{}'.format(ex)}, status=400)
    return web.json_response({'message': '{} plugin removed successfully'.format(name)}, status=200)


async def check_service_is_enabled_or_disabled(plugin_type: str, plugin_name: str):
    """
        list of plugin with enabled state
    """
    list_of_enabled_plugin = []
    filter_used = []
    storage_client = connect.get_storage_async()
    if plugin_type == 'south':
        event = 'Ingest'
    elif plugin_type == 'filter':
        event = 'Filter'
    else:
        event = 'Egress'
    payload_data = PayloadBuilder().SELECT('plugin', 'service').WHERE(['event', '=', event]).payload()
    enabled_asset_list = await storage_client.query_tbl_with_payload('asset_tracker', payload_data)
    _logger.info(enabled_asset_list['rows'])

    if plugin_type == 'filter':
        filter_payload = PayloadBuilder().SELECT('name').WHERE(['plugin', '=', plugin_name]).payload()
        filter_res = await storage_client.query_tbl_with_payload("filters", filter_payload)
        filter_used = [f['name'] for f in filter_res['rows']]
        _logger.info(f"filter:{filter_used}")
    for e in enabled_asset_list['rows']:
        if (plugin_name == e['plugin'] and plugin_type != 'filter') or (e['plugin'] in filter_used and
                                                                        plugin_type == 'filter'):
            get_enabled_plugin = await get_enabled_or_disabled_status(e['service'])
            _logger.info(get_enabled_plugin)
            if plugin_name in [x['plugin'] for x in enabled_asset_list['rows']] or e['plugin'] in filter_used:
                list_of_enabled_plugin.append(e)
        _logger.info(list_of_enabled_plugin)
    return list_of_enabled_plugin


async def get_enabled_or_disabled_status(service_name: str):
    """
        check plugin state(enabled or disabled)
    """
    storage_client = connect.get_storage_async()
    payload_data = PayloadBuilder().SELECT('id', 'enabled').WHERE(['schedule_name', '=', service_name]).payload()
    enabled_service_list = await storage_client.query_tbl_with_payload('schedules', payload_data)
    return enabled_service_list['rows']


# TODO: notification service state(enabled or disabled)
async def check_notification_service_state(plugin_type: str, plugin_name: str):
    pass


def purge_plugin(plugin_type: str, name: str):
    """
        Remove plugin based on platform
    """
    _logger.info("Plugin removal started...")
    name = name.replace('_', '-').lower()
    plugin_name = 'fledge-{}-{}'.format(plugin_type, name)
    stdout_file_path = common.create_log_file(action='delete', plugin_name=plugin_name)
    get_platform = platform.platform()
    try:
        package_manager = 'yum' if 'centos' in get_platform or 'redhat' in get_platform else 'apt'
        if package_manager == 'yum':
            cmd = "sudo {} -y remove {} > {} 2>&1".format(package_manager, plugin_name, stdout_file_path)
        else:
            cmd = "sudo {} -y purge {} > {} 2>&1".format(package_manager, plugin_name, stdout_file_path)
        code = os.system(cmd)
        installed_plugin = PluginDiscovery.get_plugins_installed(plugin_type, False)
        if name in [plugin['name'] for plugin in installed_plugin] or code != 0:
            raise KeyError("Plugin is not installed by package manager.".format(name))
    except KeyError as ex:
        try:
            _logger.info(_FLEDGE_ROOT)
            path = PYTHON_PLUGIN_PATH+'{}/{}'.format(plugin_type, name)
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    if '__pycache__' in dirs:
                        os.system('rm -rf {}'.format(os.path.join(root, '__pycache__')))
                    else:
                        for file in files:
                            os.remove(os.path.join(root, file))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                code = os.system('rm -rf {}'.format(path))
            else:
                path = C_PLUGINS_PATH + '{}/{}'.format(plugin_type, name)
                for root, dirs, files in os.walk(path):
                    for file in files:
                        os.remove(os.path.join(root, file))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                code = os.system('rm -rf {}'.format(path))
        except (OSError, Exception) as ex:
            _logger.error("Error in removing plugin:{}".format(str(ex)))
            code = 1
    return code, stdout_file_path
