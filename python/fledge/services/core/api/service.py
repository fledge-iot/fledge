# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import aiohttp
import asyncio
import os
import datetime
import uuid
import platform
import json
import multiprocessing
from aiohttp import web

from typing import Dict, List
from fledge.common import utils
from fledge.common import logger
from fledge.common.service_record import ServiceRecord
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core import server
from fledge.services.core import connect
from fledge.services.core.api import utils as apiutils
from fledge.services.core.scheduler.entities import StartUpSchedule
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.common.common import _FLEDGE_ROOT
from fledge.services.core.api.plugins import common
from fledge.services.core.api.plugins import install
from fledge.services.core.api.plugins.exceptions import *
from fledge.common.audit_logger import AuditLogger


__author__ = "Mark Riddoch, Ashwin Gopalakrishnan, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ------------------------------------------------------------------------------
    | GET POST            | /fledge/service                                      |
    | GET                 | /fledge/service/available                            |
    | GET                 | /fledge/service/installed                            |
    | PUT                 | /fledge/service/{type}/{name}/update                 |
    | DELETE              | /fledge/service/{service_name}                       |
    ------------------------------------------------------------------------------
"""

_logger = logger.setup()

#################################
#  Service
#################################


def get_service_records():
    sr_list = list()
    for service_record in ServiceRegistry.all():
        sr_list.append(
            {
                'name': service_record._name,
                'type': service_record._type,
                'address': service_record._address,
                'management_port': service_record._management_port,
                'service_port': service_record._port,
                'protocol': service_record._protocol,
                'status': ServiceRecord.Status(int(service_record._status)).name.lower()
            })
    recs = {'services': sr_list}
    return recs


def get_service_installed() -> List:
    paths = [_FLEDGE_ROOT + "/services", _FLEDGE_ROOT + "/python/fledge/services/management"]
    services = []
    svc_prefix = 'fledge.services.'
    for _path in paths:
        for root, dirs, files in os.walk(_path):
            for _file in files:
                if _file.startswith(svc_prefix):
                    services.append(_file.split(svc_prefix)[-1])
                elif _file == '__main__.py':
                    services.append('management')
    return services


async def get_health(request):
    """
    Args:
        request:

    Returns:
            health of all registered services

    :Example:
            curl -X GET http://localhost:8081/fledge/service
    """
    response = get_service_records()
    return web.json_response(response)


async def delete_service(request):
    """ Delete an existing service

    :Example:
        curl -X DELETE http://localhost:8081/fledge/service/<svc name>
    """
    try:
        svc = request.match_info.get('service_name', None)
        storage = connect.get_storage_async()

        result = await get_schedule(storage, svc)
        if result['count'] == 0:
            return web.HTTPNotFound(reason='{} service does not exist.'.format(svc))

        config_mgr = ConfigurationManager(storage)

        # TODO: 5141 - once done we need to fix for dispatcher type as well
        # In case of notification service, if notifications exists, then deletion is not allowed
        if 'notification' in result['rows'][0]['process_name']:
            notf_children = await config_mgr.get_category_child(category_name="Notifications")
            children = [x['key'] for x in notf_children]
            if len(notf_children) > 0:
                return web.HTTPBadRequest(reason='Notification service `{}` can not be deleted, as {} notification instances exist.'.format(svc, children))

        # First disable the schedule
        svc_schedule = result['rows'][0]
        sch_id = uuid.UUID(svc_schedule['id'])
        if svc_schedule['enabled'].lower() == 't':
            await server.Server.scheduler.disable_schedule(sch_id)
            # return control to event loop
            await asyncio.sleep(1)

        # Delete all configuration for the service name
        await config_mgr.delete_category_and_children_recursively(svc)

        # Remove from registry as it has been already shutdown via disable_schedule() and since
        # we intend to delete the schedule also, there is no use of its Service registry entry
        try:
            services = ServiceRegistry.get(name=svc)
            ServiceRegistry.remove_from_registry(services[0]._id)
        except service_registry_exceptions.DoesNotExist:
            pass

        await delete_streams(storage, svc)
        await delete_plugin_data(storage, svc)

        # Delete schedule
        await server.Server.scheduler.delete_schedule(sch_id)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))
    else:
        return web.json_response({'result': 'Service {} deleted successfully.'.format(svc)})


async def delete_streams(storage, north_instance):
    payload = PayloadBuilder().WHERE(["description", "=", north_instance]).payload()
    await storage.delete_from_tbl("streams", payload)

async def delete_plugin_data(storage, north_instance):
    payload = PayloadBuilder().WHERE(["key", "like", north_instance + "%"]).payload()
    await storage.delete_from_tbl("plugin_data", payload)


async def add_service(request):
    """
    Create a new service to run a specific plugin

    :Example:
             curl -X POST http://localhost:8081/fledge/service -d '{"name": "DHT 11", "plugin": "dht11", "type": "south", "enabled": true}'
             curl -sX POST http://localhost:8081/fledge/service -d '{"name": "Sine", "plugin": "sinusoid", "type": "south", "enabled": true, "config": {"dataPointsPerSec": {"value": "10"}}}' | jq
             curl -X POST http://localhost:8081/fledge/service -d '{"name": "NotificationServer", "type": "notification", "enabled": true}' | jq
             curl -sX POST http://localhost:8081/fledge/service -d '{"name": "DispatcherServer", "type": "dispatcher", "enabled": true}' | jq
             curl -X POST http://localhost:8081/fledge/service -d '{"name": "HTC", "plugin": "httpc", "type": "north", "enabled": true}' | jq
             curl -sX POST http://localhost:8081/fledge/service -d '{"name": "HT", "plugin": "http_north", "type": "north", "enabled": true, "config": {"verifySSL": {"value": "false"}}}' | jq

             curl -sX POST http://localhost:8081/fledge/service?action=install -d '{"format":"repository", "name": "fledge-service-notification"}'
             curl -sX POST http://localhost:8081/fledge/service?action=install -d '{"format":"repository", "name": "fledge-service-dispatcher"}'
             curl -sX POST http://localhost:8081/fledge/service?action=install -d '{"format":"repository", "name": "fledge-service-notification", "version":"1.6.0"}'
             curl -sX POST http://localhost:8081/fledge/service?action=install -d '{"format":"repository", "name": "fledge-service-dispatcher", "version":"1.9.1"}'
    """

    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a valid JSON')

        name = data.get('name', None)
        plugin = data.get('plugin', None)
        service_type = data.get('type', None)
        enabled = data.get('enabled', None)
        config = data.get('config', None)

        if name is None:
            raise web.HTTPBadRequest(reason='Missing name property in payload.')
        if 'action' in request.query and request.query['action'] != '':
            if request.query['action'] == 'install':
                file_format = data.get('format', None)
                if file_format is None:
                    raise ValueError("format param is required")
                if file_format not in ["repository"]:
                    raise ValueError("Invalid format. Must be 'repository'")
                if not name.startswith("fledge-service-"):
                    raise ValueError('name should start with "fledge-service-" prefix')
                version = data.get('version', None)
                if version:
                    delimiter = '.'
                    if str(version).count(delimiter) != 2:
                        raise ValueError('Service semantic version is incorrect; it should be like X.Y.Z')

                _platform = platform.platform()
                pkg_mgt = 'yum' if 'centos' in _platform or 'redhat' in _platform else 'apt'
                # Check Pre-conditions from Packages table
                # if status is -1 (Already in progress) then return as rejected request
                storage = connect.get_storage_async()
                action = "install"
                select_payload = PayloadBuilder().SELECT("status").WHERE(['action', '=', action]).AND_WHERE(
                    ['name', '=', name]).payload()
                result = await storage.query_tbl_with_payload('packages', select_payload)
                response = result['rows']
                if response:
                    exit_code = response[0]['status']
                    if exit_code == -1:
                        msg = "{} package installation already in progress".format(name)
                        return web.HTTPTooManyRequests(reason=msg, body=json.dumps({"message": msg}))
                    # Remove old entry from table for other cases
                    delete_payload = PayloadBuilder().WHERE(['action', '=', action]).AND_WHERE(
                        ['name', '=', name]).payload()
                    await storage.delete_from_tbl("packages", delete_payload)

                # Check If requested service is already installed and then return immediately
                services = get_service_installed()
                svc_name = name.split('fledge-')[1].split('-')[1]
                for s in services:
                    if s == svc_name:
                        msg = "{} package is already installed".format(name)
                        return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

                # Check If requested service is available for configured repository
                services, log_path = await common.fetch_available_packages("service")
                if name not in services:
                    raise KeyError('{} service is not available for the given repository'.format(name))
                
                # Insert record into Packages table
                uid = str(uuid.uuid4())
                insert_payload = PayloadBuilder().INSERT(id=uid, name=name, action=action, status=-1,
                                                         log_file_uri="").payload()
                result = await storage.insert_into_tbl("packages", insert_payload)
                if result['response'] == "inserted" and result['rows_affected'] == 1:
                    pn = "{}-{}".format(action, name)
                    p = multiprocessing.Process(name=pn, target=install.install_package_from_repo,
                                                args=(name, pkg_mgt, version, uid, storage))
                    p.daemon = True
                    p.start()
                    msg = "{} service installation started".format(name)
                    _logger.info("{}...".format(msg))
                    status_link = "fledge/package/install/status?id={}".format(uid)
                    return web.json_response({"message": msg, "id": uid, "statusLink": status_link})
                else:
                    raise StorageServerError
            else:
                raise web.HTTPBadRequest(reason='{} is not a valid action'.format(request.query['action']))
        if utils.check_reserved(name) is False:
            raise web.HTTPBadRequest(reason='Invalid name property in payload.')
        if utils.check_fledge_reserved(name) is False:
            raise web.HTTPBadRequest(reason="'{}' is reserved for Fledge and can not be used as service name!".format(name))
        if service_type is None:
            raise web.HTTPBadRequest(reason='Missing type property in payload.')

        service_type = str(service_type).lower()
        if service_type not in ['south', 'north', 'notification', 'management', 'dispatcher']:
            raise web.HTTPBadRequest(reason='Only south, north, notification, management and dispatcher '
                                            'types are supported.')
        if plugin is None and service_type == 'south':
            raise web.HTTPBadRequest(reason='Missing plugin property for type south in payload.')
        if plugin is None and service_type == 'north':
            raise web.HTTPBadRequest(reason='Missing plugin property for type north in payload.')
        if plugin and utils.check_reserved(plugin) is False:
            raise web.HTTPBadRequest(reason='Invalid plugin property in payload.')

        if enabled is not None:
            if enabled not in ['true', 'false', True, False]:
                raise web.HTTPBadRequest(reason='Only "true", "false", true, false'
                                                ' are allowed for value of enabled.')
        is_enabled = True if ((type(enabled) is str and enabled.lower() in ['true']) or (
            (type(enabled) is bool and enabled is True))) else False

        # Check if a valid plugin has been provided
        plugin_module_path, plugin_config, process_name, script = "", {}, "", ""
        if service_type == 'south' or service_type == 'north':
            # "plugin_module_path" is fixed by design. It is MANDATORY to keep the plugin in the exactly similar named
            # folder, within the plugin_module_path.
            # if multiple plugin with same name are found, then python plugin import will be tried first
            plugin_module_path = "{}/python/fledge/plugins/{}/{}".format(_FLEDGE_ROOT, service_type, plugin)
            process_name = 'south_c' if service_type == 'south' else 'north_C'
            script = '["services/south_c"]' if service_type == 'south' else '["services/north_C"]'
            try:
                plugin_info = common.load_and_fetch_python_plugin_info(plugin_module_path, plugin, service_type)
                plugin_config = plugin_info['config']
                if not plugin_config:
                    _logger.exception("Plugin %s import problem from path %s", plugin, plugin_module_path)
                    raise web.HTTPNotFound(reason='Plugin "{}" import problem from path "{}".'.format(
                        plugin, plugin_module_path))
            except FileNotFoundError as ex:
                # Checking for C-type plugins
                plugin_config = load_c_plugin(plugin, service_type)
                if not plugin_config:
                    _logger.exception("Plugin %s import problem from path %s. %s", plugin, plugin_module_path, str(ex))
                    raise web.HTTPNotFound(reason='Plugin "{}" import problem from path "{}".'.format(
                        plugin, plugin_module_path))
            except TypeError as ex:
                _logger.exception(str(ex))
                raise web.HTTPBadRequest(reason=str(ex))
            except Exception as ex:
                _logger.exception("Failed to fetch plugin configuration. %s", str(ex))
                raise web.HTTPInternalServerError(reason='Failed to fetch plugin configuration')
        elif service_type == 'notification':
            if not os.path.exists(_FLEDGE_ROOT + "/services/fledge.services.{}".format(service_type)):
                msg = "{} service is not installed correctly.".format(service_type.capitalize())
                raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
            process_name = 'notification_c'
            script = '["services/notification_c"]'
        elif service_type == 'management':
            file_names_list = ['{}/python/fledge/services/management/__main__.py'.format(_FLEDGE_ROOT),
                               '{}/scripts/services/management'.format(_FLEDGE_ROOT),
                               '{}/scripts/tasks/manage'.format(_FLEDGE_ROOT)]
            if not all(list(map(os.path.exists, file_names_list))):
                msg = "{} service is not installed correctly.".format(service_type.capitalize())
                raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
            process_name = 'management'
            script = '["services/management"]'
        elif service_type == 'dispatcher':
            if not os.path.exists(_FLEDGE_ROOT + "/services/fledge.services.{}".format(service_type)):
                msg = "{} service is not installed correctly.".format(service_type.capitalize())
                raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
            process_name = 'dispatcher_c'
            script = '["services/dispatcher_c"]'
        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)

        # Check  whether category name already exists
        category_info = await config_mgr.get_category_all_items(category_name=name)
        if category_info is not None:
            raise web.HTTPBadRequest(reason="The '{}' category already exists".format(name))

        # Check that the schedule name is not already registered
        count = await check_schedules(storage, name)
        if count != 0:
            raise web.HTTPBadRequest(reason='A service with this name already exists.')

        # Check that the process name is not already registered
        count = await check_scheduled_processes(storage, process_name, script)
        if count == 0:
            # Now first create the scheduled process entry for the new service
            payload = PayloadBuilder().INSERT(name=process_name, script=script).payload()
            try:
                res = await storage.insert_into_tbl("scheduled_processes", payload)
            except StorageServerError as ex:
                _logger.exception("Failed to create scheduled process. %s", ex.error)
                raise web.HTTPInternalServerError(reason='Failed to create service.')
            except Exception as ex:
                _logger.exception("Failed to create scheduled process. %s", str(ex))
                raise web.HTTPInternalServerError(reason='Failed to create service.')

        # check that notification service is not already registered, right now notification service LIMIT to 1
        if service_type == 'notification':
            res = await check_schedule_entry(storage)
            for ps in res['rows']:
                if 'notification_c' in ps['process_name']:
                    raise web.HTTPBadRequest(reason='A Notification service schedule already exists.')
        # check that dispatcher service is not already registered, right now dispatcher service LIMIT to 1
        elif service_type == 'dispatcher':
            res = await check_schedule_entry(storage)
            for ps in res['rows']:
                if 'dispatcher_c' in ps['process_name']:
                    raise web.HTTPBadRequest(reason='A Dispatcher service schedule already exists.')
        # check that management service is not already registered, right now management service LIMIT to 1
        elif service_type == 'management':
            res = await check_schedule_entry(storage)
            for ps in res['rows']:
                if 'management' in ps['process_name']:
                    raise web.HTTPBadRequest(reason='A Management service schedule already exists.')
        elif service_type == 'south' or service_type == 'north':
            try:
                # Create a configuration category from the configuration defined in the plugin
                category_desc = plugin_config['plugin']['description']
                await config_mgr.create_category(category_name=name,
                                                 category_description=category_desc,
                                                 category_value=plugin_config,
                                                 keep_original_items=True)
                # Create the parent category for all South services
                parent_cat_name = service_type.capitalize()
                await config_mgr.create_category(parent_cat_name, {}, "{} microservices".format(parent_cat_name), True)
                await config_mgr.create_child_category(parent_cat_name, [name])

                # If config is in POST data, then update the value for each config item
                if config is not None:
                    if not isinstance(config, dict):
                        raise ValueError('Config must be a JSON object')
                    for k, v in config.items():
                        await config_mgr.set_category_item_value_entry(name, k, v['value'])

            except Exception as ex:
                await config_mgr.delete_category_and_children_recursively(name)
                _logger.exception("Failed to create plugin configuration. %s", str(ex))
                raise web.HTTPInternalServerError(reason='Failed to create plugin configuration. {}'.format(ex))

        # If all successful then lastly add a schedule to run the new service at startup
        try:
            schedule = StartUpSchedule()
            schedule.name = name
            schedule.process_name = process_name
            schedule.repeat = datetime.timedelta(0)
            schedule.exclusive = True
            #  if "enabled" is supplied, it gets activated in save_schedule() via is_enabled flag
            schedule.enabled = False

            # Save schedule
            await server.Server.scheduler.save_schedule(schedule, is_enabled)
            schedule = await server.Server.scheduler.get_schedule_by_name(name)
        except StorageServerError as ex:
            await config_mgr.delete_category_and_children_recursively(name)
            _logger.exception("Failed to create schedule. %s", ex.error)
            raise web.HTTPInternalServerError(reason='Failed to create service.')
        except Exception as ex:
            await config_mgr.delete_category_and_children_recursively(name)
            _logger.exception("Failed to create service. %s", str(ex))
            raise web.HTTPInternalServerError(reason='Failed to create service.')
    except ValueError as e:
        raise web.HTTPBadRequest(reason=str(e))
    except KeyError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except StorageServerError as err:
        msg = str(err)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    else:
        return web.json_response({'name': name, 'id': str(schedule.schedule_id)})


def load_c_plugin(plugin: str, service_type: str) -> Dict:
    try:
        plugin_info = apiutils.get_plugin_info(plugin, dir=service_type)
        if plugin_info['type'] != service_type:
            msg = "Plugin of {} type is not supported".format(plugin_info['type'])
            raise TypeError(msg)
        plugin_config = plugin_info['config']
    except Exception:
        # Now looking for hybrid plugins if exists
        try:
            plugin_info = common.load_and_fetch_c_hybrid_plugin_info(plugin, True)
            if plugin_info:
                plugin_config = plugin_info['config']
        except Exception:
            # This case if C-plugin is not found either in hybrid path. Hence treated as bad plugin
            _logger.error("No {} plugin found".format(plugin))
            plugin_config = {}
    return plugin_config


async def check_scheduled_processes(storage, process_name, script):
    payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', process_name]).AND_WHERE(['script', '=', script]).payload()
    result = await storage.query_tbl_with_payload('scheduled_processes', payload)
    return result['count']


async def check_schedules(storage, schedule_name):
    payload = PayloadBuilder().SELECT("schedule_name").WHERE(['schedule_name', '=', schedule_name]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result['count']


async def get_schedule(storage, schedule_name):
    payload = PayloadBuilder().SELECT(["id", "enabled"]).WHERE(['schedule_name', '=', schedule_name]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result


async def check_schedule_entry(storage):
    payload = PayloadBuilder().SELECT("process_name").payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result


async def get_available(request: web.Request) -> web.Response:
    """ get list of a available services via package management i.e apt or yum

        :Example:
            curl -X GET http://localhost:8081/fledge/service/available
    """
    try:
        services, log_path = await common.fetch_available_packages("service")
    except PackageError as e:
        msg = "Fetch available service package request failed"
        raise web.HTTPBadRequest(body=json.dumps({"message": msg, "link": str(e)}), reason=msg)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))

    return web.json_response({"services": services, "link": log_path})


async def get_installed(request: web.Request) -> web.Response:
    """ get list of a installed services

        :Example:
            curl -X GET http://localhost:8081/fledge/service/installed
    """
    services = get_service_installed()
    return web.json_response({"services": services})


async def update_service(request: web.Request) -> web.Response:
    """ update service

    :Example:
        curl -sX PUT http://localhost:8081/fledge/service/notification/notification/update
    """
    _type = request.match_info.get('type', None)
    name = request.match_info.get('name', None)
    try:
        _type = _type.lower()
        # TODO: 5141 - once done we need to fix for dispatcher type as well
        if _type != 'notification':
            raise ValueError("Invalid service type. Must be 'notification'")

        # Check requested service name is installed or not
        installed_services = get_service_installed()
        if name not in installed_services:
            raise KeyError("{} service is not installed yet. Hence update is not possible.".format(name))

        # Check Pre-conditions from Packages table
        # if status is -1 (Already in progress) then return as rejected request
        action = 'update'
        package_name = "fledge-service-{}".format(name)
        storage_client = connect.get_storage_async()
        select_payload = PayloadBuilder().SELECT("status").WHERE(['action', '=', action]).AND_WHERE(
            ['name', '=', package_name]).payload()
        result = await storage_client.query_tbl_with_payload('packages', select_payload)
        response = result['rows']
        if response:
            exit_code = response[0]['status']
            if exit_code == -1:
                msg = "{} package {} already in progress".format(package_name, action)
                return web.HTTPTooManyRequests(reason=msg, body=json.dumps({"message": msg}))
            # Remove old entry from table for other cases
            delete_payload = PayloadBuilder().WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', package_name]).payload()
            await storage_client.delete_from_tbl("packages", delete_payload)

        # process_name always ends with "_c" suffix
        payload = PayloadBuilder().SELECT("id", "enabled", "schedule_name").WHERE(['process_name', '=', '{}_c'.format(
            _type)]).payload()
        result = await storage_client.query_tbl_with_payload('schedules', payload)
        sch_info = result['rows']
        sch_list = []
        if sch_info and sch_info[0]['enabled'] == 't':
            status, reason = await server.Server.scheduler.disable_schedule(uuid.UUID(sch_info[0]['id']))
            if status:
                _logger.warning("Schedule is disabled for {}, as {} service of type {} is being updated...".format(
                    sch_info[0]['schedule_name'], name, _type))
                sch_list.append(sch_info[0]['id'])

        # Insert record into Packages table
        uid = str(uuid.uuid4())
        insert_payload = PayloadBuilder().INSERT(id=uid, name=package_name, action=action, status=-1,
                                                 log_file_uri="").payload()
        result = await storage_client.insert_into_tbl("packages", insert_payload)
        if result['response'] == "inserted" and result['rows_affected'] == 1:
            pn = "{}-{}".format(action, name)
            p = multiprocessing.Process(name=pn, target=do_update, args=(server.Server.is_rest_server_http_enabled,
                                                                         server.Server._host,
                                                                         server.Server.core_management_port,
                                                                         storage_client, package_name, uid, sch_list))
            p.daemon = True
            p.start()
            msg = "{} {} started".format(package_name, action)
            status_link = "fledge/package/{}/status?id={}".format(action, uid)
            result_payload = {"message": msg, "id": uid, "statusLink": status_link}
        else:
            raise StorageServerError
    except KeyError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))
    else:
        return web.json_response(result_payload)


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
                _logger.error("Bad request error code: %d, reason: %s when PUT schedule", status_code, resp.reason)
            if status_code in range(500, 600):
                _logger.error("Server error code: %d, reason: %s when PUT schedule", status_code, resp.reason)
            response = json.loads(result)
            _logger.debug("PUT Schedule response: %s", response)


def do_update(http_enabled: bool, host: str, port: int, storage: connect, pkg_name: str, uid: str,
              schedules: list) -> None:
    _logger.info("{} service update started...".format(pkg_name))
    _platform = platform.platform()
    stdout_file_path = common.create_log_file("update", pkg_name)
    pkg_mgt = 'apt'
    cmd = "sudo {} -y update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    protocol = "HTTP" if http_enabled else "HTTPS"
    if 'centos' in _platform or 'redhat' in _platform:
        pkg_mgt = 'yum'
        cmd = "sudo {} check-update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    ret_code = os.system(cmd)
    # sudo apt/yum -y install only happens when update is without any error
    if ret_code == 0:
        cmd = "sudo {} -y install {} >> {} 2>&1".format(pkg_mgt, pkg_name, stdout_file_path)
        ret_code = os.system(cmd)

    # relative log file link
    link = "log/" + stdout_file_path.split("/")[-1]

    # Update record in Packages table
    payload = PayloadBuilder().SET(status=ret_code, log_file_uri=link).WHERE(['id', '=', uid]).payload()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(storage.update_tbl("packages", payload))

    if ret_code != 0:
        _logger.error("{} service update failed. Logs available at {}".format(pkg_name, link))
    else:
        # Audit info
        audit = AuditLogger(storage)
        audit_detail = {'packageName': pkg_name}
        loop.run_until_complete(audit.information('PKGUP', audit_detail))
        _logger.info('{} service updated successfully. Logs available at {}'.format(pkg_name, link))

    # Restart the service which was disabled before service update
    for sch in schedules:
        loop.run_until_complete(_put_schedule(protocol, host, port, uuid.UUID(sch), True))
