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


__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                 | /foglamp/south                                        |
    -------------------------------------------------------------------------------
"""


async def _get_tracked_assets_and_readings(storage_client, svc_name):
    asset_json = []
    payload = PayloadBuilder().SELECT("asset").WHERE(['service', '=', svc_name]).payload()
    try:
        result = await storage_client.query_tbl_with_payload('asset_tracker', payload)
        asset_records = result['rows']

        _readings_client = connect.get_readings_async()
        for r in asset_records:
            payload = PayloadBuilder().AGGREGATE(["count", "*"]).ALIAS("aggregate", ("*", "count", "count")) \
                .GROUP_BY("asset_code").WHERE(['asset_code', '=', r["asset"]]).payload()
            results = await _readings_client.query(payload)
            if int(results['count']):
                r = results['rows'][0]
                asset_json.append({"count": r['count'], "asset": r['asset_code']})
    except:
        raise
    else:
        return asset_json


async def _get_southbound_service_records():
    storage_client = connect.get_storage_async()
    sr_list = list()
    try:
        svc_records = ServiceRegistry.get(s_type="Southbound")
    except DoesNotExist:
        pass
    else:
        for service_record in svc_records:
            sr_list.append(
                {
                    'name': service_record._name,
                    'address': service_record._address,
                    'management_port': service_record._management_port,
                    'service_port': service_record._port,
                    'protocol': service_record._protocol,
                    'status': ServiceRecord.Status(int(service_record._status)).name.lower(),
                    'assets': await _get_tracked_assets_and_readings(storage_client, service_record._name)
                })

    recs = {'services': sr_list}
    return recs


async def get_south_services(request):
    """
    Args:
        request:

    Returns:
            list of all registered services having type "Southbound"

    :Example:
            curl -X GET http://localhost:8081/foglamp/south
    """
    response = await _get_southbound_service_records()
    return web.json_response(response)
