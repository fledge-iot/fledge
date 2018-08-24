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


async def _services_with_assets(storage_client, south_services):
    sr_list = list()
    try:
        try:
            services_from_registry = ServiceRegistry.get(s_type="Southbound")
        except DoesNotExist:
            services_from_registry = []

        def get_svc(name):
            return next((svc for svc in services_from_registry if svc._name == name), None)

        for ss in services_from_registry:
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
        for _s in south_services:
            south_svc = get_svc(_s)
            if not south_svc:
                sr_list.append(
                    {
                        'name': _s,
                        'address': '',
                        'management_port': '',
                        'service_port': '',
                        'protocol': '',
                        'status': '',
                        'assets': await _get_tracked_assets_and_readings(storage_client, _s)

                    })
    except:
        raise
    else:
        return sr_list


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
            list of all south services with tracked assets and readings count

    :Example:
            curl -X GET http://localhost:8081/foglamp/south
    """
    storage_client = connect.get_storage_async()
    cf_mgr = ConfigurationManager(storage_client)
    try:
        south_cat = await cf_mgr.get_category_child("South")
        south_categories = [nc["key"] for nc in south_cat]
    except ValueError:
        return web.json_response({'services': []})

    response = await _services_with_assets(storage_client, south_categories)
    return web.json_response({'services': response})
