# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
from aiohttp import web
from foglamp import server

__author__ = "Amarendra K. Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

async def ping(request):
    """
    :return: basic health information json payload
    {'uptime': 32892} Time in seconds since FogLAMP started
    """

    # Since foglamp can be started in foreground or as a daemon,
    # need to check for both foglampd and foglamp
    process_info = server.find_process_info('foglampd') or server.find_process_info('foglamp')

    since_started = 0
    if process_info is not None:
        since_started = time.time() - process_info['start_time']

    return web.json_response({'uptime': since_started})
