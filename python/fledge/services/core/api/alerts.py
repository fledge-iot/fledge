# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from aiohttp import web

from fledge.common.logger import FLCoreLogger
from fledge.services.core import server

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ----------------------------------------------------------------
    | GET    DELETE        | /fledge/alert                         |
    | DELETE               | /fledge/alert/{key}                   |
    ----------------------------------------------------------------
"""
_LOGGER = FLCoreLogger().get_logger(__name__)

def setup(app):
    app.router.add_route('GET', '/fledge/alert', get_all)
    app.router.add_route('DELETE', '/fledge/alert', delete)
    app.router.add_route('DELETE', '/fledge/alert/{key}', delete)



async def get_all(request: web.Request) -> web.Response:
    """ GET list of alerts

    :Example:
        curl -sX GET http://localhost:8081/fledge/alert
    """
    try:
        alerts = await server.Server._alert_manager.get_all()
    except Exception as ex:
        msg = str(ex)
        _LOGGER.error(ex, "Failed to get alerts.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"alerts": alerts})

async def delete(request: web.Request) -> web.Response:
    """ DELETE all alerts

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/alert
        curl -sX DELETE http://localhost:8081/fledge/alert/{key}
    """
    key = request.match_info.get('key', None)
    try:
        if key:
            response = await server.Server._alert_manager.delete(key=key)
        else:
            response = await server.Server._alert_manager.delete()
    except KeyError:
        msg = '{} alert not found.'.format(key)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _LOGGER.error(ex, "Failed to delete alerts.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": response})