# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

import asyncio
import os
import logging
import uuid
import platform

from aiohttp import web
from fledge.common import logger
from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import server
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.services.core.api.plugins import common
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.audit_logger import AuditLogger


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | PUT             | /fledge/plugin/{type}/{name}/update                      |
    -------------------------------------------------------------------------------
"""
_logger = logger.setup(__name__, level=logging.INFO)


async def update_plugin(request: web.Request) -> web.Response:
    """ update plugin

    :Example:
        curl -sX PUT http://localhost:8081/fledge/plugins/south/sinusoid/update
        curl -sX PUT http://localhost:8081/fledge/plugins/north/http_north/update
        curl -sX PUT http://localhost:8081/fledge/plugins/filter/metadata/update
        curl -sX PUT http://localhost:8081/fledge/plugins/notify/asset/update
        curl -sX PUT http://localhost:8081/fledge/plugins/rule/OutOfBound/update
    """
    _type = request.match_info.get('type', None)
    name = request.match_info.get('name', None)
    try:
        _type = _type.lower()
        if _type not in ['north', 'south', 'filter', 'notify', 'rule']:
            raise ValueError("Invalid plugin type. Must be 'north' or 'south' or 'filter' or 'notify' or 'rule'")
        if _type == 'notify':
            installed_dir_name = 'notificationDelivery'
        elif _type == 'rule':
            installed_dir_name = 'notificationRule'
        else:
            installed_dir_name = _type

        # Check requested plugin name is installed or not
        installed_plugins = PluginDiscovery.get_plugins_installed(installed_dir_name, False)
        installed_plugin_name = [p_name["name"] for p_name in installed_plugins]
        if name not in installed_plugin_name:
            raise KeyError("{} plugin is not yet installed. So update is not possible.".format(name))

        sch_list = []
        notification_list = []
        if _type in ['notify', 'rule']:
            # Check Notification service is enabled or not
            payload = PayloadBuilder().SELECT("id", "enabled", "schedule_name").WHERE(['process_name', '=',
                                                                                       'notification_c']).payload()
            storage_client = connect.get_storage_async()
            result = await storage_client.query_tbl_with_payload('schedules', payload)
            sch_info = result['rows']
            if sch_info and sch_info[0]['enabled'] == 't':
                # Find notification instances which are used by requested plugin name
                # If its config item 'enable' is true then update to false
                config_mgr = ConfigurationManager(storage_client)
                all_notifications = await config_mgr._read_all_child_category_names("Notifications")
                for notification in all_notifications:
                    notification_config = await config_mgr._read_category_val(notification['child'])
                    notification_name = notification_config['name']['value']
                    channel = notification_config['channel']['value']
                    rule = notification_config['rule']['value']
                    is_enabled = True if notification_config['enable']['value'] == 'true' else False
                    if (channel == name and is_enabled) or (rule == name and is_enabled):
                        _logger.warning("Disabling {} notification instance, as {} {} plugin is updating...".format(
                            notification_name, name, _type))
                        await config_mgr.set_category_item_value_entry(notification_name, "enable", "false")
                        notification_list.append(notification_name)
        else:
            # Tracked plugins from asset tracker
            tracked_plugins = await _get_plugin_and_sch_name_from_asset_tracker(_type)
            filters_used_by = []
            if _type == 'filter':
                # In case of filter, for asset_tracker table we are inserting filter category_name in plugin column
                # instead of filter plugin name by Design
                # Hence below query is required to get actual plugin name from filters table
                storage_client = connect.get_storage_async()
                payload = PayloadBuilder().SELECT("name").WHERE(['plugin', '=', name]).payload()
                result = await storage_client.query_tbl_with_payload('filters', payload)
                filters_used_by = [r['name'] for r in result['rows']]
            for p in tracked_plugins:
                if (name == p['plugin'] and not _type == 'filter') or (p['plugin'] in filters_used_by and _type == 'filter'):
                    sch_info = await _get_sch_id_and_enabled_by_name(p['service'])
                    if sch_info[0]['enabled'] == 't':
                        status, reason = await server.Server.scheduler.disable_schedule(uuid.UUID(sch_info[0]['id']))
                        if status:
                            _logger.warning("Disabling {} {} instance, as {} plugin is updating...".format(
                                p['service'], _type, name))
                            sch_list.append(sch_info[0]['id'])

        # Plugin update is running as a background task
        loop = request.loop
        request._type = _type
        request._name = name
        request._sch_list = sch_list
        request._notification_list = notification_list
        loop.call_later(1, do_update, request)
    except KeyError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))

    return web.json_response({"message": "{} plugin update in process. Wait for few minutes to complete.".format(name)})


async def _get_plugin_and_sch_name_from_asset_tracker(_type: str) -> list:
    if _type == "south":
        event_name = "Ingest"
    elif _type == 'filter':
        event_name = "Filter"
    else:
        event_name = "Egress"
    storage_client = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("plugin", "service").WHERE(['event', '=', event_name]).payload()
    result = await storage_client.query_tbl_with_payload('asset_tracker', payload)
    return result['rows']


async def _get_sch_id_and_enabled_by_name(name) -> list:
    storage_client = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("id", "enabled").WHERE(['schedule_name', '=', name]).payload()
    result = await storage_client.query_tbl_with_payload('schedules', payload)
    return result['rows']


def update_repo_sources_and_plugin(_type: str, name: str) -> tuple:
    # Below check is needed for python plugins
    # For Example: installed_plugin_dir=wind_turbine; package_name=wind-turbine
    name = name.replace("_", "-")

    # For endpoint curl -X GET http://localhost:8081/fledge/plugins/available we used
    # sudo apt list command internal so package name always returns in lowercase,
    # irrespective of package name defined in the configured repo.
    name = "fledge-{}-{}".format(_type, name.lower())
    _platform = platform.platform()
    stdout_file_path = common.create_log_file(action="update", plugin_name=name)
    pkg_mgt = 'apt'
    cmd = "sudo {} -y update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    if 'centos' in _platform or 'redhat' in _platform:
        pkg_mgt = 'yum'
        cmd = "sudo {} check-update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    ret_code = os.system(cmd)
    # sudo apt/yum -y install only happens when update is without any error
    if ret_code == 0:
        cmd = "sudo {} -y install {} >> {} 2>&1".format(pkg_mgt, name, stdout_file_path)
        ret_code = os.system(cmd)

    # relative log file link
    link = "log/" + stdout_file_path.split("/")[-1]
    return ret_code, link


def do_update(request):
    _logger.info("{} plugin update started...".format(request._name))
    code, link = update_repo_sources_and_plugin(request._type, request._name)
    if code != 0:
        _logger.error("{} plugin update failed. Logs available at {}".format(request._name, link))
    else:
        _logger.info("{} plugin update completed. Logs available at {}".format(request._name, link))
        # PKGUP audit log entry
        storage_client = connect.get_storage_async()
        audit = AuditLogger(storage_client)
        audit_detail = {'packageName': "fledge-{}-{}".format(request._type, request._name.replace("_", "-"))}
        asyncio.ensure_future(audit.information('PKGUP', audit_detail))

    # Restart the services which were disabled before plugin update
    for s in request._sch_list:
        asyncio.ensure_future(server.Server.scheduler.enable_schedule(uuid.UUID(s)))

    # Below case is applicable for the notification plugins ONLY
    # Enabled back configuration categories which were disabled during update process
    if request._type in ['notify', 'rule']:
        storage_client = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage_client)
        for n in request._notification_list:
            asyncio.ensure_future(config_mgr.set_category_item_value_entry(n, "enable", "true"))
