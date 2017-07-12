# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler"""

import time
import asyncio
from asyncio.subprocess import Process

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

"""CoAP handler for coap://other/sensor_readings URI 
"""

_sensor_values_tbl = sa.Table(
    'readings',
    sa.MetaData(),
    sa.Column('asset_code', sa.types.VARCHAR(50)),
    sa.Column('read_key', sa.types.VARCHAR(50)),
    sa.Column('user_ts', sa.types.TIMESTAMP),
    sa.Column('reading', JSONB))

_processes = []  # type: List[Process]
"""Long running processes

https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.asyncio.subprocess.Process
"""

_last_check_time = time.now()

def shutdown():
    """Stops the scheduler
    
    Terminates long-running processes like the device server.
    
    Waits for tasks to finish. There is no way to stop tasks that are already running.
    """
    for process in _processes:
        process.terminate()

def
    """Processes interval schedules and starts processes"""

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

