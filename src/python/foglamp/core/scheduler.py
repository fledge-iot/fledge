# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler"""

import time
from enum import Enum
import asyncio
import logging
import collections
import uuid

import aiopg.sa
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg_types

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Scheduler(object):
    """FogLAMP scheduler"""

    class _ScheduleType(Enum):
        """Schedule types"""
        interval_seconds = 0
        timed = 1

    class _TaskState(Enum):
        """Task states"""
        running = 1
        complete = 2
        canceled = 3
        interrupted = 4

    _Schedule = collections.namedtuple(
        'Schedule',
        'id type time interval exclusive process_name')
    """Represents a row in the schedules table"""

    # Class attributes (begin)
    __scheduled_processes_tbl = None  # type: sa.Table
    __schedules_tbl = None  # type: sa.Table
    __tasks_tbl = None  # type: sa.Table
    __CONNECTION_STRING = "postgresql://foglamp:foglamp@localhost:5432/foglamp"
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
                sa.Column('schedule_time', sa.types.TIME),
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
        self.start_time = time.time()
        self.last_check_time = self.start_time
        self.check_schedules_interval_seconds = 60
        self.__scheduled_processes = dict()
        """ scheduled_processes.id to script """
        self.__schedules = dict()
        """ schedules.id to _Schedule """
        self.__schedule_factors = dict()
        """For interval schedules only
        
        Maps schedules.id to a "time factor" when process was last executed
        
        A "time factor" is the amount of time the scheduler has been running divided by 
        the schedule's interval time. The division is converted to an integer
        using floor(). For example, if the interval time is
        15 minutes and the process has been running for 35 minutes, the
        time factor is 2.
        """
        self.__running_exclusive_schedules = set()
        """A set of session ids that are running, for 'exclusive' schedules"""
        self.__processes = dict()
        # pylint: disable=line-too-long
        """Running processes

        tasks.id to
        `Process <https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.asyncio.subprocess.Process>`_
        """
        # pylint: enable=line-too-long
        # Instance variables (end)

    def stop(self):
        """Stops the scheduler

        Terminates long-running processes like the device server.

        Waits for tasks to finish. There is no way to stop tasks that are already running.

        :return True if all processes have stopped
        """
        logging.getLogger(__name__).info("Processing stop request")
        all_stopped = True

        for key, process in self.__processes.items():
            try:
                process.terminate()
                process.signal(0)
                all_stopped = False
            except (ProcessLookupError, OSError):
                del self.__processes[key]

        return all_stopped

    async def _start_device_server(self):
        """Starts the device server (foglamp.device) as a subprocess"""

        # TODO what if this fails?
        process = await asyncio.create_subprocess_exec('python3', '-m', 'foglamp.device')
        self.__processes[uuid.uuid4()] = process

    async def _get_scheduled_processes(self):
        query = sa.select([self.__scheduled_processes_tbl.c.name,
                           self.__scheduled_processes_tbl.c.script])
        query.select_from(self.__scheduled_processes_tbl)

        async with aiopg.sa.create_engine(self.__CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    self.__scheduled_processes[row.name] = row.script

    async def _get_schedules(self):
        query = sa.select([self.__schedules_tbl.c.id,
                           self.__schedules_tbl.c.schedule_type,
                           self.__schedules_tbl.c.schedule_time,
                           self.__schedules_tbl.c.schedule_interval,
                           self.__schedules_tbl.c.exclusive,
                           self.__schedules_tbl.c.process_name])

        query.select_from(self.__schedules_tbl)

        async with aiopg.sa.create_engine(self.__CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    interval_seconds = None
                    if row.interval is not None:
                        t = row.interval
                        interval_seconds = 3600*t.hour+60*t.minute+t.second

                    self.__schedules[row.id] = _Schedule(
                                                id=row.id,
                                                type=row.schedule_type,
                                                time=row.schedule_time,
                                                interval_seconds=interval_seconds,
                                                exclusive=row.exclusive,
                                                process_name=row.process_name)

    async def _start_task(self, schedule):
        # TODO: What if this fails
        process = await asyncio.create_subprocess_exec(
            self.__scheduled_processes[schedule.process_name].script)

        task_id = uuid.uuid4()
        self.__processes[task_id] = process

        if schedule.exclusive:
            self.__running_exclusive_schedules.add(schedule.id)

        async with aiopg.sa.create_engine(self.__CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                await conn.execute(self.__tasks_tbl.insert().values(
                                        id=task_id,
                                        process_name=schedule.process_name,
                                        state=self._TaskState.running,
                                        start_time=time.time()))

        asyncio.ensure_future(self._wait_for_task_completion(task_id, schedule))

    async def _wait_for_task_completion(self, task_id, schedule):
        # TODO: Catch the right exception
        try:
            self.__processes[task_id].wait()
        except Exception:
            pass

        if schedule.exclusive:
            self.__running_exclusive_schedules.remove(schedule.id)

        del self.__processes[task_id]

        async with aiopg.sa.create_engine(self.__CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                await conn.execute(
                    self.__tasks_tbl.update().
                    where(self.__tasks_tbl.c.id == task_id).
                    values(reason='?',
                           end_time=time.time(),
                           state=self._TaskState.complete))

    async def schedule(self):
        seconds_run = self.__start_time - self.__last_check_time
        for key, schedule in self.__schedules:
            if schedule.exclusive:
                if is running:
                    next

            start_task = False

            if schedule.type == self._ScheduleType.interval:
                if schedule.interval_seconds == 0:
                    del self.__schedules[key]
                    start_task = True
                else:
                    factor = seconds_run / schedule.interval_seconds
                    if factor > self.__schedule_factors.get(schedule.id, 0):
                        self.__schedule_factors[schedule.id] = factor
                        start_task = True

            if start_task:
                asyncio.ensure_future(self._start_task(schedule))


    async def _schedule(self):
        await asyncio.ensure_future(self._read_storage())
        while True:
            await self.schedule()
            await asyncio.sleep(self.check_schedules_interval_seconds)

asyncio.ensure_future(self.schedule)

    async def _read_storage(self):
        """Read processes and schedules"""
        await self._get_scheduled_processes()
        await self._get_schedules()

    def start(self):
        """Starts the scheduler"""
        asyncio.ensure_future(self._start_device_server())
        asyncio.ensure_future(self._schedule())

