# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
from aiohttp import web

__author__ = "Amarendra K. Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()


async def ping(request):
    """
    :return: basic health information json payload
    {'uptime': 32892} Time in seconds since FogLAMP started
    """

    since_started = time.time() - __start_time

    return web.json_response({'uptime': since_started})
