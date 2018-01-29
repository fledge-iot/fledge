# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Utilities"""

import aiohttp
import asyncio
from foglamp.common import logger

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=20)


async def ping_service(service):
    _MAX_ATTEMPTS = 15
    """Number of max attempts for finding a heartbeat of service"""
    attempt_count = 1
    """Number of current attempt to ping url"""

    url_ping = "{}://{}:{}/foglamp/service/ping".format(service._protocol,
                                                        service._address,
                                                        service._management_port)
    async with aiohttp.ClientSession() as session:
        while attempt_count < _MAX_ATTEMPTS + 1:
            try:
                async with session.get(url_ping) as resp:
                    res = await resp.json()
                    if res["uptime"] is not None:
                        break
            except:
                attempt_count += 1
                await asyncio.sleep(1.5)
        if attempt_count <= _MAX_ATTEMPTS:
            _logger.info('Ping received for Service %s id %s at url %s', service._name, service._id, url_ping)
            return True
    _logger.error('Ping not received for Service %s id %s at url %s attempt_count %s', service._name, service._id,
                       url_ping, attempt_count)
    return False


async def shutdown_service(service):
    _ping_timeout = 15  # type: int
    """Timeout for a response from any given micro-service"""
    try:
        _logger.info("Shutting down the %s service %s ...", service._type, service._name)
        url_shutdown = "{}://{}:{}/foglamp/service/shutdown".format(service._protocol, service._address,
                                                                    service._management_port)
        async with aiohttp.ClientSession() as session:
            async with session.post(url_shutdown) as resp:
                status_code = resp.status
                assert 200 == resp.status
    except (Exception, AssertionError) as ex:
        _logger.exception('Error in Service shutdown %s, %s', service._name, str(ex))
        return False
    else:
        _logger.info('Service %s, id %s at url %s successfully shutdown', service._name, service._id, url_shutdown)
        return True
