# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler module"""

import asyncio
import collections
import datetime
import logging
import math
import time
import uuid
from enum import IntEnum
from typing import List

import aiopg.sa
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg_types

from foglamp import logger


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
_CONNECTION_STRING = "dbname='foglamp'"


class NotReadyError(RuntimeError):
    pass


class DuplicateRequestError(RuntimeError):
    pass


class TaskNotRunningError(RuntimeError):
    """Raised when canceling a task and the task isn't running"""
    def __init__(self, task_id: uuid.UUID, *args):
        self.task_id = task_id
        super(RuntimeError, self).__init__(
            "Task is not running: {}".format(task_id), *args)


class TaskNotFoundError(ValueError):
    def __init__(self, task_id: uuid.UUID, *args):
        self.task_id = task_id
        super(ValueError, self).__init__(
            "Task not found: {}".format(task_id), *args)


class ScheduleNotFoundError(ValueError):
    def __init__(self, schedule_id: uuid.UUID, *args):
        self.schedule_id = schedule_id
        super(ValueError, self).__init__(
            "Schedule not found: {}".format(schedule_id), *args)


class Task(object):
    """A task represents an operating system process"""

    class State(IntEnum):
        """Enumeration for tasks.task_state"""
        RUNNING = 1
        COMPLETE = 2
        CANCELED = 3
        INTERRUPTED = 4

    __slots__ = ['task_id', 'process_name', 'state', 'cancel_requested', 'start_time',
                 'end_time', 'state', 'exit_code', 'reason']

    def __init__(self):
        self.task_id = None  # type: uuid.UUID
        """Unique identifier"""
        self.process_name = None  # type: str
        self.reason = None  # type: str
        self.state = None  # type: Task.State
        self.cancel_requested = None  # type: datetime.datetime
        self.start_time = None  # type: datetime.datetime
        self.end_time = None  # type: datetime.datetime
        self.exit_code = None  # type: int


class ScheduledProcess(object):
    """Represents a program that a Task can run"""

    __slots__ = ['name', 'script']

    def __init__(self):
        self.name = None  # type: str
        """Unique identifier"""
        self.script = None  # type: List[ str ]


class Schedule(object):
    """Schedule base class"""
    __slots__ = ['schedule_id', 'name', 'process_name', 'exclusive', 'repeat', 'type']

    def __init__(self):
        self.schedule_id = None
        """uuid.UUID"""
        self.name = None
        """str"""
        self.exclusive = True
        """bool"""
        self.repeat = None
        """"datetime.timedelta"""
        self.process_name = None
        """str"""
        self.type = None
        """int"""


class IntervalSchedule(Schedule):
    """Interval schedule"""
    pass


class TimedSchedule(Schedule):
    """Timed schedule"""
    __slots__ = ['time', 'day']

    def __init__(self):
        super().__init__()
        self.time = None
        """int"""
        self.day = None
        """int from 1 (Monday) to 7 (Sunday)"""


class ManualSchedule(Schedule):
    """A schedule that is run manually"""
    pass


class StartUpSchedule(Schedule):
    """A schedule that is run when the scheduler starts"""
    pass


