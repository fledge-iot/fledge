# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import aiohttp
import os
import json
import asyncio
import uuid
import multiprocessing

from aiohttp import web
from fledge.common import utils
from fledge.common.audit_logger import AuditLogger
from fledge.common.common import _FLEDGE_ROOT
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.logger import FLCoreLogger
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect
from fledge.services.core.api.plugins import common
from fledge.services.core.api.plugins.exceptions import *


__author__ = "Rajesh Kumar, Ashish Jabble"
__copyright__ = "Copyright (c) 2020-2023, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    --------------------------------------------------------------------
    | DELETE             | /fledge/plugins/{package_name}              |
    --------------------------------------------------------------------
"""

_logger = FLCoreLogger().get_logger(__name__)
valid_plugin_types = ['north', 'south', 'filter', 'notify', 'rule']
PYTHON_PLUGIN_PATH = _FLEDGE_ROOT+'/python/fledge/plugins/'
C_PLUGINS_PATH = _FLEDGE_ROOT+'/plugins/'


# only work with core 2.1.0 onwards version
async def remove_package(request: web.Request) -> web.Response:
    """Remove installed Package

    package_name: package name of plugin

    Example:
        curl -sX DELETE http://localhost:8081/fledge/plugins/fledge-south-modbus
        curl -sX DELETE http://localhost:8081/fledge/plugins/fledge-north-http-north
        curl -sX DELETE http://localhost:8081/fledge/plugins/fledge-filter-scale
        curl -sX DELETE http://localhost:8081/fledge/plugins/fledge-notify-alexa
        curl -sX DELETE http://localhost:8081/fledge/plugins/fledge-rule-watchdog
    """
    try:
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
        plugin_info = [(_plugin["name"], _plugin["version"]) for _plugin in installed_plugins
                       if _plugin["packageName"] == package_name]
        if not plugin_info:
            raise KeyError("{} package not found. Either package is not installed or missing in plugins installed."
                           "".format(package_name))
        plugin_name = plugin_info[0][0]
        plugin_version = plugin_info[0][1]
        if plugin_type in ['notify', 'rule']:
            notification_instances_plugin_used_in = await _check_plugin_usage_in_notification_instances(plugin_name)
            if notification_instances_plugin_used_in:
                err_msg = "{} cannot be removed. This is being used by {} instances.".format(
                    plugin_name, notification_instances_plugin_used_in)
                _logger.warning(err_msg)
                raise RuntimeError(err_msg)
        else:
            get_tracked_plugins = await _check_plugin_usage(plugin_type, plugin_name)
            if get_tracked_plugins:
                e = "{} cannot be removed. This is being used by {} instances.". \
                    format(plugin_name, get_tracked_plugins[0]['service_list'])
                _logger.warning(e)
                raise RuntimeError(e)
            else:
                _logger.info("No entry found for {name} plugin in asset tracker; "
                             "or {name} plugin may have been added in disabled state & never used."
                             "".format(name=plugin_name))
        # Check Pre-conditions from Packages table
        # if status is -1 (Already in progress) then return as rejected request
        action = 'purge'
        storage = connect.get_storage_async()
        select_payload = PayloadBuilder().SELECT("status").WHERE(['action', '=', action]).AND_WHERE(
            ['name', '=', package_name]).payload()
        result = await storage.query_tbl_with_payload('packages', select_payload)
        response = result['rows']
        if response:
            exit_code = response[0]['status']
            if exit_code == -1:
                msg = "{} package purge already in progress.".format(package_name)
                return web.HTTPTooManyRequests(reason=msg, body=json.dumps({"message": msg}))
            # Remove old entry from table for other cases
            delete_payload = PayloadBuilder().WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            await storage.delete_from_tbl("packages", delete_payload)

        # Insert record into Packages table
        insert_payload = PayloadBuilder().INSERT(id=str(uuid.uuid4()), name=package_name, action=action,
                                                 status=-1, log_file_uri="").payload()
        result = await storage.insert_into_tbl("packages", insert_payload)
        response = result['response']
        if response:
            select_payload = PayloadBuilder().SELECT("id").WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            result = await storage.query_tbl_with_payload('packages', select_payload)
            response = result['rows']
            if response:
                pn = "{}-{}".format(action, plugin_name)
                uid = response[0]['id']
                p = multiprocessing.Process(name=pn,
                                            target=_uninstall,
                                            args=(package_name, plugin_version, uid, storage)
                                            )
                p.daemon = True
                p.start()
                msg = "{} plugin remove started.".format(plugin_name)
                status_link = "fledge/package/{}/status?id={}".format(action, uid)
                final_response = {"message": msg, "id": uid, "statusLink": status_link}
        else:
            raise StorageServerError
    except (ValueError, RuntimeError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({'message': msg}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({'message': msg}))
    except StorageServerError as e:
        msg = e.error
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to delete {} package.".format(package_name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({'message': msg}))
    else:
        return web.json_response(final_response)


def _uninstall(pkg_name: str, version: str, uid: uuid, storage: connect) -> tuple:
    from fledge.services.core.server import Server
    _logger.info("{} package removal started...".format(pkg_name))
    stdout_file_path = ''
    try:
        stdout_file_path = common.create_log_file(action='remove', plugin_name=pkg_name)
        link = "log/" + stdout_file_path.split("/")[-1]
        if utils.is_redhat_based():
            cmd = "sudo yum -y remove {} > {} 2>&1".format(pkg_name, stdout_file_path)
        else:
            cmd = "sudo apt -y purge {} > {} 2>&1".format(pkg_name, stdout_file_path)
        code = os.system(cmd)
        # Update record in Packages table
        payload = PayloadBuilder().SET(status=code, log_file_uri=link).WHERE(['id', '=', uid]).payload()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(storage.update_tbl("packages", payload))
        if code == 0:
            # Clear internal cache
            loop.run_until_complete(_put_refresh_cache(Server.is_rest_server_http_enabled,
                                                       Server._host, Server.core_management_port))
            # Audit logger
            audit = AuditLogger(storage)
            audit_detail = {'package_name': pkg_name, 'version': version}
            loop.run_until_complete(audit.information('PKGRM', audit_detail))
            _logger.info('{} removed successfully.'.format(pkg_name))
    except Exception:
        # Non-Zero integer - Case of fail
        code = 1
    return code, stdout_file_path


# only work with lesser or equal to version of core 2.1.0 version
async def remove_plugin(request: web.Request) -> web.Response:
    """ Remove installed plugin from fledge

    type: installed plugin type
    name: installed plugin name

    Example:
        curl -X DELETE http://localhost:8081/fledge/plugins/south/sinusoid
        curl -X DELETE http://localhost:8081/fledge/plugins/north/http_north
        curl -X DELETE http://localhost:8081/fledge/plugins/filter/expression
        curl -X DELETE http://localhost:8081/fledge/plugins/notify/alexa
        curl -X DELETE http://localhost:8081/fledge/plugins/rule/Average
    """
    plugin_type = request.match_info.get('type', None)
    name = request.match_info.get('name', None)
    try:
        plugin_type = str(plugin_type).lower()
        if plugin_type not in valid_plugin_types:
            raise ValueError("Invalid plugin type. Please provide valid type: {}".format(valid_plugin_types))
        # only OMF is an inbuilt plugin
        if name.lower() == 'omf':
            raise ValueError("Cannot delete an inbuilt {} plugin.".format(name.upper()))
        result_payload = {}
        installed_plugins = PluginDiscovery.get_plugins_installed(plugin_type, False)
        plugin_info = [(_plugin["name"], _plugin["packageName"], _plugin["version"]) for _plugin in installed_plugins]
        package_name = "fledge-{}-{}".format(plugin_type, name.lower().replace("_", "-"))
        plugin_found = False
        plugin_version = None
        for p in plugin_info:
            if p[0] == name:
                package_name = p[1]
                plugin_version = p[2]
                plugin_found = True
                break
        if not plugin_found:
            raise KeyError("Invalid plugin name {} or plugin is not installed.".format(name))
        if plugin_type in ['notify', 'rule']:
            notification_instances_plugin_used_in = await _check_plugin_usage_in_notification_instances(name)
            if notification_instances_plugin_used_in:
                err_msg = "{} cannot be removed. This is being used by {} instances.".format(
                    name, notification_instances_plugin_used_in)
                _logger.warning(err_msg)
                raise RuntimeError(err_msg)
        else:
            get_tracked_plugins = await _check_plugin_usage(plugin_type, name)
            if get_tracked_plugins:
                e = "{} cannot be removed. This is being used by {} instances.".\
                    format(name, get_tracked_plugins[0]['service_list'])
                _logger.warning(e)
                raise RuntimeError(e)
            else:
                _logger.info("No entry found for {name} plugin in asset tracker; or "
                             "{name} plugin may have been added in disabled state & never used.".format(name=name))
        # Check Pre-conditions from Packages table
        # if status is -1 (Already in progress) then return as rejected request
        action = 'purge'
        storage = connect.get_storage_async()
        select_payload = PayloadBuilder().SELECT("status").WHERE(['action', '=', action]).AND_WHERE(
            ['name', '=', package_name]).payload()
        result = await storage.query_tbl_with_payload('packages', select_payload)
        response = result['rows']
        if response:
            exit_code = response[0]['status']
            if exit_code == -1:
                msg = "{} package purge already in progress.".format(package_name)
                return web.HTTPTooManyRequests(reason=msg, body=json.dumps({"message": msg}))
            # Remove old entry from table for other cases
            delete_payload = PayloadBuilder().WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            await storage.delete_from_tbl("packages", delete_payload)

        # Insert record into Packages table
        insert_payload = PayloadBuilder().INSERT(id=str(uuid.uuid4()), name=package_name, action=action, status=-1,
                                                 log_file_uri="").payload()
        result = await storage.insert_into_tbl("packages", insert_payload)
        response = result['response']
        if response:
            select_payload = PayloadBuilder().SELECT("id").WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            result = await storage.query_tbl_with_payload('packages', select_payload)
            response = result['rows']
            if response:
                pn = "{}-{}".format(action, name)
                uid = response[0]['id']
                p = multiprocessing.Process(name=pn,
                                            target=purge_plugin,
                                            args=(plugin_type, name, package_name, plugin_version, uid, storage)
                                            )
                p.daemon = True
                p.start()
                msg = "{} plugin remove started.".format(name)
                status_link = "fledge/package/{}/status?id={}".format(action, uid)
                result_payload = {"message": msg, "id": uid, "statusLink": status_link}
        else:
            raise StorageServerError
    except (ValueError, RuntimeError) as err:
        raise web.HTTPBadRequest(reason=str(err), body=json.dumps({'message': str(err)}))
    except KeyError as err:
        raise web.HTTPNotFound(reason=str(err), body=json.dumps({'message': str(err)}))
    except StorageServerError as e:
        msg = e.error
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to remove {} plugin.".format(name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({'message': msg}))
    else:
        return web.json_response(result_payload)


async def _check_plugin_usage(plugin_type: str, plugin_name: str) -> list:
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
            service_in_schedules_list = await _check_service_in_schedules(list_of_tracked_plugin['rows'][r]['service'])
            for p in filter_used:
                if p in list_of_tracked_plugin['rows'][r]['plugin'] and service_in_schedules_list:
                    service_list.append(list_of_tracked_plugin['rows'][r]['service'])
                    break
    if list_of_tracked_plugin['rows']:
        for e in list_of_tracked_plugin['rows']:
            if (plugin_name == e['plugin'] and plugin_type != 'filter') or (e['plugin'] in filter_used and
                                                                            plugin_type == 'filter'):
                service_in_list = await _check_service_in_schedules(e['service'])
                if (plugin_name in [x['plugin'] for x in list_of_tracked_plugin['rows']] and service_in_list) \
                        or (e['plugin'] in filter_used and service_in_list):
                    if service_list:
                        plugin_users.append({'e': e, 'service_list': service_list})
                    else:
                        service_list.append(e['service'])
                        plugin_users.append({'e': e, 'service_list': service_list})
    return plugin_users


async def _check_service_in_schedules(service_name: str) -> bool:
    storage_client = connect.get_storage_async()
    payload_data = PayloadBuilder().SELECT('id', 'enabled').WHERE(['schedule_name', '=', service_name]).payload()
    enabled_service_list = await storage_client.query_tbl_with_payload('schedules', payload_data)
    is_service_list = True if enabled_service_list['rows'] else False
    return is_service_list


async def _check_plugin_usage_in_notification_instances(plugin_name: str) -> list:
    """ Check notification instance state using the given rule or delivery plugin
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


