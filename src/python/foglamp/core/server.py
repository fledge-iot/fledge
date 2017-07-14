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
    """Core server"""

    # Class attributes (begin)
    __scheduler = None
    # Class attributes (end)

    @classmethod
    def start(cls, loop=None):
        """Starts the server"""
        if not loop:
            loop = asyncio.get_event_loop()

        cls.__scheduler = scheduler.Scheduler()

        # Register signal handlers
        for signal_name in (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
            loop.add_signal_handler(signal_name, cls.stop, loop)

        cls.__scheduler.start()

        # https://aiohttp.readthedocs.io/en/stable/_modules/aiohttp/web.html#run_app
        web.run_app(cls._make_app(), host='0.0.0.0', port=8082)

    @staticmethod
    def _make_app():
        """Creates the REST server

        :rtype: web.Application
        """
        app = web.Application(middlewares=[middleware.error_middleware])
        routes.setup(app)
        return app

    @classmethod
    def stop(cls, loop):
        """Stops the server"""
        cls.__scheduler.stop()

        for task in asyncio.Task.all_tasks():
            task.cancel()
        loop.stop()
