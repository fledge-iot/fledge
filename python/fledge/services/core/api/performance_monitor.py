# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from aiohttp import web

from fledge.common.logger import FLCoreLogger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2023, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ----------------------------------------------------------------
    | GET  DELETE          | /fledge/monitors                      |
    | GET  DELETE          | /fledge/monitors/{service}            |
    | GET  DELETE          | /fledge/monitors/{service}/{counter}  |
    ----------------------------------------------------------------
"""
_LOGGER = FLCoreLogger().get_logger(__name__)

def setup(app):
    app.router.add_route('GET', '/fledge/monitors', get_all)
    app.router.add_route('GET', '/fledge/monitors/{service}', get_by_service_name)
    app.router.add_route('GET', '/fledge/monitors/{service}/{counter}', get_by_service_and_counter_name)
    app.router.add_route('DELETE', '/fledge/monitors', purge_all)
    app.router.add_route('DELETE', '/fledge/monitors/{service}', purge_by_service)
    app.router.add_route('DELETE', '/fledge/monitors/{service}/{counter}', purge_by_service_and_counter)

async def get_all(request: web.Request) -> web.Response:
    """ GET list of performance monitors

    :Example:
        curl -sX GET http://localhost:8081/fledge/monitors
    """
    return web.json_response({})


async def get_by_service_name(request: web.Request) -> web.Response:
    """ GET performance monitors for the given service

    :Example:
        curl -sX GET http://localhost:8081/fledge/monitors/<SVC_NAME>
    """
    return web.json_response({})

async def get_by_service_and_counter_name(request: web.Request) -> web.Response:
    """ GET values for the single counter for the single service

    :Example:
        curl -sX GET http://localhost:8081/fledge/monitors/<SVC_NAME>/<COUNTER_NAME>
    """
    return web.json_response({})


async def purge_all(request: web.Request) -> web.Response:
    """ DELETE all performance monitors

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/monitors
    """
    return web.json_response({})

async def purge_by_service(request: web.Request) -> web.Response:
    """ DELETE performance monitors for the given service

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/monitors/<SVC_NAME>
    """
    return web.json_response({})

async def purge_by_service_and_counter(request: web.Request) -> web.Response:
    """ DELETE performance monitors for the single counter for the single service

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/monitors/<SVC_NAME>/<COUNTER_NAME>
    """
    return web.json_response({})
