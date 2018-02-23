# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import time
from foglamp.common import logger
from aiohttp import web
from foglamp.services.core import server

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()

_logger = logger.setup(__name__, level=20)

_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/ping                                             |
    | PUT             | /foglamp/shutdown                                         |
    -------------------------------------------------------------------------------
"""


async def ping(request):
    """
    Args:
        request:

    Returns:
            basic health information json payload
            {'uptime': 32892} Time in seconds since FogLAMP started

    :Example:
            curl -X GET http://localhost:8081/foglamp/ping
    """
    since_started = time.time() - __start_time

    # TODO: FOGL-790 - ping method should return more data
    return web.json_response({'uptime': since_started})


async def shutdown(request):
    """
    Args:
        request:

    Returns:

    :Example:
            curl -X PUT http://localhost:8081/foglamp/shutdown
    """

    try:
        loop = request.loop
        loop.call_later(2, do_shutdown, loop)

        return web.json_response({'message': 'FogLAMP shutdown has been scheduled. '
                                             'Wait for few seconds for process cleanup.'})
    except TimeoutError as err:
        raise web.HTTPInternalServerError(reason=str(err))
    except Exception as ex:
        raise web.HTTPException(reason=str(ex))


def do_shutdown(loop=None):
    _logger.info("Executing controlled shutdown")
    if loop is None:
        loop = asyncio.get_event_loop()
    loop.run_until_complete(server.Server._stop())
    loop.stop()
