# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Monitor module"""

import asyncio
import aiohttp
import logging
import os
import json

from foglamp import logger
from foglamp import configuration_manager
from foglamp.microservice_management.service_registry.instance import Service

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Monitor(object):
    _DEFAULT_SLEEP_INTERVAL = 5
    """The time (in seconds) to sleep between health checks"""
    _DEFAULT_PING_TIMEOUT = 1
    """Timeout for a response from any given microservice"""

    _logger = None  # type: logging.Logger
    def __init__(self):
        """Constructor"""

        cls = Monitor

        # Initialize class attributes
        if not cls._logger:
            cls._logger = logger.setup(__name__)

        self._monitor_loop_task = None  # type: asyncio.Task
        """Task for :meth:`_monitor_loop`, to ensure it has finished"""
        self._sleep_interval = None  # type: int
        """The time (in seconds) to sleep between health checks"""
        self._ping_timeout = None # type: int
        """Timeout for a response from any given microservice"""

    async def _monitor_loop(self):
        """Main loop for the scheduler"""
        # check health of all microservices every N seconds
        while True:
            for service in Service.Instances.all():
                url = "{}://{}:{}/foglamp/service/ping".format(service._protocol, service._address, service._management_port)
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(url, timeout=self._ping_timeout) as resp:
                            text = await resp.text()
                            res = json.loads(text)
                            if res["uptime"] is None:
                                raise ValueError('Improper Response')
                    except:
                        service._status = 0
                    else:
                        service._status = 1
            await asyncio.ensure_future(asyncio.sleep(self._sleep_interval))

    async def _read_config(self):
        """Reads configuration"""
        default_config = {
            "sleep_interval": {
                "description": "The time (in seconds) to sleep between health checks. (must be greater than 5)",
                "type": "integer",
                "default": str(self._DEFAULT_SLEEP_INTERVAL)
            },
            "ping_timeout": {
                "description": "Timeout for a response from any given microservice. (must be greater than 0)",
                "type": "integer",
                "default": str(self._DEFAULT_PING_TIMEOUT)
            },
        }

        await configuration_manager.create_category('SMNTR', default_config,
                                                    'Service Monitor configuration')

        config = await configuration_manager.get_category_all_items('SMNTR')

        self._sleep_interval = int(config['sleep_interval']['value'])
        self._ping_timeout = int(config['ping_timeout']['value'])


    async def start(self):
        await self._read_config()
        self._monitor_loop_task = asyncio.ensure_future(self._monitor_loop())

