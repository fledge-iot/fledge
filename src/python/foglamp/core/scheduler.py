#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler"""

import asyncio
from concurrent.futures import ProcessPoolExecutor

__author__    = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__   = "Apache 2.0"
__version__   = "${VERSION}"

_executor = None
"""Static processes"""


def shutdown():
    """Stops the scheduler"""
    _executor.shutdown()


def _start_device():
    """Start the device service (temporary)"""
    try:
        exec("from foglamp.device import server; server.start()")
    except BaseException:
        pass

async def _main(loop):
    while True:
        await asyncio.sleep(0)
    pass


def start(loop):
    """Start the scheduler"""

    global _executor
    _executor = ProcessPoolExecutor(1)

    asyncio.ensure_future(loop.run_in_executor(_executor, _start_device))

    # asyncio.ensure_future(_main(loop))

