# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler"""

import asyncio
from asyncio.subprocess import Process

__author__    = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__   = "Apache 2.0"
__version__   = "${VERSION}"

# For Process methods, see https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.asyncio.subprocess.Process
# or upgrade to a version of Python that uses type annotations
_processes = []  # type: List[Process]


def shutdown():
    """Stops the scheduler"""
    for process in _processes:
        process.terminate()


async def _start_device():
    process = await asyncio.create_subprocess_exec(
        'python3', '-m', 'foglamp.device')

    global _processes
    _processes.insert(-1, process)


async def _main():
    await _start_device()


def start(loop):
    """Start the scheduler"""

    asyncio.ensure_future(_main())

