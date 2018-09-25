# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
from foglamp.common.plugin_discovery import PluginDiscovery

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/plugins/installed                                |
    -------------------------------------------------------------------------------
"""


async def get_plugins_installed(request):
    """ get list of installed plugins

    :Example:
        curl -X GET http://localhost:8081/foglamp/plugins/installed
        curl -X GET http://localhost:8081/foglamp/plugins/installed?config=true
        curl -X GET http://localhost:8081/foglamp/plugins/installed?type=north
        curl -X 'GET http://localhost:8081/foglamp/plugins/installed?type=north&config=true'
    """

    plugin_type = None
    is_config = False
    if 'type' in request.query and request.query['type'] != '':
        plugin_type = request.query['type'].lower()

    if plugin_type is not None and plugin_type not in ['north', 'south']:
        raise web.HTTPBadRequest(reason="Invalid plugin type. Must be 'north' or 'south'.")

    if 'config' in request.query:
        config = request.query['config']
        if config not in ['true', 'false', True, False]:
                raise web.HTTPBadRequest(reason='Only "true", "false", true, false'
                                                ' are allowed for value of config.')
        is_config = True if ((type(config) is str and config.lower() in ['true']) or (
            (type(config) is bool and config is True))) else False

    plugins_list = PluginDiscovery.get_plugins_installed(plugin_type, is_config)

    return web.json_response({"plugins": plugins_list})
