# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from functools import lru_cache

from aiohttp import web

from fledge.common.service_record import ServiceRecord
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry.exceptions import DoesNotExist
from fledge.services.core import connect
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.plugin_discovery import PluginDiscovery

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                 | /fledge/south                                         |
    -------------------------------------------------------------------------------
"""


async def _get_schedule_status(storage_client, svc_name):
    payload = PayloadBuilder().SELECT("enabled").WHERE(['schedule_name', '=', svc_name]).payload()
    result = await storage_client.query_tbl_with_payload('schedules', payload)
    return True if result['rows'][0]['enabled'] == 't' else False


@lru_cache(maxsize=1024)
def _get_installed_plugins():
    return PluginDiscovery.get_plugins_installed("south", False)


async def _services_with_assets(storage_client, cf_mgr, south_services):
    sr_list = list()
    try:
        try:
            services_from_registry = ServiceRegistry.get(s_type="Southbound")
        except DoesNotExist:
            services_from_registry = []

        def is_svc_in_service_registry(name):
            return next((svc for svc in services_from_registry if svc._name == name), None)

        installed_plugins = _get_installed_plugins()

        for s_record in services_from_registry:
            plugin, assets = await _get_tracked_plugin_assets_and_readings(storage_client, cf_mgr, s_record._name)
            plugin_version = ''
            for p in installed_plugins:
                if p["name"] == plugin:
                    plugin_version = p["version"]
                    break

            # Service running on another machine have no scheduler entry
            sched_enable = 'unknown'
            try:
                sched_enable = await _get_schedule_status(storage_client, s_record._name)
            except:
                pass
            sr_list.append(
                {
                    'name': s_record._name,
                    'address': s_record._address,
                    'management_port': s_record._management_port,
                    'service_port': s_record._port,
                    'protocol': s_record._protocol,
                    'status': ServiceRecord.Status(int(s_record._status)).name.lower(),
                    'assets': assets,
                    'plugin': {'name': plugin, 'version': plugin_version},
                    'schedule_enabled': sched_enable
                })
        for s_name in south_services:
            south_svc = is_svc_in_service_registry(s_name)
            if not south_svc:
                plugin, assets = await _get_tracked_plugin_assets_and_readings(storage_client, cf_mgr, s_name)
                plugin_version = ''
                for p in installed_plugins:
                    if p["name"] == plugin:
                        plugin_version = p["version"]
                        break
                # Handle schedule status when there is no schedule entry matching a South child category name
                sch_status = 'unknown'
                try:
                    sch_status = await _get_schedule_status(storage_client, s_name)
                except:
                    pass
                sr_list.append(
                    {
                        'name': s_name,
                        'address': '',
                        'management_port': '',
                        'service_port': '',
                        'protocol': '',
                        'status': '',
                        'assets': assets,
                        'plugin': {'name': plugin, 'version': plugin_version},
                        'schedule_enabled': sch_status
                    })
    except:
        raise
    else:
        return sr_list


async def _get_tracked_plugin_assets_and_readings(storage_client, cf_mgr, svc_name):
    asset_json = []
    plugin_value = await cf_mgr.get_category_item(svc_name, 'plugin')
    plugin = plugin_value['value'] if plugin_value is not None else ''
    payload = PayloadBuilder().SELECT(["asset", "plugin"]).WHERE(['service', '=', svc_name]).AND_WHERE(
        ['event', '=', 'Ingest']).AND_WHERE(['plugin', '=', plugin]).payload()
    try:
        result = await storage_client.query_tbl_with_payload('asset_tracker', payload)
        # TODO: FOGL-2549
        # old asset track entry still appears with combination of service name + plugin name + event name if exists
        asset_records = result['rows']
        assets = [ar["asset"].upper()for ar in asset_records]
        if len(assets):
            def map_original_asset_name(asset_stats_key):
                # asset name are being recorded in uppercase as key in statistics table
                for ar in asset_records:
                    if ar["asset"].upper() == asset_stats_key:
                        return ar["asset"]
                return None

            payload = PayloadBuilder().SELECT(["key", "value"]).WHERE(["key", "in", assets]).payload()
            results = await storage_client.query_tbl_with_payload("statistics", payload)
            for _r in results['rows']:
                asset_json.append({"count": _r['value'], "asset": map_original_asset_name(_r['key'])})
    except:
        raise
    else:
        return plugin, asset_json


async def get_south_services(request):
    """
    Args:
        request:

    Returns:
            list of all south services with tracked assets and readings count

    :Example:
            curl -X GET http://localhost:8081/fledge/south
    """
    if 'cached' in request.query and request.query['cached'].lower() == 'false':
        _get_installed_plugins.cache_clear()

    storage_client = connect.get_storage_async()
    cf_mgr = ConfigurationManager(storage_client)
    try:
        south_cat = await cf_mgr.get_category_child("South")
        south_categories = [nc["key"] for nc in south_cat]
    except:
        return web.json_response({'services': []})

    response = await _services_with_assets(storage_client, cf_mgr, south_categories)
    return web.json_response({'services': response})
