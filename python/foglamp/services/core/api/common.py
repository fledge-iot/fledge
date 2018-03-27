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
        cfg_mgr = ConfigurationManager(connect.get_storage())
        category_item = await cfg_mgr.get_category_item('rest_api', 'allowPing')
        allow_ping = True if category_item['value'].lower() == 'true' else False
        if request.is_auth_optional is False and allow_ping is False:
            raise web.HTTPForbidden

    def get_stats(k):
        v = [a['value'] for a in stats if a['key'] == k]
        return int(v[0])

    since_started = time.time() - __start_time

    stats_request = request.clone(rel_url='foglamp/statistics')
    stats_res = await get_statistics(stats_request)
    stats = json.loads(stats_res.body.decode())

    data_read = get_stats('READINGS')
    data_sent_1 = get_stats('SENT_1')
    data_sent_2 = get_stats('SENT_2')
    data_sent_3 = get_stats('SENT_3')
    data_sent_4 = get_stats('SENT_4')
    data_purged = get_stats('PURGED')

    return web.json_response({'uptime': since_started,
                              'dataRead': data_read,
                              'dataSent': data_sent_1 + data_sent_2 + data_sent_3 + data_sent_4,
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
