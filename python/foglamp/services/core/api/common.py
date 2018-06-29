# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import time
import json
from foglamp.common import logger
from aiohttp import web
from foglamp.services.core import server
from foglamp.services.core.api.statistics import get_statistics
from foglamp.services.core import connect
from foglamp.common.configuration_manager import ConfigurationManager

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

    :Example:
           curl -X GET http://localhost:8081/foglamp/ping
    """

    try:
        auth_token = request.token
    except AttributeError:
        cfg_mgr = ConfigurationManager(connect.get_storage_async())
        category_item = await cfg_mgr.get_category_item('rest_api', 'allowPing')
        allow_ping = True if category_item['value'].lower() == 'true' else False
        if request.is_auth_optional is False and allow_ping is False:
            _logger.warning("Permission denied for Ping when Auth is mandatory.")
            raise web.HTTPForbidden

    since_started = time.time() - __start_time

    stats_request = request.clone(rel_url='foglamp/statistics')
    stats_res = await get_statistics(stats_request)
    stats = json.loads(stats_res.body.decode())

    def get_stats(k):
        v = [s['value'] for s in stats if s['key'] == k]
        return int(v[0])

    def get_sent_stats():
        return sum([int(s['value']) for s in stats if s['key'].startswith('SENT_')])

    data_read = get_stats('READINGS')
    data_sent = get_sent_stats()
    data_purged = get_stats('PURGED')

    return web.json_response({'uptime': since_started,
                              'dataRead': data_read,
                              'dataSent': data_sent,
                              'dataPurged': data_purged,
                              'authenticationOptional': request.is_auth_optional
                              })


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
        loop.call_later(2, do_shutdown, request)
        return web.json_response({'message': 'FogLAMP shutdown has been scheduled. '
                                             'Wait for few seconds for process cleanup.'})
    except TimeoutError as err:
        raise web.HTTPInternalServerError(reason=str(err))
    except Exception as ex:
        raise web.HTTPException(reason=str(ex))


def do_shutdown(request):
    _logger.info("Executing controlled shutdown")
    try:
        loop = request.loop
        asyncio.ensure_future(server.Server.shutdown(request), loop=loop)
    except RuntimeError as e:
        _logger.exception("Error while stopping FogLAMP server: {}".format(str(e)))
        raise
