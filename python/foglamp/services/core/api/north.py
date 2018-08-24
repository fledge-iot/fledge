# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.services.core import server
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.services.core import connect


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


async def _get_north_schedules(storage_client):

    cf_mgr = ConfigurationManager(storage_client)
    try:
        north_categories = await cf_mgr.get_category_child("North")
        north_schedules = [nc["key"] for nc in north_categories]
    except ValueError:
        return []

    schedules = []
    schedule_list = await server.Server.scheduler.get_schedules()
    for sch in schedule_list:
        if sch.name in north_schedules:
            schedules.append({
                'id': str(sch.schedule_id),
                'name': sch.name,
                'processName': sch.process_name,
                'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
                'day': sch.day,
                'enabled': sch.enabled,
                'exclusive': sch.exclusive
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
            stat = next((s for s in stats if s["key"] == sch["processName"]), None)
            sch["sent"] = stat["value"] if stat else -1

    except (KeyError, ValueError) as e:  # Handles KeyError of _get_sent_stats
        return web.HTTPInternalServerError(reason=e)
    else:
        return web.json_response(north_schedules)
