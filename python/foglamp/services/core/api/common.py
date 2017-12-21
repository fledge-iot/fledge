# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
from aiohttp import web

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/ping                                             |
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
