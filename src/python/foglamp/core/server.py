# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import signal
import asyncio
from aiohttp import web

from foglamp.core import routes
from foglamp.core import middleware
from foglamp.core import scheduler

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def _make_app():
    """create the server"""
    # https://aiohttp.readthedocs.io/en/stable/_modules/aiohttp/web.html#run_app
    app = web.Application(middlewares=[middleware.error_middleware])
    routes.setup(app)
    return app


def _shutdown(loop):
    scheduler.shutdown()
    for task in asyncio.Task.all_tasks():
        task.cancel()
    loop.stop()


def start():
    """starts the server"""
    loop = asyncio.get_event_loop()
    scheduler.start(loop)

    for signal_name in (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
        loop.add_signal_handler(signal_name, _shutdown, loop)

    web.run_app(_make_app(), host='0.0.0.0', port=8082)