class Scheduler(object):
    """FogLAMP Task Scheduler

    Starts and tracks 'tasks' that run periodically,
    start-up, and/or manually.

    Schedules specify when to start and restart Tasks. A Task
    is an operating system process. ScheduleProcesses
    specify process/command name and parameters.

    Most methods are coroutines and use the default
    event loop to create tasks.

    This class does not use threads.

    Usage:
        - Call :meth:`start`
        - Wait
        - Call :meth:`stop`
    """

    class _ScheduleType(IntEnum):
        """Enumeration for schedules.schedule_type"""
        STARTUP = 1
        TIMED = 2
        INTERVAL = 3
        MANUAL = 4

    # TODO: Document the fields
    _ScheduleRow = collections.namedtuple(
        'ScheduleRow',
        'id name type time day repeat repeat_seconds exclusive process_name')
    """Represents a row in the schedules table"""

    class _TaskProcess(object):
        """Tracks a running task with some flags"""
        __slots__ = ['task_id', 'process', 'cancel_requested', 'schedule', 'start_time']

        def __init__(self):
            self.task_id = None  # type: uuid.UUID
            self.process = None  # type: asyncio.subprocess.Process
            self.cancel_requested = None  # type: int
            """Epoch time when cancel was requested"""
            self.schedule = None  # _ScheduleRow
            self.start_time = None  # type: int
            """Epoch time when the task was started"""

    # TODO: Methods that accept a schedule and look in _schedule_executions
    # should accept schedule_execution instead. Add reference to schedule
    # in _ScheduleExecution.

    class _ScheduleExecution(object):
        """Tracks information about schedules"""

        __slots__ = ['next_start_time', 'task_processes', 'start_now']

        def __init__(self):
            self.next_start_time = None
            """When to next start a task for the schedule"""
            self.task_processes = dict()
            """dict of task id to _TaskProcess"""
            self.start_now = False
            """True when a task is queued to start via :meth:`start_task`"""

    # Constant class attributes
    DEFAULT_MAX_ACTIVE_TASKS = 50
    _HOUR_SECONDS = 3600
    _DAY_SECONDS = 3600*24
    _WEEK_SECONDS = 3600*24*7
    _MAX_SLEEP = 9999999
    """When there is nothing to do, sleep for this number of seconds (forever)"""
    _ONE_HOUR = datetime.timedelta(hours=1)
    _ONE_DAY = datetime.timedelta(days=1)
    _STOP_WAIT_SECONDS = 5
    """Wait this number of seconds in :meth:`stop` for tasks to stop"""

    # Mostly constant class attributes
    _scheduled_processes_tbl = None  # type: sa.Table
    _schedules_tbl = None  # type: sa.Table
    _tasks_tbl = None  # type: sa.Table
    _logger = None

    def __init__(self):
        """Constructor"""

        # Class attributes
        #
        # Do not alter class attributes using
        # 'self.' Otherwise they will become
        # instance attributes.
        cls = type(self)
        if not cls._logger:
            # cls._logger = logger.setup(__name__, destination=logger.CONSOLE, level=logging.DEBUG)
            # cls._logger = logger.setup(__name__, level=logging.DEBUG)
            cls._logger = logger.setup(__name__)

        if cls._schedules_tbl is None:
            metadata = sa.MetaData()

            cls._schedules_tbl = sa.Table(
                'schedules',
                metadata,
                sa.Column('id', pg_types.UUID),
                sa.Column('schedule_name', sa.types.VARCHAR(20)),
                sa.Column('process_name', sa.types.VARCHAR(20)),
                sa.Column('schedule_type', sa.types.SMALLINT),
                sa.Column('schedule_time', sa.types.TIME),
                sa.Column('schedule_day', sa.types.SMALLINT),
                sa.Column('schedule_interval', sa.types.Interval),
                sa.Column('exclusive', sa.types.BOOLEAN))

            cls._tasks_tbl = sa.Table(
                'tasks',
                metadata,
                sa.Column('id', pg_types.UUID),
                sa.Column('process_name', sa.types.VARCHAR(20)),
                sa.Column('state', sa.types.INT),
                sa.Column('start_time', sa.types.TIMESTAMP),
                sa.Column('end_time', sa.types.TIMESTAMP),
                sa.Column('pid', sa.types.INT),
                sa.Column('exit_code', sa.types.INT),
                sa.Column('reason', sa.types.VARCHAR(255)))

            cls._scheduled_processes_tbl = sa.Table(
                'scheduled_processes',
                metadata,
                sa.Column('name', pg_types.VARCHAR(20)),
                sa.Column('script', pg_types.JSONB))

        # Instance attributes
        self._ready = False
        """True when the scheduler is ready to accept API calls"""
        self._start_time = None
        """When the scheduler started"""
        self.max_task_processes = self.DEFAULT_MAX_ACTIVE_TASKS
        """Maximum number of active tasks"""
        self._paused = False
        """When True, the scheduler will not start any new tasks"""
        self._process_scripts = dict()
        """Dictionary of schedules.id to script"""
        self._schedules = dict()
        """Dictionary of schedules.id to immutable _Schedule"""
        self._schedule_executions = dict()
        """Dictionary of schedules.id to _ScheduleExecution"""
        self._task_processes = dict()
        """task id to _TaskProcess"""
        self._check_processes_pending = None
        """bool: True when request to run check_processes"""
        self._main_loop_task = None
        """Coroutine for _main_loop_task, to ensure it has finished"""
        self._main_sleep_task = None
        """Coroutine that sleeps in the main loop"""

    async def stop(self):
        """Attempts to stop the scheduler

        Sends TERM signal to all running tasks. Does not wait for tasks to stop.

        Prevents any new tasks from starting. This can be undone by setting the
        _paused attribute to False.

        Raises:
            TimeoutError: A task is still running. Wait and try again.
        """
        if not self._start_time:
            return

        self._logger.info("Processing stop request")

        # This method is designed to be called multiple times

        if not self._paused:
            # Stop the main loop
            self._paused = True
            self._resume_check_schedules()
            await self._main_loop_task
            self._main_loop_task = None

        # Can not iterate over _task_processes - it can change mid-iteration
        for task_id in list(self._task_processes.keys()):
            try:
                task_process = self._task_processes[task_id]
            except KeyError:
                continue

            # TODO: FOGL-356 track the last time TERM was sent to each task
            task_process.cancel_requested = time.time()

            schedule = task_process.schedule

            self._logger.info(
                "Stopping process: Schedule '%s' process '%s' task %s pid %s\n%s",
                schedule.name,
                schedule.process_name,
                task_id,
                task_process.process.pid,
                self._process_scripts[schedule.process_name])

            try:
                task_process.process.terminate()
            except ProcessLookupError:
                pass  # Process has terminated

        for _ in range(self._STOP_WAIT_SECONDS):
            if not self._task_processes:
                break
            await asyncio.sleep(1)

        if self._task_processes:
            raise TimeoutError()

        self._schedule_executions = None
        self._task_processes = None
        self._schedules = None
        self._process_scripts = None

        self._ready = False
        self._paused = False
        self._start_time = None

        self._logger.info("Stopped")

        return True

    async def _start_task(self, schedule: _ScheduleRow) -> None:
        """Starts a task process

        Raises:
            EnvironmentError: If the process could not start
        """

        # This check is necessary only if significant time can elapse between "await" and
        # the start of the awaited coroutine.
        args = self._process_scripts[schedule.process_name]

        task_process = self._TaskProcess()
        task_process.start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(*args)
        except EnvironmentError:
            self._logger.exception(
                "Unable to start schedule '%s' process '%s'\n%s".format(
                    schedule.name, schedule.process_name, args))
            raise

        task_id = uuid.uuid4()
        task_process.process = process
        task_process.schedule = schedule
        task_process.task_id = task_id

        self._task_processes[task_id] = task_process
        self._schedule_executions[schedule.id].task_processes[task_id] = task_process

        self._logger.info(
            "Process started: Schedule '%s' process '%s' task %s pid %s, %s active tasks\n%s",
            schedule.name, schedule.process_name, task_id, process.pid,
            len(self._task_processes), args)

        if schedule.type == self._ScheduleType.STARTUP:
            # Startup tasks are not tracked in the tasks table
            asyncio.ensure_future(self._wait_for_task_completion(task_process))
        else:
            # The task row needs to exist before the completion handler runs
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    await conn.execute(self._tasks_tbl.insert().values(
                        id=str(task_id),
                        pid=(self._schedule_executions[schedule.id].
                             task_processes[task_id].process.pid),
                        process_name=schedule.process_name,
                        state=int(Task.State.RUNNING),
                        start_time=datetime.datetime.now()))

            asyncio.ensure_future(self._wait_for_task_completion(task_process))

    async def _wait_for_task_completion(self, task_process: _TaskProcess)->None:
        # TODO: If an exception is raised here, _task_processes will be
        # out of sync with reality and the scheduler will never know when
        # the process terminates. However, if an exception like CanceledError
        # occurs here, it's assumed that the process needs to stop ASAP and
        # I/O activities such as writing to the database should be avoided. It is
        # presumed that all coroutines will be canceled and the process will exit.
        exit_code = await task_process.process.wait()

        schedule = task_process.schedule

        self._logger.info(
            "Process terminated: Schedule '%s' process '%s' task %s pid %s exit %s,"
            " %s active tasks\n%s",
            schedule.name,
            schedule.process_name,
            task_process.task_id,
            task_process.process.pid,
            exit_code,
            len(self._task_processes)-1,
            self._process_scripts[schedule.process_name])

        schedule_execution = self._schedule_executions[schedule.id]
        del schedule_execution.task_processes[task_process.task_id]

        schedule_deleted = False

        # Pick up modifications to the schedule
        # Or maybe it's been deleted
        try:
            schedule = self._schedules[schedule.id]
        except KeyError:
            schedule_deleted = True

        if self._paused or schedule_deleted or (
                            schedule.repeat is None and not schedule_execution.start_now):
            if schedule_execution.next_start_time:
                schedule_execution.next_start_time = None
                self._logger.info(
                    "Tasks will no longer execute for schedule '%s'", schedule.name)
        elif schedule.exclusive:
            self._schedule_next_task(schedule)

        if schedule.type != self._ScheduleType.STARTUP:
            if exit_code < 0 and task_process.cancel_requested:
                state = Task.State.CANCELED
            else:
                state = Task.State.COMPLETE

            # Update the task's status
            # TODO if no row updated output a WARN row
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    result = await conn.execute(
                        self._tasks_tbl.update().where(
                            self._tasks_tbl.c.id == str(task_process.task_id)).values(
                            exit_code=exit_code,
                            state=int(state),
                            end_time=datetime.datetime.now()))

                    if result.rowcount == 0:
                        self._logger.warning("Task %s not found. Unable to update its status",
                                             task_process.task_id)

        # Due to maximum active tasks reached it is necessary to
        # look for schedules that are ready to run even if there
        # are only manual tasks waiting
        # TODO Do this only if len(_task_processes) >= max_processes or
        # an exclusive task finished and ( start_now or schedule.repeats )
        self._resume_check_schedules()

        # This must occur after all awaiting! The size of _task_processes
        # is used by stop() to determine whether the scheduler can stop.
        del self._task_processes[task_process.task_id]

    async def queue_task(self, schedule_id: uuid.UUID)->None:
        """Requests a task to be started for a schedule

        Args:
            schedule_id: Specifies the schedule

        Raises:
            SchedulePausedError:
                The scheduler is stopping

            ScheduleNotFoundError
        """
        if self._paused or not self._ready:
            raise NotReadyError()

        try:
            schedule_row = self._schedules[schedule_id]
        except KeyError:
            raise ScheduleNotFoundError(schedule_id)

        try:
            schedule_execution = self._schedule_executions[schedule_id]
        except KeyError:
            schedule_execution = self._ScheduleExecution()
            self._schedule_executions[schedule_row.id] = schedule_execution

        schedule_execution.start_now = True

        self._logger.info("Queued schedule '%s' for execution", schedule_row.name)
        self._resume_check_schedules()

    async def _check_schedules(self):
        """Starts tasks according to schedules based on the current time"""
        earliest_start_time = None

        # Can not iterate over _schedule_executions - it can change mid-iteration
        for schedule_id in list(self._schedule_executions.keys()):
            if self._paused or len(self._task_processes) >= self.max_task_processes:
                return None

            schedule_execution = self._schedule_executions[schedule_id]

            try:
                schedule = self._schedules[schedule_id]
            except KeyError:
                # The schedule has been deleted
                if not schedule_execution.task_processes:
                    del self._schedule_executions[schedule_id]
                continue

            if schedule.exclusive and schedule_execution.task_processes:
                continue

            # next_start_time is None when repeat is None until the
            # task completes, at which time schedule_execution is removed
            next_start_time = schedule_execution.next_start_time
            if not next_start_time and not schedule_execution.start_now:
                if not schedule_execution.task_processes:
                    del self._schedule_executions[schedule_id]
                continue

            right_time = time.time() >= next_start_time

            if right_time or schedule_execution.start_now:
                # Start a task

                if not right_time:
                    # Manual start - don't change next_start_time
                    pass
                elif schedule.exclusive:
                    # Exclusive tasks won't start again until they terminate
                    # Or the schedule doesn't repeat
                    next_start_time = None
                else:
                    # _schedule_next_task alters next_start_time
                    self._schedule_next_task(schedule)
                    next_start_time = schedule_execution.next_start_time

                await self._start_task(schedule)

                # Queued manual execution is ignored when it was
                # already time to run the task. The task doesn't
                # start twice even when nonexclusive.
                # The choice to put this after "await" above was
                # deliberate. The above "await" could have allowed
                # queue_task() to run. The following line
                # will undo that because, after all, the task started.
                schedule_execution.start_now = False

            # Keep track of the earliest next_start_time
            if next_start_time and (earliest_start_time is None or
                                    earliest_start_time > next_start_time):
                earliest_start_time = next_start_time

        return earliest_start_time

    def _schedule_next_timed_task(self, schedule, schedule_execution, current_dt):
        """Handle daylight savings time transitions.
           Assume 'repeat' is not null.

        """
        if schedule.repeat_seconds < self._DAY_SECONDS:
            # If repeat is less than a day, use the current hour.
            # Ignore the hour specified in the schedule's time.
            dt = datetime.datetime(
                year=current_dt.year,
                month=current_dt.month,
                day=current_dt.day,
                hour=current_dt.hour,
                minute=schedule.time.minute,
                second=schedule.time.second)

            if current_dt.time() > schedule.time:
                # It's already too late. Try for an hour later.
                dt += self._ONE_HOUR
        else:
            dt = datetime.datetime(
                year=current_dt.year,
                month=current_dt.month,
                day=current_dt.day,
                hour=schedule.time.hour,
                minute=schedule.time.minute,
                second=schedule.time.second)

            if current_dt.time() > schedule.time:
                # It's already too late. Try for tomorrow
                dt += self._ONE_DAY

        # Advance to the correct day if specified
        if schedule.day:
            while dt.isoweekday() != schedule.day:
                dt += self._ONE_DAY

        schedule_execution.next_start_time = time.mktime(dt.timetuple())

    def _schedule_first_task(self, schedule, current_time):
        """Determines the time when a task for a schedule will start.

        Args:
            schedule: The schedule to consider

            current_time:
                Epoch time to use as the current time when determining
                when to schedule tasks

        """
        try:
            schedule_execution = self._schedule_executions[schedule.id]
        except KeyError:
            schedule_execution = self._ScheduleExecution()
            self._schedule_executions[schedule.id] = schedule_execution

        if schedule.type == self._ScheduleType.INTERVAL:
            advance_seconds = schedule.repeat_seconds

            # When modifying a schedule, this is imprecise if the
            # schedule is exclusive and a task is running. When the
            # task finishes, next_start_time will be incremented
            # by at least schedule.repeat, thus missing the interval at
            # start_time + advance_seconds. Fixing this required an if statement
            # in _schedule_next_task. Search for AVOID_ALTER_NEXT_START

            if advance_seconds:
                advance_seconds *= max([1, math.ceil(
                    (current_time - self._start_time) / advance_seconds)])
            else:
                advance_seconds = 0

            schedule_execution.next_start_time = self._start_time + advance_seconds
        elif schedule.type == self._ScheduleType.TIMED:
            self._schedule_next_timed_task(
                schedule,
                schedule_execution,
                datetime.datetime.fromtimestamp(current_time))
        elif schedule.type == self._ScheduleType.STARTUP:
            schedule_execution.next_start_time = current_time

        self._logger.info(
            "Scheduled task for schedule '%s' to start at %s", schedule.name,
            datetime.datetime.fromtimestamp(schedule_execution.next_start_time))

    def _schedule_next_task(self, schedule)->None:
        """Computes the next time to start a task for a schedule.

        This method is called only for schedules that have repeat != None.

        For nonexclusive schedules, this method is called after starting
        a task automatically (it is not called when a task is started
        manually).

        For exclusive schedules, this method is called after the task
        has completed.

        """
        schedule_execution = self._schedule_executions[schedule.id]
        advance_seconds = schedule.repeat_seconds

        if self._paused or advance_seconds is None:
            schedule_execution.next_start_time = None
            self._logger.info(
                "Tasks will no longer execute for schedule '%s'", schedule.name)
            return

        now = time.time()

        if schedule.exclusive and now < schedule_execution.next_start_time:
            # The task was started manually
            # Or the schedule was modified after the task started (AVOID_ALTER_NEXT_START)
            return

        if advance_seconds:
            advance_seconds *= max([1, math.ceil(
                (now - schedule_execution.next_start_time) / advance_seconds)])

            if schedule.type == self._ScheduleType.TIMED:
                # Handle daylight savings time transitions
                next_dt = datetime.datetime.fromtimestamp(schedule_execution.next_start_time)
                next_dt += datetime.timedelta(seconds=advance_seconds)

                if schedule.day is not None and next_dt.isoweekday() != schedule.day:
                    # Advance to the next matching day
                    next_dt = datetime.datetime(year=next_dt.year,
                                                month=next_dt.month,
                                                day=next_dt.day)
                    self._schedule_next_timed_task(schedule, schedule_execution, next_dt)
                else:
                    schedule_execution.next_start_time = time.mktime(next_dt.timetuple())
            else:
                # Interval schedule
                schedule_execution.next_start_time += advance_seconds

            self._logger.info(
                "Scheduled task for schedule '%s' to start at %s", schedule.name,
                datetime.datetime.fromtimestamp(schedule_execution.next_start_time))

    async def _get_process_scripts(self):
        query = sa.select([self._scheduled_processes_tbl.c.name,
                           self._scheduled_processes_tbl.c.script])
        query.select_from(self._scheduled_processes_tbl)

        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    self._process_scripts[row.name] = row.script

    async def _mark_tasks_interrupted(self):
        """Any task with a NULL end_time is set to interrupted"""
        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                await conn.execute(
                    self._tasks_tbl.update().where(
                        self._tasks_tbl.c.end_time is None).values(
                            state=int(Task.State.INTERRUPTED),
                            end_time=datetime.datetime.now()))

    async def _get_schedules(self):
        # TODO: Get processes first, then add to Schedule
        query = sa.select([self._schedules_tbl.c.id,
                           self._schedules_tbl.c.schedule_name,
                           self._schedules_tbl.c.schedule_type,
                           self._schedules_tbl.c.schedule_time,
                           self._schedules_tbl.c.schedule_day,
                           self._schedules_tbl.c.schedule_interval,
                           self._schedules_tbl.c.exclusive,
                           self._schedules_tbl.c.process_name])

        query.select_from(self._schedules_tbl)

        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    interval = row.schedule_interval

                    repeat_seconds = None
                    if interval is not None:
                        repeat_seconds = interval.total_seconds()

                    schedule = self._ScheduleRow(
                                        id=row.id,
                                        name=row.schedule_name,
                                        type=row.schedule_type,
                                        day=row.schedule_day,
                                        time=row.schedule_time,
                                        repeat=interval,
                                        repeat_seconds=repeat_seconds,
                                        exclusive=row.exclusive,
                                        process_name=row.process_name)

                    # TODO: Move this to _add_schedule to check for errors
                    self._schedules[row.id] = schedule
                    self._schedule_first_task(schedule, self._start_time)

    async def _read_storage(self):
        """Reads schedule information from the storage server"""
        await self._get_process_scripts()
        await self._get_schedules()

    def _resume_check_schedules(self):
        """Wakes up :meth:`_main_loop` so that
        :meth:`_check_schedules` will be called the next time 'await'
        is invoked.

        """
        if self._main_sleep_task:
            try:
                self._main_sleep_task.cancel()
                self._main_sleep_task = None
            except RuntimeError:
                self._check_processes_pending = True
        else:
            self._check_processes_pending = True

    async def _main_loop(self):
        """Main loop for the scheduler"""
        # TODO: log exception here or add an exception handler in asyncio

        while True:
            next_start_time = await self._check_schedules()

            if self._paused:
                break

            # Determine how long to sleep
            if self._check_processes_pending:
                self._check_processes_pending = False
                sleep_seconds = 0
            elif next_start_time is None:
                sleep_seconds = self._MAX_SLEEP
            else:
                sleep_seconds = next_start_time - time.time()

            if sleep_seconds > 0:
                self._logger.info("Sleeping for %s seconds", sleep_seconds)
                self._main_sleep_task = asyncio.ensure_future(asyncio.sleep(sleep_seconds))

                try:
                    await self._main_sleep_task
                    self._main_sleep_task = None
                except asyncio.CancelledError:
                    self._logger.debug("Main loop awakened")

    @staticmethod
    async def populate_test_data():
        """Delete all schedule-related tables and insert processes for testing"""
        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                await conn.execute('delete from foglamp.tasks')
                await conn.execute('delete from foglamp.schedules')
                await conn.execute('delete from foglamp.scheduled_processes')
                await conn.execute(
                    '''insert into foglamp.scheduled_processes(name, script)
                    values('sleep1', '["sleep", "1"]')''')
                await conn.execute(
                    '''insert into foglamp.scheduled_processes(name, script)
                    values('sleep10', '["sleep", "10"]')''')
                await conn.execute(
                    '''insert into foglamp.scheduled_processes(name, script)
                    values('sleep30', '["sleep", "30"]')''')
                await conn.execute(
                    '''insert into foglamp.scheduled_processes(name, script)
                    values('sleep5', '["sleep", "5"]')''')

    async def save_schedule(self, schedule: Schedule):
        """Creates or update a schedule

        Args:
            schedule:
                The id can be None, in which case a new id will be generated

        Raises:
            NotReadyError: The scheduler is not ready for requests
        """
        if self._paused or not self._ready:
            raise NotReadyError()

        schedule_type = None
        day = None
        schedule_time = None

        # TODO: verify schedule object (day, etc)

        if isinstance(schedule, IntervalSchedule):
            schedule_type = self._ScheduleType.INTERVAL
        elif isinstance(schedule, StartUpSchedule):
            schedule_type = self._ScheduleType.STARTUP
        elif isinstance(schedule, TimedSchedule):
            schedule_type = self._ScheduleType.TIMED
            schedule_time = schedule.time
            day = schedule.day
        elif isinstance(schedule, ManualSchedule):
            schedule_type = self._ScheduleType.MANUAL

        prev_schedule_row = None

        if schedule.schedule_id is None:
            is_new_schedule = True
            schedule.schedule_id = uuid.uuid4()
        else:
            try:
                prev_schedule_row = self._schedules[schedule.schedule_id]
                is_new_schedule = False
            except KeyError:
                is_new_schedule = True

        if not is_new_schedule:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    result = await conn.execute(
                        self._schedules_tbl.update().where(
                            self._schedules_tbl.c.id == str(schedule.schedule_id)).values(
                            schedule_name=schedule.name,
                            schedule_interval=schedule.repeat,
                            schedule_day=day,
                            schedule_time=schedule_time,
                            exclusive=schedule.exclusive,
                            process_name=schedule.process_name
                        ))

                    if result.rowcount == 0:
                        is_new_schedule = True

        if is_new_schedule:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    await conn.execute(self._schedules_tbl.insert().values(
                        id=str(schedule.schedule_id),
                        schedule_type=int(schedule_type),
                        schedule_name=schedule.name,
                        schedule_interval=schedule.repeat,
                        schedule_day=day,
                        schedule_time=schedule_time,
                        exclusive=schedule.exclusive,
                        process_name=schedule.process_name))

        # Added by: Amarendra
        # Required as saving a TIMED schedule
        if isinstance(schedule, TimedSchedule):
            sch_h, sch_m, sch_s = schedule_time.split(':')
            now = datetime.datetime.now()
            new_schedule_time = now.replace(hour=int(sch_h), minute=int(sch_m), second=int(sch_s), microsecond=0).time()
        else:
            new_schedule_time = None

        # TODO: Move this to _add_schedule for error checking
        repeat_seconds = None
        if schedule.repeat is not None:
            repeat_seconds = schedule.repeat.total_seconds()

        schedule_row = self._ScheduleRow(
                                id=str(schedule.schedule_id),
                                name=schedule.name,
                                type=schedule_type,
                                time=new_schedule_time,
                                day=day,
                                repeat=schedule.repeat,
                                repeat_seconds=repeat_seconds,
                                exclusive=schedule.exclusive,
                                process_name=schedule.process_name)

        self._schedules[str(schedule.schedule_id)] = schedule_row

        # Did the schedule change in a way that will affect task scheduling?

        if schedule_type in [self._ScheduleType.INTERVAL,
                             self._ScheduleType.TIMED] and (
                is_new_schedule or
                prev_schedule_row.time != schedule_row.time or
                prev_schedule_row.day != schedule_row.day or
                prev_schedule_row.repeat_seconds != schedule_row.repeat_seconds or
                prev_schedule_row.exclusive != schedule_row.exclusive):
            self._schedule_first_task(schedule_row, time.time())
            self._resume_check_schedules()

    async def delete_schedule(self, schedule_id: uuid.UUID):
        """Deletes a schedule

        Args:
            schedule_id

        Raises:
            ScheduleNotFoundError

            NotReadyError
        """
        if not self._ready:
            raise NotReadyError()

        # TODO: Inspect race conditions with _set_first
        try:
            del self._schedules[schedule_id]
        except KeyError:
            raise ScheduleNotFoundError(schedule_id)

        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                await conn.execute(self._schedules_tbl.delete().where(
                    self._schedules_tbl.c.id == str(schedule_id)))

    @classmethod
    def _schedule_row_to_schedule(cls,
                                  schedule_id: uuid.UUID,
                                  schedule_row: _ScheduleRow) -> Schedule:
        schedule_type = schedule_row.type

        if schedule_type == cls._ScheduleType.STARTUP:
            schedule = StartUpSchedule()
        elif schedule_type == cls._ScheduleType.TIMED:
            schedule = TimedSchedule()
        elif schedule_type == cls._ScheduleType.INTERVAL:
            schedule = IntervalSchedule()
        elif schedule_type == cls._ScheduleType.MANUAL:
            schedule = ManualSchedule()
        else:
            raise ValueError("Unknown schedule type {}", schedule_type)

        schedule.schedule_id = schedule_id
        schedule.type = schedule_type
        schedule.exclusive = schedule_row.exclusive
        schedule.name = schedule_row.name
        schedule.process_name = schedule_row.process_name
        schedule.repeat = schedule_row.repeat

        if schedule_type == cls._ScheduleType.TIMED:
            schedule.day = schedule_row.day
            schedule.time = schedule_row.time
        else:
            schedule.day = None
            schedule.time = None

        return schedule

    async def get_scheduled_processes(self) -> List[ScheduledProcess]:
        """Retrieves all rows from the scheduled_processes table
        """
        if not self._ready:
            raise NotReadyError()

        processes = []

        for (name, script) in self._process_scripts.items():
            process = ScheduledProcess()
            process.name = name
            process.script = script
            processes.append(process)

        return processes

    async def get_schedules(self) -> List[Schedule]:
        """Retrieves all schedules
        """
        if not self._ready:
            raise NotReadyError()

        schedules = []

        for (schedule_id, schedule_row) in self._schedules.items():
            schedules.append(self._schedule_row_to_schedule(schedule_id, schedule_row))

        return schedules

    async def get_schedule(self, schedule_id: uuid.UUID) -> Schedule:
        """Retrieves a schedule from its id

        Raises:
            ScheduleNotFoundException
        """
        if not self._ready:
            raise NotReadyError()

        try:
            schedule_row = self._schedules[schedule_id]
        except KeyError:
            raise ScheduleNotFoundError(schedule_id)

        return self._schedule_row_to_schedule(schedule_id, schedule_row)

    async def get_running_tasks(self) -> List[Task]:
        """Retrieves a list of all tasks that are currently running

        Returns:
            An empty list if no tasks are running

            A list of Task objects
        """
        if not self._ready:
            raise NotReadyError()

        tasks = []

        for (task_id, task_process) in self._task_processes.items():
            task = Task()
            task.task_id = task_id
            task.process_name = task_process.schedule.process_name
            task.state = Task.State.RUNNING
            if task_process.cancel_requested is not None:
                task.cancel_requested = (
                    datetime.datetime.fromtimestamp(task_process.cancel_requested))
            task.start_time = datetime.datetime.fromtimestamp(task_process.start_time)
            tasks.append(task)

        return tasks

    async def get_task(self, task_id: uuid.UUID)->Task:
        """Retrieves a task given its id"""
        query = sa.select([self._tasks_tbl.c.id,
                           self._tasks_tbl.c.process_name,
                           self._tasks_tbl.c.state,
                           self._tasks_tbl.c.start_time,
                           self._tasks_tbl.c.end_time,
                           self._tasks_tbl.c.exit_code,
                           self._tasks_tbl.c.reason])

        query.select_from(self._tasks_tbl)

        query.where(self._tasks_tbl.c.id == task_id)

        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    task = Task()
                    task.task_id = row.id
                    task.state = Task.State(row.state)
                    task.start_time = row.start_time
                    task.process_name = row.process_name
                    task.end_time = row.end_time
                    task.exit_code = row.exit_code
                    task.reason = row.reason

                    return task

        raise TaskNotFoundError(task_id)

    async def get_tasks(self, limit: int)->List[Task]:
        """Retrieves tasks

        The result set is ordered by start_time descending

        Args:
            limit: Return at most this number of rows
        """
        query = sa.select([self._tasks_tbl.c.id,
                           self._tasks_tbl.c.process_name,
                           self._tasks_tbl.c.state,
                           self._tasks_tbl.c.start_time,
                           self._tasks_tbl.c.end_time,
                           self._tasks_tbl.c.exit_code,
                           self._tasks_tbl.c.reason]).select_from(self._tasks_tbl).order_by(
                                self._tasks_tbl.c.start_time.desc()).limit(limit)

        tasks = []

        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(query):
                    task = Task()
                    task.task_id = row.id
                    task.state = Task.State(row.state)
                    task.start_time = row.start_time
                    task.process_name = row.process_name
                    task.end_time = row.end_time
                    task.exit_code = row.exit_code
                    task.reason = row.reason

                    tasks.append(task)
        return tasks

    async def cancel_task(self, task_id: uuid.UUID)->None:
        """Cancels a running task

        Args:

        Raises:
            NotReadyError

            TaskNotRunningError
        """
        if self._paused or not self._ready:
            raise NotReadyError()

        try:
            task_process = self._task_processes[task_id]  # _TaskProcess
        except KeyError:
            raise TaskNotRunningError(task_id)

        if task_process.cancel_requested:
            # TODO: Allow after some period of time has elapsed
            raise DuplicateRequestError()

        # TODO: FOGL-356 track the last time TERM was sent to each task
        task_process.cancel_requested = time.time()

        schedule = task_process.schedule

        self._logger.info(
            "Stopping process: Schedule '%s' process '%s' task %s pid %s\n%s",
            schedule.name,
            schedule.process_name,
            task_id,
            task_process.process.pid,
            self._process_scripts[schedule.process_name])

        try:
            task_process.process.terminate()
        except ProcessLookupError:
            pass  # Process has terminated

    async def start(self):
        """Starts the scheduler

        When this method returns, an asyncio task is
        scheduled that starts tasks and monitors their subprocesses. This class
        does not use threads (tasks run as subprocesses).

        Raises:
            NotReadyError: Scheduler was stopped
        """
        if self._paused or self._schedule_executions is None:
            raise NotReadyError("The scheduler was stopped and can not be restarted")

        if self._ready:
            return

        if self._start_time:
            raise NotReadyError("The scheduler is starting")

        self._logger.info("Starting")

        self._start_time = time.time()

        # Hard-code storage server:
        # wait self._start_startup_task(self._schedules['storage'])
        # Then wait for it to start.

        await self._mark_tasks_interrupted()
        await self._read_storage()

        self._ready = True

        self._main_loop_task = asyncio.ensure_future(self._main_loop())
