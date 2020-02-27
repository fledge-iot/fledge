# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

import platform
import os
import logging
import json

from aiohttp import web
from fledge.common import logger
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.services.core.api.plugins import common
from fledge.services.core.api.plugins.exceptions import *
from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.configuration_manager import ConfigurationManager
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


async def remove_plugin(request):
    """
    Remove plugin from fledge
    name: installed_directory name

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
            notification_instances_plugin_used_in = await check_plugin_usage_in_notification_instances(name)
            if notification_instances_plugin_used_in:
                raise RuntimeError("{} cannot be removed. This is being used by {} instances".
                                   format(name, notification_instances_plugin_used_in))
            plugin_type = 'notify' if plugin_type == 'notificationDelivery' else 'rule'
        else:
            get_tracked_plugins = await check_plugin_usage(plugin_type, name)
            if get_tracked_plugins:
                e = "{} cannot be removed. This is being used by {} instances".\
                    format(name, get_tracked_plugins[0]['service_list'])
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
    except (ValueError, RuntimeError) as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except KeyError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except PackageError as e:
        msg = "Plugin removal request failed"
        raise web.HTTPBadRequest(body=json.dumps({"message": msg, "link": str(e)}), reason=msg)
    _logger.info('{} plugin removed successfully'.format(name))
    return web.json_response({'message': '{} plugin removed successfully'.format(name)}, status=200)


async def check_plugin_usage(plugin_type: str, plugin_name: str):
    """ Check usage of plugin and return a list of services / tasks or other instances with reference
    """
    plugin_users = []
    filter_used = []
    service_list = []
    storage_client = connect.get_storage_async()
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
            service_in_schedules_list = await check_service_in_schedules(list_of_tracked_plugin['rows'][r]['service'])
            for p in filter_used:
                if p in list_of_tracked_plugin['rows'][r]['plugin'] and service_in_schedules_list:
                    service_list.append(list_of_tracked_plugin['rows'][r]['service'])
                    break
    if list_of_tracked_plugin['rows']:
        for e in list_of_tracked_plugin['rows']:
            if (plugin_name == e['plugin'] and plugin_type != 'filter') or (e['plugin'] in filter_used and
                                                                            plugin_type == 'filter'):
                service_in_list = await check_service_in_schedules(e['service'])
                if (plugin_name in [x['plugin'] for x in list_of_tracked_plugin['rows']] and service_in_list) \
                        or (e['plugin'] in filter_used and service_in_list):
                    if service_list:
                        plugin_users.append({'e': e, 'service_list': service_list})
                    else:
                        service_list.append(e['service'])
                        plugin_users.append({'e': e, 'service_list': service_list})
    return plugin_users


async def check_service_in_schedules(service_name: str):
    storage_client = connect.get_storage_async()
    payload_data = PayloadBuilder().SELECT('id', 'enabled').WHERE(['schedule_name', '=', service_name]).payload()
    enabled_service_list = await storage_client.query_tbl_with_payload('schedules', payload_data)
    is_service_list = True if enabled_service_list['rows'] else False
    return is_service_list


async def check_plugin_usage_in_notification_instances(plugin_name: str):
    """
    Check notification instance state using the given rule or delivery plugin
    """
    notification_instances = []
    storage_client = connect.get_storage_async()
    configuration_mgr = ConfigurationManager(storage_client)
    notifications = await configuration_mgr.get_category_child("Notifications")
    if notifications:
        for notification in notifications:
            notification_config = await configuration_mgr._read_category_val(notification['key'])
            name = notification_config['name']['value']
            channel = notification_config['channel']['value']
            rule = notification_config['rule']['value']
            enabled = True if notification_config['enable']['value'] == 'true' else False
            if (channel == plugin_name and enabled) or (rule == plugin_name and enabled):
                notification_instances.append(name)
    return notification_instances


def purge_plugin(plugin_type: str, name: str) -> tuple:
    _logger.info("{} plugin removal started...".format(name))
    original_name = name
    # Special case handling - installed directory name Vs package name
    # For example: Plugins like http_south Vs http-south
    name = name.replace('_', '-').lower()
    plugin_name = 'fledge-{}-{}'.format(plugin_type, name)
    stdout_file_path = common.create_log_file(action='remove', plugin_name=plugin_name)
    link = "log/" + stdout_file_path.split("/")[-1]
    get_platform = platform.platform()
    try:
        if 'centos' in get_platform or 'redhat' in get_platform:
            cmd = "sudo yum -y remove {} > {} 2>&1".format(plugin_name, stdout_file_path)
        else:
            cmd = "sudo apt -y purge {} > {} 2>&1".format(plugin_name, stdout_file_path)
        code = os.system(cmd)
        if code != 0:
            # TODO: If package repo is NOT configured but we have installation of plugin with make or make install
            raise PackageError(link)

        if plugin_type in ['notify', 'rule']:
            plugin_type = 'notificationDelivery' if plugin_type == 'notify' else 'notificationRule'
        else:
            plugin_type = plugin_type
        installed_plugin = PluginDiscovery.get_plugins_installed(plugin_type, False)
        if [plugin['name'] for plugin in installed_plugin if plugin['name'] in [original_name, name]]:
            raise KeyError("Requested plugin is not installed: {}".format(original_name))
    except KeyError:
        # This case is for non-package installation - python plugin path will be tried first and then C
        try:
            path = PYTHON_PLUGIN_PATH+'{}/{}'.format(plugin_type, original_name)
            if os.path.isdir(path):
                code = os.system('rm -rv {}'.format(path))
            else:
                path = C_PLUGINS_PATH + '{}/{}'.format(plugin_type, original_name)
                code = os.system('rm -rv {}'.format(path))
            if code != 0:
                raise OSError("While deleting, invalid plugin path found for {}".format(original_name))
        except Exception as ex:
            code = 1
            _logger.error("Error in removing plugin: {}".format(str(ex)))
    except Exception as e:
        code = 1
        _logger.error("Error in removing plugin: {}".format(str(e)))
    return code, stdout_file_path
