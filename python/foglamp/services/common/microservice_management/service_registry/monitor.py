# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Monitor module"""

import asyncio
import aiohttp
import json
import logging

from foglamp.common import logger
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.common.microservice_management.service_registry.instance import Service
from foglamp.services.core import connect

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Monitor(object):

    _DEFAULT_SLEEP_INTERVAL = 5
    """The time (in seconds) to sleep between health checks"""

    _DEFAULT_PING_TIMEOUT = 1
    """Timeout for a response from any given micro-service"""

    _logger = None  # type: logging.Logger

    def __init__(self):

        self._logger = logger.setup("SMNTR", level=logging.INFO)

        self._monitor_loop_task = None  # type: asyncio.Task
        """Task for :meth:`_monitor_loop`, to ensure it has finished"""
        self._sleep_interval = None  # type: int
        """The time (in seconds) to sleep between health checks"""
        self._ping_timeout = None  # type: int
        """Timeout for a response from any given micro-service"""

    async def _monitor_loop(self):
        """Main loop for the scheduler"""
        # check health of all micro-services every N seconds
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
                        Service.Instances.unregister(service._id)
                        self._logger.info("Unregistered the failed micro-service %s", service.__repr__())
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
                "description": "Timeout for a response from any given micro-service. (must be greater than 0)",
                "type": "integer",
                "default": str(self._DEFAULT_PING_TIMEOUT)
            },
        }

        storage_client = connect.get_storage()
        cfg_manager = ConfigurationManager(storage_client)
        await cfg_manager.create_category('SMNTR', default_config, 'Service Monitor configuration')

        config = await cfg_manager.get_category_all_items('SMNTR')

        self._sleep_interval = int(config['sleep_interval']['value'])
        self._ping_timeout = int(config['ping_timeout']['value'])

    async def start(self):
        await self._read_config()
        self._monitor_loop_task = asyncio.ensure_future(self._monitor_loop())

    async def stop(self):
        self._monitor_loop_task.cancel()
