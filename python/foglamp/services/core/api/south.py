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


async def _get_tracked_services(storage_client):
    sr_list = list()
    try:
        payload = PayloadBuilder().SELECT("service").payload()
        result = await storage_client.query_tbl_with_payload('asset_tracker', payload)

        services_with_assets = result['rows']
        try:
            southbound_services = ServiceRegistry.get(s_type="Southbound")
        except DoesNotExist:
            southbound_services = []

        def get_svc(name):
            return next((ss for ss in southbound_services if ss._name == name), None)

        for ss in southbound_services:
            sr_list.append(
                {
                    'name': ss._name,
                    'address': ss._address,
                    'management_port': ss._management_port,
                    'service_port': ss._port,
                    'protocol': ss._protocol,
                    'status': ServiceRecord.Status(int(ss._status)).name.lower(),
                    'assets': await _get_tracked_assets_and_readings(storage_client, ss._name)
                })
        for swa in services_with_assets:
            south_svc = get_svc(swa["service"])
            if not south_svc:
                sr_list.append(
                    {
                        'name': swa["service"],
                        'address': '',
                        'management_port': '',
                        'service_port': '',
                        'protocol': '',
                        'status': '',
                        'assets': await _get_tracked_assets_and_readings(storage_client, swa["service"])

                    })
    except:
        raise
    else:
        return {'services': sr_list}


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


async def get_south_services(request):
    """
    Args:
        request:

    Returns:
            list of all registered services having type "Southbound"

    :Example:
            curl -X GET http://localhost:8081/foglamp/south
    """
    storage_client = connect.get_storage_async()
    response = await _get_tracked_services(storage_client)
    return web.json_response(response)
