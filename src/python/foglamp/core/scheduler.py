# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler module
"""

import time
import datetime
from enum import IntEnum
import asyncio
import collections
import uuid
import logging  # TODO: Delete me
import sys  # TODO: Needed for logging delete me

import aiopg.sa
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg_types

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Scheduler(object):
    """FogLAMP Task Scheduler
    
    Starts and manages subprocesses (called tasks) via entities
    called Schedules (when to execute) and ProcessSchedules (what to execute).
    
    Most methods are coroutines.
    """

    class _ScheduleType(IntEnum):
        """Enumeration for schedules.schedule_type"""
        TIMED = 1
        INTERVAL = 2
        MANUAL = 3
        STARTUP = 4

    class _TaskState(IntEnum):
        """Enumeration for tasks.task_state"""
        RUNNING = 1
        COMPLETE = 2
        CANCELED = 3
        INTERRUPTED = 4

    _Schedule = collections.namedtuple(
        'Schedule',
        'id type time day interval_seconds exclusive process')
    """Represents a row in the schedules table"""

    class _ScheduleExecution:
        """Tracks information about schedules"""
        __slots__ = ['next_start_time', 'exclusive_lock']

        def __init__(self):
            self.next_start_time = None
            self.exclusive_lock = False

    # Class attributes (begin)
    __scheduled_processes_tbl = None  # type: sa.Table
    __schedules_tbl = None  # type: sa.Table
    __tasks_tbl = None  # type: sa.Table
    __CONNECTION_STRING = "postgresql://foglamp:foglamp@localhost:5432/foglamp"
    # Class attributes (end)

    def __init__(self):
        # Class variables (begin)
        if self.__schedules_tbl is None:
            self.__schedules_tbl = sa.Table(
                'schedules',
                sa.MetaData(),
                sa.Column('id', pg_types.UUID),
                sa.Column('schedule_name', sa.types.VARCHAR(20)),
                sa.Column('process_name', sa.types.VARCHAR(20)),
                sa.Column('schedule_type', sa.types.SMALLINT),
                sa.Column('schedule_time', sa.types.TIME),
                sa.Column('schedule_day', sa.types.SMALLINT),
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
                sa.Column('exit_code', sa.types.INT),
                sa.Column('reason', sa.types.VARCHAR(20)))

            self.__scheduled_processes_tbl = sa.Table(
                'scheduled_processes',
                sa.MetaData(),
                sa.Column('name', pg_types.VARCHAR(20)),
                sa.Column('script', pg_types.JSONB))
        # Class variables (end)

        # Instance variables (begin)
        self._start_time = None
        """When the scheduler started"""
        self.check_schedules_seconds = 5
        """Frequency, in seconds, to check schedules to start tasks"""
        self._paused = False
        """When True, the scheduler will not start any new tasks"""
        self._scheduled_processes = dict()
        """Dictionary of scheduled_processes.id to script. Immutable."""
        self._schedules = dict()
        """Dictionary of schedules.id to _Schedule"""
        self._schedule_executions = dict()
        """Dictionary of schedules.id to _ScheduleExecution"""
        self._processes = dict()
        # pylint: disable=line-too-long
        """Running processes

        Dictionary of tasks.id to
        `Process <https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.asyncio.subprocess.Process>`_
        """
        # pylint: enable=line-too-long
        # Instance variables (end)

    async def stop(self):
        """Attempts to stop the scheduler

        Sends TERM signal to all running tasks. Does not wait for tasks to stop.

        Prevents any new tasks from starting. This can be undone by setting the
        _paused attribute to False.

        Raises TimeoutError:
            A task is still running. Wait and try again.
        """
        logging.getLogger(__name__).info("Stop requested")

        self._paused = True

        # Can not iterate over _processes - it can change mid-iteration
        for key in list(self._processes.keys()):
            try:
                process = self._processes[key]
            except KeyError:
                continue

            logging.getLogger(__name__).info(
                    "Terminating pid %s for task %s",
                    process.pid,
                    key)

            try:
                process.send_signal(0)  # Check whether the process is running
                process.terminate()
            except (ProcessLookupError, OSError):
                pass  # Process has terminated

            await asyncio.sleep(.1)  # sleep 0 doesn't work

        if self._processes:
            raise TimeoutError()

        # TODO: _schedule_executions should be empty
        #if self._schedule_executions:
        #    await asyncio.sleep(.1)  # sleep 0 doesn't work

        self._start_time = None

        return True

    async def _start_startup_task(self, *args):
        """Startup tasks are not tracked in the tasks table"""
        task_id = str(uuid.uuid4())
        logging.getLogger(__name__).info("Starting task %s %s", task_id, args)

        # TODO: what if this fails?
        process = await asyncio.create_subprocess_exec(*args)
        self._processes[task_id] = process
        asyncio.ensure_future(self._wait_for_startup_task_completion(task_id))

    async def _start_task(self, schedule):
        # TODO: What if the process doesn't exist in scheduled_processes
        task_id = str(uuid.uuid4())
        args = self._scheduled_processes[schedule.process]
        logging.getLogger(__name__).info("Starting task %s %s", task_id, args)

        try:
            process = await asyncio.create_subprocess_exec(*args)
            self._processes[task_id] = process
        except Exception as exception:
            # TODO catch real exception
            logging.getLogger(__name__).exception(
                "Unable to start task {} {}".format(task_id, args), exception)

        if schedule.exclusive:
            self._schedule_executions[schedule.id].exclusive_lock = True

        async with aiopg.sa.create_engine(self.__CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                await conn.execute(self.__tasks_tbl.insert().values(
                                        id=task_id,
                                        process_name=schedule.process,
                                        state=int(self._TaskState.RUNNING),
                                        start_time=datetime.datetime.now()))

        asyncio.ensure_future(self._wait_for_task_completion(task_id, schedule))

    async def _wait_for_startup_task_completion(self, task_id):
        # TODO: Restart if the process terminates unexpectedly
        # TODO: Catch the right exception
        try:
            await self._processes[task_id].wait()
        except Exception:
            pass

        logging.getLogger(__name__).info("Task %s stopped", task_id)

        del self._processes[task_id]

    async def _wait_for_task_completion(self, task_id, schedule):
        # TODO: Catch the right exception
        exit_code = None
        try:
            exit_code = await self._processes[task_id].wait()
        except Exception:
            pass

        logging.getLogger(__name__).info("Task %s stopped", task_id)

        del self._processes[task_id]

        if schedule.exclusive:
            # TODO could this dictionary entry disappear?
            self._schedule_executions[schedule.id].exclusive_lock = False

            # TODO: FOGL-308 Compute next start time here when repeating
            # instead of in _check_schedules. Next _check_schedule time
            # execution time should be recalculated
            asyncio.ensure_future(self._check_schedules())

        async with aiopg.sa.create_engine(self.__CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                await conn.execute(
                    self.__tasks_tbl.update().
                    where(self.__tasks_tbl.c.id == task_id).
                    values(exit_code=exit_code,
                           state=int(self._TaskState.COMPLETE),
                           end_time=datetime.datetime.now()))

    async def _check_schedules(self):
        """Starts tasks according to schedules based on the current time"""
        if self._paused:
            return

        # Can not iterate over _next_starts - it can change mid-iteration
        for key in list(self._schedule_executions.keys()):
            if self._paused:
                break

            try:
                schedule = self._schedules[key]
            except KeyError:
                continue

            exec_info = self._schedule_executions[key]

            if time.time() >= exec_info.next_start_time:
                # Set next time before any 'await' calls to avoid reentrancy
                if not self._compute_next_start(schedule):
                    del self._schedule_executions[key]

                if schedule.exclusive and exec_info.exclusive_lock:
                    pass
                else:
                    if schedule.type == self._ScheduleType.STARTUP:
                        await self._start_startup_task(*self._scheduled_processes[schedule.process])
                    else:
                        await self._start_task(schedule)

    def _compute_first_start(self, schedule, current_time):
        if schedule.type == self._ScheduleType.INTERVAL:
            exec_info = self._ScheduleExecution()
            exec_info.next_start_time = current_time + schedule.interval_seconds
            self._schedule_executions[schedule.id] = exec_info
        elif schedule.type == self._ScheduleType.TIMED:
            # Only support run daily
            add_day = False

            dt = datetime.datetime.fromtimestamp(current_time)
            requested_time = schedule.time

            if dt.time() > requested_time:
                add_day = True

            dt = datetime.datetime(
                    year=dt.year,
                    month=dt.month,
                    day=dt.day,
                    second=requested_time.second,
                    minute=requested_time.minute,
                    hour=requested_time.hour)

            if add_day:
                # Go to the next day
                dt = dt + datetime.timedelta(days=1)

            exec_info = self._ScheduleExecution()
            exec_info.next_start_time = time.mktime(dt.timetuple())

        elif schedule.type == self._ScheduleType.STARTUP:
            exec_info = self._ScheduleExecution()
            exec_info.next_start_time = current_time
            self._schedule_executions[schedule.id] = exec_info
            return self._start_time

    def _compute_next_start(self, schedule):
        if schedule.interval_seconds:
            exec_info = self._schedule_executions[schedule.id]

            if schedule.type == self._ScheduleType.TIMED:
                next_dt = datetime.datetime.fromtimestamp(exec_info.next_start_time)
                next_dt = next_dt + datetime.timedelta(seconds=schedule.interval_seconds)

                exec_info.next_start_time = time.mktime(next_dt.timetuple())
            else:
                exec_info.next_start_time += schedule.interval_seconds

            return True

        return False

    async def _get_scheduled_processes(self):
        query = sa.select([self.__scheduled_processes_tbl.c.name,
                           self.__scheduled_processes_tbl.c.script])
        query.select_from(self.__scheduled_processes_tbl)

        async with aiopg.sa.create_engine(self.__CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    self._scheduled_processes[row.name] = row.script

    async def _get_schedules(self):
        # TODO Get processes first, then add to Schedule
        query = sa.select([self.__schedules_tbl.c.id,
                           self.__schedules_tbl.c.schedule_type,
                           self.__schedules_tbl.c.schedule_time,
                           self.__schedules_tbl.c.schedule_day,
                           self.__schedules_tbl.c.schedule_interval,
                           self.__schedules_tbl.c.exclusive,
                           self.__schedules_tbl.c.process_name])

        query.select_from(self.__schedules_tbl)

        async with aiopg.sa.create_engine(self.__CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    interval = row.schedule_interval
                    interval_seconds = None

                    if interval:
                        interval_seconds = 3600*interval.hour + 60*interval.minute + interval.second

                    schedule = self._Schedule(
                        id=row.id,
                        type=row.schedule_type,
                        day=row.schedule_day,
                        time=row.schedule_time,
                        interval_seconds=interval_seconds,
                        exclusive=row.exclusive,
                        process=row.process_name)

                    # TODO: Move this to _add_schedule to check for errors
                    self._schedules[row.id] = schedule
                    self._compute_first_start(schedule, self._start_time)

    async def _read_storage(self):
        """Reads schedule information from the storage server"""
        await self._get_scheduled_processes()
        await self._get_schedules()

    async def _main(self):
        """Main loop for the scheduler

        - Reads configuration and schedules
        - Runs :meth:`Scheduler._check_schedules` in an endless loop until
          :meth:`Scheduler.stop` is called
        """
        # TODO log exception here or add an exception handler in asyncio
        await self._read_storage()

        while True:
            await self._check_schedules()
            if self._paused:
                return
            await asyncio.sleep(self.check_schedules_seconds)

    # TODO: Used for development. Delete me.
    @staticmethod
    def _debug_logging_stdout():
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(ch)

    def start(self):
        """Starts the scheduler

        Raises StartedException:
            Scheduler already started
        """
        if self._start_time:
            raise ValueError("The scheduler is already running")

        self._start_time = time.time()
        self._debug_logging_stdout()
        asyncio.ensure_future(self._main())
        # await self._start_startup_task('python3', '-m', 'foglamp.storage')
