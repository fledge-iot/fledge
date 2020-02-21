# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

import platform
import os
import logging
from aiohttp import web
from fledge.common import logger
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.services.core.api.plugins import common
from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.common import _FLEDGE_ROOT
from fledge.common.audit_logger import AuditLogger

__author__ = "Rajesh Kumar"
__copyright__ = "Copyright (c) 2020, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__, level=logging.INFO)

valid_plugin = ['north', 'south', 'filter', 'notificationDelivery', 'notificationRule']
PYTHON_PLUGIN_PATH = _FLEDGE_ROOT+'/python/fledge/plugins/'
C_PLUGINS_PATH = _FLEDGE_ROOT+'/plugins/'


async def plugin_remove(request):
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
            raise ValueError("Invalid plugin type. Please provide valid type: {}".format(valid_plugin))
        installed_plugin = PluginDiscovery.get_plugins_installed(plugin_type, False)
        if name not in [plugin['name'] for plugin in installed_plugin]:
            raise KeyError("Invalid {} plugin name or plugin is not installed".format(name))
        if plugin_type in ['notificationDelivery', 'notificationRule']:
            plugin_type = 'notify' if plugin_type == 'notificationDelivery' else 'rule'
        get_tracked_plugins = await check_plugin_usage(plugin_type, name)
        if get_tracked_plugins:
            e = "{} cannot be removed. This is being used by {} instances".format(name, get_tracked_plugins[0]['service_list'])
            _logger.error(e)
            raise RuntimeError(e)
        else:
            _logger.info("No entry found for {name} plugin in asset tracker; or "
                         "{name} plugin may have been added in disabled state & never used".format(name=name))
        res, log_path = purge_plugin(plugin_type, name)
        if res != 0:
            _logger.error("Something went wrong. Please check log {}".format(log_path))
            raise RuntimeError("Something went wrong. Please check log {}".format(log_path))
        else:
            storage_client = connect.get_storage_async()
            audit_log = AuditLogger(storage_client)
            audit_detail = {'package_name': "fledge-{}-{}".format(plugin_type, name)}
            await audit_log.information('PKGRM', audit_detail)
    except ValueError as ex:
        return web.json_response({'error': '{}'.format(ex)}, status=400)
    except KeyError as ex:
        return web.json_response({'error': '{}'.format(ex)}, status=404)
    except RuntimeError as ex:
        return web.json_response({'error': '{}'.format(ex)}, status=400)
    return web.json_response({'message': '{} plugin removed successfully'.format(name)}, status=200)


async def check_plugin_usage(plugin_type: str, plugin_name: str):
    """ Check usage of plugin and return a list of services / tasks or other instances with reference
    """
    plugin_users = []
    filter_used = []
    service_list = []
    storage_client = connect.get_storage_async()
    # TODO: add check for notification plugins
    if plugin_type == 'south':
        event = 'Ingest'
    elif plugin_type == 'filter':
        event = 'Filter'
    else:
        event = 'Egress'
    payload_data = PayloadBuilder().SELECT('plugin', 'service').WHERE(['event', '=', event]).payload()
    list_of_tracked_plugin = await storage_client.query_tbl_with_payload('asset_tracker', payload_data)

    if plugin_type == 'filter':
        filter_payload = PayloadBuilder().SELECT('name').WHERE(['plugin', '=', plugin_name]).payload()
        filter_res = await storage_client.query_tbl_with_payload("filters", filter_payload)
        filter_used = [f['name'] for f in filter_res['rows']]
        for r in range(0, len(list_of_tracked_plugin['rows'])):
            for p in filter_used:
                if p in list_of_tracked_plugin['rows'][r]['plugin']:
                    service_list.append(list_of_tracked_plugin['rows'][r]['service'])
                    break
    if list_of_tracked_plugin['rows']:
        for e in list_of_tracked_plugin['rows']:
            if (plugin_name == e['plugin'] and plugin_type != 'filter') or (e['plugin'] in filter_used and
                                                                            plugin_type == 'filter'):
                if plugin_name in [x['plugin'] for x in list_of_tracked_plugin['rows']] or e['plugin'] in filter_used:
                    if service_list:
                        plugin_users.append({'e': e, 'service_list': service_list})
                    else:
                        service_list.append(e['service'])
                        plugin_users.append({'e': e, 'service_list': service_list})
    return plugin_users


# TODO: Check notification instance state using the given rule or delivery plugin?
async def check_plugin_usage_in_notification_instances(plugin_type: str, plugin_name: str):
    pass


def purge_plugin(plugin_type: str, name: str):
    """
        Remove plugin based on platform
    """
    _logger.info("Plugin removal started...")
    org_name = name
    name = name.replace('_', '-').lower()
    plugin_name = 'fledge-{}-{}'.format(plugin_type, name)
    stdout_file_path = common.create_log_file(action='remove', plugin_name=plugin_name)
    get_platform = platform.platform()
    try:
        package_manager = 'yum' if 'centos' in get_platform or 'redhat' in get_platform else 'apt'
        if package_manager == 'yum':
            cmd = "sudo {} -y remove {} > {} 2>&1".format(package_manager, plugin_name, stdout_file_path)
        else:
            cmd = "sudo {} -y purge {} > {} 2>&1".format(package_manager, plugin_name, stdout_file_path)
        code = os.system(cmd)
        installed_plugin = PluginDiscovery.get_plugins_installed(plugin_type, False)
        if org_name or name in [plugin['name'] for plugin in installed_plugin]:
            raise KeyError("Plugin is not installed by package manager.".format(org_name))
    except KeyError:
        try:
            path = PYTHON_PLUGIN_PATH+'{}/{}'.format(plugin_type, org_name)
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
                path = C_PLUGINS_PATH + '{}/{}'.format(plugin_type, org_name)
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
