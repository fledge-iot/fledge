# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler"""

import time
from enum import Enum
import asyncio
import logging
import aiopg.sa
# from asyncio.subprocess import Process
# from typing import List

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg_types

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Scheduler(object):
    """FogLAMP scheduler"""

    class _ScheduleTypes(Enum):
        """Schedule types"""
        interval = 1
        timed = 2

    class _TaskStates(Enum):
        """Task states"""
        running = 1
        complete = 2
        canceled = 3
        interrupted = 4

    # Class attributes (begin)
    __scheduled_processes_tbl = None  # type: sa.Table
    __schedules_tbl = None  # type: sa.Table
    __tasks_tbl = None  # type: sa.Table
    # Class attributes (end)

    def __init__(self):
        """Constructor"""

        # Class variables (begin)
        if self.__schedules_tbl is None:
            self.__schedules_tbl = sa.Table(
                'schedules',
                sa.MetaData(),
                sa.Column('id', pg_types.UUID),
                sa.Column('schedule_name', sa.types.VARCHAR(20)),
                sa.Column('process_name', sa.types.VARCHAR(20)),
                sa.Column('schedule_type', sa.types.INT),
                sa.Column('schedule_interval', sa.types.TIME),
                sa.Column('exclusive', sa.types.BOOLEAN))

            self.__tasks_tbl = sa.Table(
                'tasks',
                sa.MetaData(),
                sa.Column('id', pg_types.UUID),
                sa.Column('process_name', sa.types.VARCHAR(20)),
                sa.Column('state', sa.types.INT),
                sa.Column('start_time', sa.types.TIMESTAMP),
                sa.Column('end_time', sa.types.TIMESTAMP),
                sa.Column('reason', sa.types.VARCHAR(20)))

            self.__scheduled_processes_tbl = sa.Table(
                'scheduled_processes',
                sa.MetaData(),
                sa.Column('name', pg_types.VARCHAR(20)),
                sa.Column('script', pg_types.JSONB))
        # Class variables (end)

        # Instance variables (begin)
        self.last_check_time = None
        self.start_time = time.time()
        self.__processes = []  # type: List[Process]
        self.__scheduled_processes = dict()

        # pylint: disable=line-too-long
        """Long running processes

        A list of
        `Process <https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.asyncio.subprocess.Process>`_
        objects
        """
        # pylint: enable=line-too-long
        # Instance variables (end)

    def stop(self):
        """Stops the scheduler

        Terminates long-running processes like the device server.

        Waits for tasks to finish. There is no way to stop tasks that are already running.

        :return True if all processes have stopped
        """
        # TODO After telling processes to stop, wait for them to stop
        logging.getLogger(__name__).info("Stopping")
        for process in self.__processes:
            try:
                process.terminate()
            except ProcessLookupError:
                # This occurs when the process has terminated already
                # TODO remove process from the list
                pass

    async def _start_device_server(self):
        """Starts the device server (foglamp.device) as a subprocess"""

        # TODO what if this fails?
        process = await asyncio.create_subprocess_exec( 'python3', '-m', 'foglamp.device' )
        self.__processes.append(process)

    async def _get_scheduled_processes(self):
        query = sa.select([self.__scheduled_processes_tbl.c.name,
                           self.__scheduled_processes_tbl.c.script])
        query.select_from(self.__scheduled_processes_tbl)

        async with aiopg.sa.create_engine(
                'postgresql://foglamp:foglamp@localhost:5432/foglamp') as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    self.__scheduled_processes[row.name] = row.script

    async def _read_storage(self):
        """Read processes and schedules"""
        await self._get_scheduled_processes()
        print(self.__scheduled_processes)

    def start(self):
        """Starts the scheduler"""
        asyncio.ensure_future(self._start_device_server())
        asyncio.ensure_future(self._read_storage())