async def _put_refresh_cache(protocol: str, host: int, port: int) -> None:
    management_api_url = '{}://{}:{}/fledge/cache'.format(protocol, host, port)
    headers = {'content-type': 'application/json'}
    verify_ssl = False if protocol == 'HTTP' else True
    connector = aiohttp.TCPConnector(verify_ssl=verify_ssl)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.put(management_api_url, data=json.dumps({}), headers=headers) as resp:
            result = await resp.text()
            status_code = resp.status
            if status_code in range(400, 500):
                _logger.error("Bad request error code: {}, reason: {} when refresh cache".format(status_code, resp.reason))
            if status_code in range(500, 600):
                _logger.error("Server error code: {}, reason: {} when refresh cache".format(status_code, resp.reason))
            response = json.loads(result)
            _logger.debug("PUT Refresh Cache response: {}".format(response))


def purge_plugin(plugin_type: str, plugin_name: str, pkg_name: str, version: str, uid: uuid, storage: connect) -> tuple:
    from fledge.services.core.server import Server
    _logger.info("{} plugin remove started...".format(pkg_name))
    is_package = True
    stdout_file_path = ''
    try:
        if utils.is_redhat_based():
            rpm_list = os.popen('rpm -qa | grep fledge*').read()
            _logger.debug("rpm list : {}".format(rpm_list))
            if len(rpm_list):
                f = rpm_list.find(pkg_name)
                if f == -1:
                    raise KeyError
            else:
                raise KeyError
            stdout_file_path = common.create_log_file(action='remove', plugin_name=pkg_name)
            link = "log/" + stdout_file_path.split("/")[-1]
            cmd = "sudo yum -y remove {} > {} 2>&1".format(pkg_name, stdout_file_path)
        else:
            dpkg_list = os.popen('dpkg --list "fledge*" 2>/dev/null')
            ls_output = dpkg_list.read()
            _logger.debug("dpkg list output: {}".format(ls_output))
            if len(ls_output):
                f = ls_output.find(pkg_name)
                if f == -1:
                    raise KeyError
            else:
                raise KeyError
            stdout_file_path = common.create_log_file(action='remove', plugin_name=pkg_name)
            link = "log/" + stdout_file_path.split("/")[-1]
            cmd = "sudo apt -y purge {} > {} 2>&1".format(pkg_name, stdout_file_path)

        code = os.system(cmd)
        # Update record in Packages table
        payload = PayloadBuilder().SET(status=code, log_file_uri=link).WHERE(['id', '=', uid]).payload()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(storage.update_tbl("packages", payload))

        if code == 0:
            # Clear internal cache
            loop.run_until_complete(_put_refresh_cache(Server.is_rest_server_http_enabled,
                                                       Server._host, Server.core_management_port))
            # Audit info
            audit = AuditLogger(storage)
            audit_detail = {'package_name': pkg_name, 'version': version}
            loop.run_until_complete(audit.information('PKGRM', audit_detail))
            _logger.info('{} plugin removed successfully.'.format(pkg_name))
    except KeyError:
        # This case is for non-package installation - python plugin path will be tried first and then C
        _logger.info("Trying removal of manually installed plugin...")
        is_package = False
        if plugin_type in ['notify', 'rule']:
            plugin_type = 'notificationDelivery' if plugin_type == 'notify' else 'notificationRule'
        try:
            path = PYTHON_PLUGIN_PATH+'{}/{}'.format(plugin_type, plugin_name)
            if not os.path.isdir(path):
                path = C_PLUGINS_PATH + '{}/{}'.format(plugin_type, plugin_name)
            rm_cmd = 'rm -rv {}'.format(path)
            if os.path.exists("{}/bin".format(_FLEDGE_ROOT)) and os.path.exists("{}/bin/fledge".format(_FLEDGE_ROOT)):
                rm_cmd = 'sudo rm -rv {}'.format(path)
            code = os.system(rm_cmd)
            if code != 0:
                raise OSError("While deleting, invalid plugin path found for {}".format(plugin_name))
        except Exception as ex:
            code = 1
            _logger.error(ex, "Error in removing plugin.")
        _logger.info('{} plugin removed successfully.'.format(plugin_name))
    return code, stdout_file_path, is_package
