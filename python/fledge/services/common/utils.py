# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Common Utilities"""

import aiohttp
import asyncio
from fledge.common import logger

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=20)

_MAX_ATTEMPTS = 15
"""Number of max attempts for finding a heartbeat of service"""


async def ping_service(service, loop=None):
    attempt_count = 1
    """Number of current attempt to ping url"""

    loop = asyncio.get_event_loop() if loop is None else loop
    url_ping = "{}://{}:{}/fledge/service/ping".format(service._protocol,
                                                        service._address,
                                                        service._management_port)
    async with aiohttp.ClientSession(loop=loop) as session:
        while attempt_count < _MAX_ATTEMPTS + 1:
            try:
                async with session.get(url_ping) as resp:
                    res = await resp.json()
                    if res["uptime"] is not None:
                        break
            except Exception as ex:
                attempt_count += 1
                await asyncio.sleep(1.5, loop=loop)
        if attempt_count <= _MAX_ATTEMPTS:
            _logger.info('Ping received for Service %s id %s at url %s', service._name, service._id, url_ping)
            return True
    _logger.error('Ping not received for Service %s id %s at url %s attempt_count %s', service._name, service._id,
                       url_ping, attempt_count)
    return False


async def shutdown_service(service, loop=None):
    loop = asyncio.get_event_loop() if loop is None else loop

    try:
        _logger.info("Shutting down the %s service %s ...", service._type, service._name)
        url_shutdown = "{}://{}:{}/fledge/service/shutdown".format(service._protocol, service._address,
                                                                    service._management_port)
        async with aiohttp.ClientSession(loop=loop) as session:
            async with session.post(url_shutdown) as resp:
                status_code = resp.status
                text = await resp.text()
                if not status_code == 200:
                    raise Exception(message=text)
    except Exception as ex:
        _logger.exception('Error in Service shutdown %s, %s', service._name, str(ex))
        return False
    else:
        _logger.info('Service %s, id %s at url %s successfully shutdown', service._name, service._id, url_shutdown)
        return True
