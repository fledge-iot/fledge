# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

import asyncio
import os
import logging
import uuid
import platform

from aiohttp import web
from fledge.common import logger
from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import server
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.services.core.api.plugins import common


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | PUT             | /fledge/plugin/{type}/{name}/update                      |
    -------------------------------------------------------------------------------
"""
_logger = logger.setup(__name__, level=logging.INFO)


async def update_plugin(request: web.Request) -> web.Response:
    """ update plugin

    :Example:
        curl -sX PUT http://localhost:8081/fledge/plugins/south/sinusoid/update
        curl -sX PUT http://localhost:8081/fledge/plugins/north/http_north/update
        curl -sX PUT http://localhost:8081/fledge/plugins/filter/metadata/update
    """
    _type = request.match_info.get('type', None)
    name = request.match_info.get('name', None)
    try:
        # TODO: FOGL-3064
        _type = _type.lower()
        if _type not in ['north', 'south', 'filter']:
            raise ValueError("Invalid plugin type. Must be 'north', 'south', 'filter'")

        # Check requested plugin name is installed or not
        installed_plugins = PluginDiscovery.get_plugins_installed(_type, False)
        installed_plugin_name = [p_name["name"] for p_name in installed_plugins]
        if name not in installed_plugin_name:
            raise KeyError("{} plugin is not yet installed. So update is not possible.".format(name))

        # Tracked plugins from asset tracker
        tracked_plugins = await _get_plugin_and_sch_name_from_asset_tracker(_type)
        sch_list = []
        filters_used_by = []
        if _type == 'filter':
            # In case of filter, for asset_tracker table we are inserting filter category_name in plugin column
            # instead of filter plugin name by Design
            # Hence below query is required to get actual plugin name from filters table
            storage_client = connect.get_storage_async()
            payload = PayloadBuilder().SELECT("name").WHERE(['plugin', '=', name]).payload()
            result = await storage_client.query_tbl_with_payload('filters', payload)
            filters_used_by = [r['name'] for r in result['rows']]
        for p in tracked_plugins:
            if (name == p['plugin'] and not _type == 'filter') or (p['plugin'] in filters_used_by and _type == 'filter'):
                sch_info = await _get_sch_id_and_enabled_by_name(p['service'])
                if sch_info[0]['enabled'] == 't':
                    status, reason = await server.Server.scheduler.disable_schedule(uuid.UUID(sch_info[0]['id']))
                    if status:
                        _logger.warning("{} {} instance is disabled as {} plugin is updating..".format(
                            p['service'], _type, name))
                        sch_list.append(sch_info[0]['id'])

        # Plugin update is running as a background task
        loop = request.loop
        request._type = _type
        request._name = name
        request._sch_list = sch_list
        loop.call_later(1, do_update, request)
    except KeyError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))

    return web.json_response({"message": "{} plugin update in process. Wait for few minutes to complete.".format(name)})


async def _get_plugin_and_sch_name_from_asset_tracker(_type: str) -> list:
    if _type == "south":
        event_name = "Ingest"
    elif _type == 'filter':
        event_name = "Filter"
    else:
        event_name = "Egress"
    storage_client = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("plugin", "service").WHERE(['event', '=', event_name]).payload()
    result = await storage_client.query_tbl_with_payload('asset_tracker', payload)
    return result['rows']


async def _get_sch_id_and_enabled_by_name(name) -> list:
    storage_client = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("id", "enabled").WHERE(['schedule_name', '=', name]).payload()
    result = await storage_client.query_tbl_with_payload('schedules', payload)
    return result['rows']


def update_repo_sources_and_plugin(_type: str, name: str) -> tuple:
    # Below check is needed for python plugins
    # For Example: installed_plugin_dir=wind_turbine; package_name=wind-turbine
    if "_" in name:
        name = name.replace("_", "-")

    # For endpoint curl -X GET http://localhost:8081/fledge/plugins/available we used
    # sudo apt list command internal so package name always returns in lowercase,
    # irrespective of package name defined in the configured repo.
    name = "fledge-{}-{}".format(_type, name.lower())
    _platform = platform.platform()
    stdout_file_path = common.create_log_file(action="update", plugin_name=name)
    pkg_mgt = 'apt'
    cmd = "sudo {} -y update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    if 'centos' in _platform or 'redhat' in _platform:
        pkg_mgt = 'yum'
        cmd = "sudo {} check-update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    ret_code = os.system(cmd)
    # sudo apt/yum -y install only happens when update is without any error
    if ret_code == 0:
        cmd = "sudo {} -y install {} >> {} 2>&1".format(pkg_mgt, name, stdout_file_path)
        ret_code = os.system(cmd)

    # relative log file link
    link = "log/" + stdout_file_path.split("/")[-1]
    return ret_code, link


def do_update(request):
    _logger.info("{} plugin update starts...".format(request._name))
    code, link = update_repo_sources_and_plugin(request._type, request._name)
    if code != 0:
        _logger.error("{} plugin update failed. Logs available at {}".format(request._name, link))
    else:
        _logger.info("{} plugin update completed. Logs available at {}".format(request._name, link))

    # Restart the services which were disabled before plugin update
    for s in request._sch_list:
        asyncio.ensure_future(server.Server.scheduler.enable_schedule(uuid.UUID(s)))
