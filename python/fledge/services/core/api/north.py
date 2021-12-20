# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from functools import lru_cache
from aiohttp import web

from fledge.services.core import server
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.services.core import connect
from fledge.services.core.scheduler.entities import Task
from fledge.common.service_record import ServiceRecord
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry.exceptions import DoesNotExist
from fledge.common import logger

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                 | /fledge/north                                         |
    -------------------------------------------------------------------------------
"""
_logger = logger.setup(__name__)


async def _get_sent_stats(storage_client):
    stats = []
    try:
        payload = PayloadBuilder().SELECT("key", "value").payload()
        result = await storage_client.query_tbl_with_payload('statistics', payload)
        if int(result['count']):
            stats = result['rows']
    except:
        raise
    else:
        return stats


async def _get_tasks_status():
    payload = PayloadBuilder().SELECT("id", "schedule_name", "process_name", "state", "start_time",
                                      "end_time", "reason", "pid", "exit_code")\
        .WHERE(["process_name", "=", "north"])\
        .OR_WHERE(["process_name", "=", "north_c"])\
        .ALIAS("return", ("start_time", 'start_time'), ("end_time", 'end_time'))\
        .FORMAT("return", ("start_time", "YYYY-MM-DD HH24:MI:SS.MS"), ("end_time", "YYYY-MM-DD HH24:MI:SS.MS"))\
        .ORDER_BY(["schedule_name", "asc"], ["start_time", "desc"])

    tasks = {}
    try:
        _storage = connect.get_storage_async()
        results = await _storage.query_tbl_with_payload('tasks', payload.payload())
        previous_schedule = None
        for row in results['rows']:
            if not row['schedule_name'].strip():
                continue
            if previous_schedule != row['schedule_name']:
                tasks.update({row['schedule_name']: row})
                previous_schedule = row['schedule_name']
    except Exception as ex:
        raise ValueError(str(ex))
    return tasks


async def _get_north_schedules(cf_mgr):
    try:
        north_categories = await cf_mgr.get_category_child("North")
        north_schedules = [nc["key"] for nc in north_categories]
    except ValueError:
        return []

    schedules = []
    north_sch_dict = {}
    schedule_list = await server.Server.scheduler.get_schedules()
    latest_tasks = await _get_tasks_status()
    try:
        services_from_registry = ServiceRegistry.get(s_type="Northbound")
    except DoesNotExist:
        services_from_registry = []
    for sch in schedule_list:
        if sch.name in north_schedules:
            if sch.process_name != "north_C" and sch.schedule_type != 1:
                task = latest_tasks.get(sch.name, None)
                north_sch_dict = {
                    'id': str(sch.schedule_id),
                    'name': sch.name,
                    'processName': sch.process_name,
                    'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
                    'day': sch.day,
                    'enabled': sch.enabled,
                    'exclusive': sch.exclusive,
                    'execution': 'task',
                    'taskStatus': None if task is None else {
                        'state': [t.name.capitalize() for t in list(Task.State)][int(task['state']) - 1],
                        'startTime': str(task['start_time']),
                        'endTime': str(task['end_time']),
                        'exitCode': task['exit_code'],
                        'reason': task['reason']
                    }
                }
            else:
                for s_record in services_from_registry:
                    if s_record._name == sch.name:
                        north_sch_dict = {
                            'id': str(sch.schedule_id),
                            'name': sch.name,
                            'processName': sch.process_name,
                            'enabled': sch.enabled,
                            'execution': 'service',
                            'address': s_record._address,
                            'managementPort': s_record._management_port,
                            'servicePort': s_record._port,
                            'protocol': s_record._protocol,
                            'status': ServiceRecord.Status(int(s_record._status)).name.lower()
                        }
                # north-C service case, If not in service registry
                if sch.enabled is False and sch.name not in [s_record._name for s_record in services_from_registry]:
                    north_sch_dict = {
                        'id': str(sch.schedule_id),
                        'name': sch.name,
                        'processName': sch.process_name,
                        'enabled': sch.enabled,
                        'execution': 'service',
                        'address': '',
                        'managementPort': '',
                        'servicePort': '',
                        'protocol': '',
                        'status': ''
                    }
            if north_sch_dict:
                schedules.append(north_sch_dict)

    return list({v['name']: v for v in schedules}.values())


@lru_cache(maxsize=1024)
def _get_installed_plugins():
    return PluginDiscovery.get_plugins_installed("north", False)


async def get_north_schedules(request):
    """
    Args:
        request:

    Returns:
            list of all north instances with statistics

    :Example:
            curl -X GET http://localhost:8081/fledge/north
    """
    try:
        if 'cached' in request.query and request.query['cached'].lower() == 'false':
            _get_installed_plugins.cache_clear()
        storage_client = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage_client)
        north_schedules = await _get_north_schedules(cf_mgr)
        stats = await _get_sent_stats(storage_client)
        installed_plugins = _get_installed_plugins()
        for sch in north_schedules:
            stat = next((s for s in stats if s["key"] == sch["name"]), None)
            sch["sent"] = stat["value"] if stat else -1
            plugin = await cf_mgr.get_category_item(sch["name"], 'plugin')
            plugin_name = plugin['value'] if plugin is not None else ''
            plugin_version = ''
            for p in installed_plugins:
                if p["name"] == plugin_name:
                    plugin_version = p["version"]
                    break
            sch["plugin"] = {"name": plugin_name, "version": plugin_version}

    except (KeyError, ValueError) as e:  # Handles KeyError of _get_sent_stats
        msg = str(e)
        return web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        return web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(north_schedules)
