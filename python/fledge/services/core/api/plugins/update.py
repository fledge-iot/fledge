# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import aiohttp
import asyncio
import os
import uuid
import multiprocessing
import json

from aiohttp import web
from fledge.common import utils
from fledge.common.audit_logger import AuditLogger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.logger import FLCoreLogger
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect, server
from fledge.services.core.api.plugins import common


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019-2023, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ------------------------------------------------------------------------
    | PUT             | /fledge/plugins/{package_name}                     |
    ------------------------------------------------------------------------
"""
_logger = FLCoreLogger().get_logger(__name__)


# only work with core 2.1.0 onwards version
async def update_package(request: web.Request) -> web.Response:
    """ Update Package

    package_name: package name of plugin

    Example:
        curl -sX PUT http://localhost:8081/fledge/plugins/fledge-south-modbus
        curl -sX PUT http://localhost:8081/fledge/plugins/fledge-north-http-north
        curl -sX PUT http://localhost:8081/fledge/plugins/fledge-filter-scale
        curl -sX PUT http://localhost:8081/fledge/plugins/fledge-notify-alexa
        curl -sX PUT http://localhost:8081/fledge/plugins/fledge-rule-watchdog
    """

    try:
        valid_plugin_types = ['north', 'south', 'filter', 'notify', 'rule']
        package_name = request.match_info.get('package_name', "fledge-")
        package_name = package_name.replace(" ", "")
        final_response = {}
        if not package_name.startswith("fledge-"):
            raise ValueError("Package name should start with 'fledge-' prefix.")
        plugin_type = package_name.split("-", 2)[1]
        if not plugin_type:
            raise ValueError('Invalid Package name. Check and verify the package name in plugins installed.')
        if plugin_type not in valid_plugin_types:
            raise ValueError("Invalid plugin type. Please provide valid type: {}".format(valid_plugin_types))
        installed_plugins = PluginDiscovery.get_plugins_installed(plugin_type, False)
        plugin_info = [_plugin["name"] for _plugin in installed_plugins if _plugin["packageName"] == package_name]
        if not plugin_info:
            raise KeyError("{} package not found. Either package is not installed or missing in plugins installed."
                           "".format(package_name))
        plugin_name = plugin_info[0]
        # Check Pre-conditions from Packages table
        # if status is -1 (Already in progress) then return as rejected request
        action = 'update'
        storage_client = connect.get_storage_async()
        select_payload = PayloadBuilder().SELECT("status").WHERE(['action', '=', action]).AND_WHERE(
            ['name', '=', package_name]).payload()
        result = await storage_client.query_tbl_with_payload('packages', select_payload)
        response = result['rows']
        if response:
            exit_code = response[0]['status']
            if exit_code == -1:
                msg = "{} package {} already in progress.".format(package_name, action)
                return web.HTTPTooManyRequests(reason=msg, body=json.dumps({"message": msg}))
            # Remove old entry from table for other cases
            delete_payload = PayloadBuilder().WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            await storage_client.delete_from_tbl("packages", delete_payload)

        schedules = []
        notifications = []
        if plugin_type in ['notify', 'rule']:
            # Check Notification service is enabled or not
            payload = PayloadBuilder().SELECT("id", "enabled", "schedule_name").WHERE(['process_name', '=',
                                                                                       'notification_c']).payload()
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
                    if (channel == plugin_name and is_enabled) or (rule == plugin_name and is_enabled):
                        _logger.warning(
                            "Disabling {} notification instance, as {} {} plugin is being updated...".format(
                                notification_name, plugin_name, plugin_type))
                        await config_mgr.set_category_item_value_entry(notification_name, "enable", "false")
                        notifications.append(notification_name)
        else:
            # FIXME: if any south/north service or task doesnot have tracked by Fledge;
            #  then we need to handle the case to disable the service or task if enabled
            # Tracked plugins from asset tracker
            tracked_plugins = await _get_plugin_and_sch_name_from_asset_tracker(plugin_type)
            filters_used_by = []
            if plugin_type == 'filter':
                # In case of filter, for asset_tracker table we are inserting filter category_name in plugin column
                # instead of filter plugin name by Design
                # Hence below query is required to get actual plugin name from filters table
                storage_client = connect.get_storage_async()
                payload = PayloadBuilder().SELECT("name").WHERE(['plugin', '=', plugin_name]).payload()
                result = await storage_client.query_tbl_with_payload('filters', payload)
                filters_used_by = [r['name'] for r in result['rows']]
            for p in tracked_plugins:
                if (plugin_name == p['plugin'] and not plugin_type == 'filter') or (
                        p['plugin'] in filters_used_by and plugin_type == 'filter'):
                    sch_info = await _get_sch_id_and_enabled_by_name(p['service'])
                    if sch_info[0]['enabled'] == 't':
                        status, reason = await server.Server.scheduler.disable_schedule(uuid.UUID(sch_info[0]['id']))
                        if status:
                            _logger.warning("Disabling {} {} instance, as {} plugin is being updated...".format(
                                p['service'], plugin_type, plugin_name))
                            schedules.append(sch_info[0]['id'])
        # Insert record into Packages table
        insert_payload = PayloadBuilder().INSERT(id=str(uuid.uuid4()), name=package_name, action=action, status=-1,
                                                 log_file_uri="").payload()
        result = await storage_client.insert_into_tbl("packages", insert_payload)
        response = result['response']
        if response:
            select_payload = PayloadBuilder().SELECT("id").WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            result = await storage_client.query_tbl_with_payload('packages', select_payload)
            response = result['rows']
            if response:
                pn = "{}-{}".format(action, package_name)
                uid = response[0]['id']
                p = multiprocessing.Process(name=pn,
                                            target=do_update,
                                            args=(server.Server.is_rest_server_http_enabled,
                                                  server.Server._host, server.Server.core_management_port,
                                                  storage_client, plugin_type, plugin_name, package_name, uid,
                                                  schedules, notifications))
                p.daemon = True
                p.start()
                msg = "{} {} started.".format(package_name, action)
                status_link = "fledge/package/{}/status?id={}".format(action, uid)
                final_response = {"message": msg, "id": uid, "statusLink": status_link}
        else:
            raise StorageServerError
    except KeyError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({'message': msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({'message': msg}))
    except StorageServerError as e:
        msg = e.error
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to update {} package.".format(package_name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({'message': msg}))
    else:
        return web.json_response(final_response)


# only work with lesser or equal to version of core 2.1.0 version
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
            raise ValueError("Invalid plugin type. Must be one of 'south' , north', 'filter', 'notify' or 'rule'")
        # only OMF is an inbuilt plugin
        if name.lower() == 'omf':
            raise ValueError("Cannot update an inbuilt {} plugin.".format(name.upper()))
        # Check requested plugin name is installed or not
        installed_plugins = PluginDiscovery.get_plugins_installed(_type, False)
        plugin_info = [(_plugin["name"], _plugin["packageName"]) for _plugin in installed_plugins]
        package_name = "fledge-{}-{}".format(_type, name.lower().replace('_', '-'))
        plugin_found = False
        for p in plugin_info:
            if p[0] == name:
                package_name = p[1]
                plugin_found = True
                break
        if not plugin_found:
            raise KeyError("{} plugin is not yet installed. So update is not possible.".format(name))

        # Check Pre-conditions from Packages table
        # if status is -1 (Already in progress) then return as rejected request
        result_payload = {}
        action = 'update'
        storage_client = connect.get_storage_async()
        select_payload = PayloadBuilder().SELECT("status").WHERE(['action', '=', action]).AND_WHERE(
            ['name', '=', package_name]).payload()
        result = await storage_client.query_tbl_with_payload('packages', select_payload)
        response = result['rows']
        if response:
            exit_code = response[0]['status']
            if exit_code == -1:
                msg = "{} package {} already in progress.".format(package_name, action)
                return web.HTTPTooManyRequests(reason=msg, body=json.dumps({"message": msg}))
            # Remove old entry from table for other cases
            delete_payload = PayloadBuilder().WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            await storage_client.delete_from_tbl("packages", delete_payload)

        schedules = []
        notifications = []
        if _type in ['notify', 'rule']:
            # Check Notification service is enabled or not
            payload = PayloadBuilder().SELECT("id", "enabled", "schedule_name").WHERE(['process_name', '=',
                                                                                       'notification_c']).payload()
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
                        _logger.warning("Disabling {} notification instance, as {} {} plugin is being updated...".format(
                            notification_name, name, _type))
                        await config_mgr.set_category_item_value_entry(notification_name, "enable", "false")
                        notifications.append(notification_name)
        else:
            # FIXME: if any south/north service or task doesnot have tracked by Fledge;
            #  then we need to handle the case to disable the service or task if enabled
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
                if (name == p['plugin'] and not _type == 'filter') or (
                        p['plugin'] in filters_used_by and _type == 'filter'):
                    sch_info = await _get_sch_id_and_enabled_by_name(p['service'])
                    if sch_info[0]['enabled'] == 't':
                        status, reason = await server.Server.scheduler.disable_schedule(uuid.UUID(sch_info[0]['id']))
                        if status:
                            _logger.warning("Disabling {} {} instance, as {} plugin is being updated...".format(
                                p['service'], _type, name))
                            schedules.append(sch_info[0]['id'])
        # Insert record into Packages table
        insert_payload = PayloadBuilder().INSERT(id=str(uuid.uuid4()), name=package_name, action=action, status=-1,
                                                 log_file_uri="").payload()
        result = await storage_client.insert_into_tbl("packages", insert_payload)
        response = result['response']
        if response:
            select_payload = PayloadBuilder().SELECT("id").WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            result = await storage_client.query_tbl_with_payload('packages', select_payload)
            response = result['rows']
            if response:
                pn = "{}-{}".format(action, name)
                uid = response[0]['id']
                p = multiprocessing.Process(name=pn,
                                            target=do_update,
                                            args=(server.Server.is_rest_server_http_enabled,
                                                  server.Server._host, server.Server.core_management_port,
                                                  storage_client, _type, name, package_name, uid,
                                                  schedules, notifications))
                p.daemon = True
                p.start()
                msg = "{} {} started.".format(package_name, action)
                status_link = "fledge/package/{}/status?id={}".format(action, uid)
                result_payload = {"message": msg, "id": uid, "statusLink": status_link}
        else:
            raise StorageServerError
    except KeyError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except StorageServerError as e:
        msg = e.error
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to update {} plugin.".format(name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({'message': msg}))
    else:
        return web.json_response(result_payload)


async def _get_plugin_and_sch_name_from_asset_tracker(_type: str) -> list:
    if _type == "south":
        event_name = "Ingest"
    elif _type == "filter":
        event_name = "Filter"
    elif _type == "north":
        event_name = "Egress"
    else:
        # Return empty if _type is different
        return []
    storage_client = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("plugin", "service").WHERE(['event', '=', event_name]).payload()
    result = await storage_client.query_tbl_with_payload('asset_tracker', payload)
    return result['rows']


async def _get_sch_id_and_enabled_by_name(name: str) -> list:
    storage_client = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("id", "enabled").WHERE(['schedule_name', '=', name]).payload()
    result = await storage_client.query_tbl_with_payload('schedules', payload)
    return result['rows']


async def _put_schedule(protocol: str, host: str, port: int, sch_id: uuid, is_enabled: bool) -> None:
    management_api_url = '{}://{}:{}/fledge/schedule/{}/enable'.format(protocol, host, port, sch_id)
    headers = {'content-type': 'application/json'}
    verify_ssl = False if protocol == 'HTTP' else True
    connector = aiohttp.TCPConnector(verify_ssl=verify_ssl)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.put(management_api_url, data=json.dumps({"value": is_enabled}), headers=headers) as resp:
            result = await resp.text()
            status_code = resp.status
            if status_code in range(400, 500):
                _logger.error("Bad request error code: {}, reason: {} when PUT schedule".format(status_code, resp.reason))
            if status_code in range(500, 600):
                _logger.error("Server error code: {}, reason: {} when PUT schedule".format(status_code, resp.reason))
            response = json.loads(result)
            _logger.debug("PUT Schedule response: {}".format(response))


def _update_repo_sources_and_plugin(pkg_name: str) -> tuple:
    stdout_file_path = common.create_log_file(action="update", plugin_name=pkg_name)
    pkg_mgt = 'apt'
    cmd = "sudo {} -y update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    if utils.is_redhat_based():
        pkg_mgt = 'yum'
        cmd = "sudo {} check-update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    ret_code = os.system(cmd)
    # sudo apt/yum -y install only happens when update is without any error
    if ret_code == 0:
        cmd = "sudo {} -y install {} >> {} 2>&1".format(pkg_mgt, pkg_name, stdout_file_path)
        ret_code = os.system(cmd)

    # relative log file link
    link = "log/" + stdout_file_path.split("/")[-1]
    return ret_code, link


def do_update(http_enabled: bool, host: str, port: int, storage: connect, _type: str, plugin_name: str,
              pkg_name: str, uid: str, schedules: list, notifications: list) -> None:
    _logger.info("{} package update started...".format(pkg_name))
    
    # Protocol is always http:// on core_management_port
    protocol = "HTTP"

    code, link = _update_repo_sources_and_plugin(pkg_name)

    # Update record in Packages table
    payload = PayloadBuilder().SET(status=code, log_file_uri=link).WHERE(['id', '=', uid]).payload()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(storage.update_tbl("packages", payload))

    if code == 0:
        # Audit info
        audit = AuditLogger(storage)
        installed_plugins = PluginDiscovery.get_plugins_installed(_type, False)
        version = [p["version"] for p in installed_plugins if p['name'] == plugin_name]
        audit_detail = {'packageName': pkg_name}
        if version:
            audit_detail['version'] = version[0]
        loop.run_until_complete(audit.information('PKGUP', audit_detail))
        _logger.info('{} package updated successfully.'.format(pkg_name))
    # Restart the services which were disabled before plugin update
    for sch in schedules:
        loop.run_until_complete(_put_schedule(protocol, host, port, uuid.UUID(sch), True))

    # Below case is applicable for the notification plugins ONLY
    # Enabled back configuration categories which were disabled during update process
    if _type in ['notify', 'rule']:
        config_mgr = ConfigurationManager(storage)
        for notify in notifications:
            loop.run_until_complete(config_mgr.set_category_item_value_entry(notify, "enable", "true"))
