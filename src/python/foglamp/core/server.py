# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Core server module"""

import signal
import asyncio
from aiohttp import web

from foglamp.core import routes
from foglamp.core import middleware
from foglamp.core import scheduler

__author__ = "Praveen Garg, Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Server:
    def __init__(self):
        """Constructor"""
        self.__scheduler = scheduler.Scheduler()

    def start(self):
        loop = asyncio.get_event_loop()

        for signal_name in (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
            loop.add_signal_handler(signal_name, _shutdown, loop, self)

        # https://aiohttp.readthedocs.io/en/stable/_modules/aiohttp/web.html#run_app
        web.run_app(__make_app(), host='0.0.0.0', port=8082)

    @staticmethod
    def __make_app():
        """Creates the server"""
        app = web.Application(middlewares=[middleware.error_middleware])
        routes.setup(app)
        return app

    @staticmethod
    def _shutdown(loop, self: Server):
        """Shuts down the server"""
        scheduler.shutdown()
        for task in asyncio.Task.all_tasks():
            task.cancel()
        loop.stop()

