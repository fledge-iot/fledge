# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import logging
import json

from aiohttp import web
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.services.core.api.plugins import common
from fledge.common import logger
from fledge.services.core.api.plugins.exceptions import *

__author__ = "Amarendra K Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /fledge/plugins/installed                                |
    | GET             | /fledge/plugins/available                                |
    -------------------------------------------------------------------------------
"""
_logger = logger.setup(__name__, level=logging.INFO)


async def get_plugins_installed(request):
    """ get list of installed plugins

    :Example:
        curl -X GET http://localhost:8081/fledge/plugins/installed
        curl -X GET http://localhost:8081/fledge/plugins/installed?config=true
        curl -X GET http://localhost:8081/fledge/plugins/installed?type=north|south|filter|notify|rule
        curl -X 'GET http://localhost:8081/fledge/plugins/installed?type=north&config=true'
    """

    plugin_type = None
    is_config = False
    if 'type' in request.query and request.query['type'] != '':
        plugin_type = request.query['type'].lower()

    if plugin_type is not None and plugin_type not in ['north', 'south', 'filter', 'notify', 'rule']:
        raise web.HTTPBadRequest(reason="Invalid plugin type. Must be 'north' or 'south' or 'filter' or 'notify' "
                                        "or 'rule'.")

    if 'config' in request.query:
        config = request.query['config']
        if config not in ['true', 'false', True, False]:
            raise web.HTTPBadRequest(reason='Only "true", "false", true, false are allowed for value of config.')
        is_config = True if ((type(config) is str and config.lower() in ['true']) or (
            (type(config) is bool and config is True))) else False

    plugins_list = PluginDiscovery.get_plugins_installed(plugin_type, is_config)

    return web.json_response({"plugins": plugins_list})


async def get_plugins_available(request: web.Request) -> web.Response:
    """ get list of a available plugins via package management i.e apt or yum

        :Example:
            curl -X GET http://localhost:8081/fledge/plugins/available
            curl -X GET http://localhost:8081/fledge/plugins/available?type=north | south | filter | notify | rule
    """
    try:
        package_type = ""
        if 'type' in request.query and request.query['type'] != '':
            package_type = request.query['type'].lower()

        if package_type and package_type not in ['north', 'south', 'filter', 'notify', 'rule']:
            raise ValueError("Invalid package type. Must be 'north' or 'south' or 'filter' or 'notify' or 'rule'.")
        plugins, log_path = await common.fetch_available_packages(package_type)
        if not package_type:
            prefix_list = ['fledge-filter-', 'fledge-north-', 'fledge-notify-', 'fledge-rule-', 'fledge-south-']
            plugins = [p for p in plugins if str(p).startswith(tuple(prefix_list))]
    except ValueError as e:
        raise web.HTTPBadRequest(reason=e)
    except PackageError as e:
        msg = "Fetch available plugins package request failed"
        raise web.HTTPBadRequest(body=json.dumps({"message": msg, "link": str(e)}), reason=msg)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)

    return web.json_response({"plugins": plugins, "link": log_path})
