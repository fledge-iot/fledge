# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.services.core import server
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.services.core import connect
from foglamp.services.core.scheduler.entities import Task

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                 | /foglamp/north                                        |
    -------------------------------------------------------------------------------
"""


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
    payload = PayloadBuilder().SELECT("id", "schedule_name", "process_name", "state", "start_time", "end_time", "reason", "pid", "exit_code")\
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


async def _get_north_schedules(storage_client):

    cf_mgr = ConfigurationManager(storage_client)
    try:
        north_categories = await cf_mgr.get_category_child("North")
        north_schedules = [nc["key"] for nc in north_categories]
    except ValueError:
        return []

    schedules = []
    schedule_list = await server.Server.scheduler.get_schedules()
    latest_tasks = await _get_tasks_status()
    for sch in schedule_list:
        if sch.name in north_schedules:
            task = latest_tasks.get(sch.name, None)
            schedules.append({
                'id': str(sch.schedule_id),
                'name': sch.name,
                'processName': sch.process_name,
                'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
                'day': sch.day,
                'enabled': sch.enabled,
                'exclusive': sch.exclusive,
                'taskStatus': None if task is None else {
                    'state': [t.name.capitalize() for t in list(Task.State)][int(task['state']) - 1],
                    'startTime': str(task['start_time']),
                    'endTime': str(task['end_time']),
                    'exitCode': task['exit_code'],
                    'reason': task['reason'],
                }
            })

    return schedules


async def get_north_schedules(request):
    """
    Args:
        request:

    Returns:
            list of all north instances with statistics

    :Example:
            curl -X GET http://localhost:8081/foglamp/north
    """
    try:
        storage_client = connect.get_storage_async()
        north_schedules = await _get_north_schedules(storage_client)
        stats = await _get_sent_stats(storage_client)

        for sch in north_schedules:
            stat = next((s for s in stats if s["key"] == sch["name"]), None)
            sch["sent"] = stat["value"] if stat else -1

    except (KeyError, ValueError) as e:  # Handles KeyError of _get_sent_stats
        return web.HTTPInternalServerError(reason=e)
    else:
        return web.json_response(north_schedules)
