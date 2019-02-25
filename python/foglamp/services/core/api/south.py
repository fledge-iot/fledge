# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.common.service_record import ServiceRecord
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry.exceptions import DoesNotExist
from foglamp.services.core import connect
from foglamp.common.configuration_manager import ConfigurationManager


__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                 | /foglamp/south                                        |
    -------------------------------------------------------------------------------
"""


async def _get_schedule_status(storage_client, svc_name):
    payload = PayloadBuilder().SELECT("enabled").WHERE(['schedule_name', '=', svc_name]).payload()
    result = await storage_client.query_tbl_with_payload('schedules', payload)
    return True if result['rows'][0]['enabled'] == 't' else False


async def _services_with_assets(storage_client, south_services):
    sr_list = list()
    try:
        try:
            services_from_registry = ServiceRegistry.get(s_type="Southbound")
        except DoesNotExist:
            services_from_registry = []

        def is_svc_in_service_registry(name):
            return next((svc for svc in services_from_registry if svc._name == name), None)

        for s_record in services_from_registry:
            sr_list.append(
                {
                    'name': s_record._name,
                    'address': s_record._address,
                    'management_port': s_record._management_port,
                    'service_port': s_record._port,
                    'protocol': s_record._protocol,
                    'status': ServiceRecord.Status(int(s_record._status)).name.lower(),
                    'assets': await _get_tracked_assets_and_readings(storage_client, s_record._name),
                    'schedule_enabled': await _get_schedule_status(storage_client, s_record._name)
                })
        for s_name in south_services:
            south_svc = is_svc_in_service_registry(s_name)
            if not south_svc:
                sr_list.append(
                    {
                        'name': s_name,
                        'address': '',
                        'management_port': '',
                        'service_port': '',
                        'protocol': '',
                        'status': '',
                        'assets': await _get_tracked_assets_and_readings(storage_client, s_name),
                        'schedule_enabled': await _get_schedule_status(storage_client, s_name)
                    })
    except:
        raise
    else:
        return sr_list


async def _get_tracked_assets_and_readings(storage_client, svc_name):
    asset_json = []
    payload = PayloadBuilder().SELECT("asset").WHERE(['service', '=', svc_name]).\
        AND_WHERE(['event', '=', 'Ingest']).payload()
    try:
        result = await storage_client.query_tbl_with_payload('asset_tracker', payload)
        asset_records = result['rows']

        _readings_client = connect.get_readings_async()
        for r in asset_records:
            payload = PayloadBuilder().SELECT("value").WHERE(["key", "=", r["asset"].upper()]).payload()
            results = await storage_client.query_tbl_with_payload("statistics", payload)
            if int(results['count']):
                asset_result = results['rows'][0]
                asset_json.append({"count": asset_result['value'], "asset": r["asset"]})
    except:
        raise
    else:
        return asset_json


async def get_south_services(request):
    """
    Args:
        request:

    Returns:
            list of all south services with tracked assets and readings count

    :Example:
            curl -X GET http://localhost:8081/foglamp/south
    """
    storage_client = connect.get_storage_async()
    cf_mgr = ConfigurationManager(storage_client)
    try:
        south_cat = await cf_mgr.get_category_child("South")
        south_categories = [nc["key"] for nc in south_cat]
    except:
        return web.json_response({'services': []})

    response = await _services_with_assets(storage_client, south_categories)
    return web.json_response({'services': response})
