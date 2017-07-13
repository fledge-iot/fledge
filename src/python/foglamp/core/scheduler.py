# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler"""

import asyncio
from asyncio.subprocess import Process

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# For Process methods, see https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.asyncio.subprocess.Process
# or upgrade to a version of Python that uses type annotations
_processes = []  # type: List[Process]


def shutdown():
    """Stops the scheduler
    
    Terminates long-running processes like the device server.
    
    Waits for tasks to finish. There is no way to stop tasks that are already running.
    """
    for process in _processes:
        try:
            process.terminate()
        except ProcessLookupError:
            # This occurs when the process has terminated already
            pass


async def _start_device_server():
    """Starts the device server (foglamp.device) as a subprocess"""
    process = await asyncio.create_subprocess_exec(
        'python3', '-m', 'foglamp.device')

    global _processes
    _processes.append(process)


async def _main():
    await _start_device_server()
    # More is coming


def start():
    """Start the scheduler"""

    asyncio.ensure_future(_main())

