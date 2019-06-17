# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import logging

from aiohttp import web
from foglamp.common.plugin_discovery import PluginDiscovery
from foglamp.services.core.api.plugins import common
from foglamp.common import logger

__author__ = "Amarendra K Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/plugins/installed                                |
    | GET             | /foglamp/plugins/available                                |
    -------------------------------------------------------------------------------
"""
_logger = logger.setup(__name__, level=logging.INFO)


async def get_plugins_installed(request):
    """ get list of installed plugins

    :Example:
        curl -X GET http://localhost:8081/foglamp/plugins/installed
        curl -X GET http://localhost:8081/foglamp/plugins/installed?config=true
        curl -X GET http://localhost:8081/foglamp/plugins/installed?type=north|south|filter|notificationDelivery|notificationRule
        curl -X 'GET http://localhost:8081/foglamp/plugins/installed?type=north&config=true'
    """

    plugin_type = None
    is_config = False
    if 'type' in request.query and request.query['type'] != '':
        plugin_type = request.query['type'].lower() if request.query['type'] not in ['notificationDelivery', 'notificationRule'] else request.query['type']

    if plugin_type is not None and plugin_type not in ['north', 'south', 'filter', 'notificationDelivery', 'notificationRule']:
        raise web.HTTPBadRequest(reason="Invalid plugin type. Must be 'north' or 'south' or 'filter' or 'notificationDelivery' or 'notificationRule'.")

    if 'config' in request.query:
        config = request.query['config']
        if config not in ['true', 'false', True, False]:
            raise web.HTTPBadRequest(reason='Only "true", "false", true, false'
                                                ' are allowed for value of config.')
        is_config = True if ((type(config) is str and config.lower() in ['true']) or (
            (type(config) is bool and config is True))) else False

    plugins_list = PluginDiscovery.get_plugins_installed(plugin_type, is_config)

    return web.json_response({"plugins": plugins_list})


async def get_plugins_available(request: web.Request) -> web.Response:
    """ get list of a available plugins via package management i.e apt or yum

        :Example:
            curl -X GET http://localhost:8081/foglamp/plugins/available
            curl -X GET http://localhost:8081/foglamp/plugins/available?type=north | south | filter | notify | rule
    """
    try:
        package_type = ""
        if 'type' in request.query and request.query['type'] != '':
            package_type = request.query['type'].lower()

        if package_type and package_type not in ['north', 'south', 'filter', 'notify', 'rule']:
            raise ValueError("Invalid package type. Must be 'north' or 'south' or 'filter' or 'notify' or 'rule'.")
        plugins = common.fetch_available_plugins(package_type)
        # foglamp-gui, foglamp-quickstart and foglamp-service-* packages are excluded when no type is given
        if not package_type:
            plugins = [e for e in plugins if not str(e).startswith('foglamp-service-') and e not in ('foglamp-quickstart', 'foglamp-gui')]
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=ex)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)

    return web.json_response({"plugins": plugins})
