# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time

from aiohttp import web
import sys, traceback

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
            curl -X GET http://localhost:8082/foglamp/ping
    """
    since_started = time.time() - __start_time

    return web.json_response({'uptime': since_started})


def handle_scheduler_api_exception(ex, if_trace=0):
    if not isinstance(ex, Exception):
        raise web.HTTPInternalServerError(reason='Exception passed to handler does not belong to Exception class.', text=str(ex))

    _class = ex.__class__.__name__
    _msg = str(ex)
    _module = ex.__module__
    # traceback.print_tb(ex.__traceback__)

    error_500 = ['NotReadyError', 'DuplicateRequestError', 'TaskNotRunningError']
    error_400 = ['TaskNotFoundError', 'ScheduleNotFoundError', 'ValueError']

    if _class in error_400:
        if if_trace:
            raise web.HTTPNotFound(reason={"exception":_class, "traceback":traceback.format_exc()}, text=_msg)
        else:
            raise web.HTTPNotFound(text=_msg)

    if if_trace:
        raise web.HTTPInternalServerError(reason={"exception": _class, "traceback": traceback.format_exc()}, text=_msg)
    else:
        raise web.HTTPInternalServerError(text=_msg)
