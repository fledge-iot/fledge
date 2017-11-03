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
from typing import Iterable, List, Tuple, Union
import os

import aiopg.sa
import sqlalchemy
from sqlalchemy.dialects import postgresql as pg_types

from foglamp import logger
from foglamp import configuration_manager
from foglamp.microservice_management.service_registry.instance import Service

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
_CONNECTION_STRING = "dbname='foglamp' user='foglamp'"

try:
  snap_user_common = os.environ['SNAP_USER_COMMON']
  unix_socket_dir = "{}/tmp/".format(snap_user_common)
  _CONNECTION_STRING = _CONNECTION_STRING + " host='" + unix_socket_dir + "'"
except KeyError:
  pass


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


# Forward declare
class LogicExpr:
    pass


class Where(object):
    @staticmethod
    def and_(*argv)->LogicExpr:  # This should be Tuple[Query] but Python doesn't allow it
        return LogicExpr(LogicExpr.Operator.AND, argv)

    @staticmethod
    def or_(*argv)->LogicExpr:  # This should be Tuple[Query] but Python doesn't allow it
        return LogicExpr(LogicExpr.Operator.OR, argv)


class WhereExpr(object):
    def and_(self, *argv)->LogicExpr:
        return LogicExpr(LogicExpr.Operator.AND, argv, self)

    def or_(self, *argv)->LogicExpr:
        return LogicExpr(LogicExpr.Operator.OR, argv, self)

    def __and__(self, other):
        return Where.and_(self, other)

    def __or__(self, other):
        return Where.or_(self, other)

    @property
    def query(self):
        raise TypeError("Abstract method called")


class LogicExpr(WhereExpr):
    __slots__ = ['_and_expr', '_queries', '_operator']

    class Operator(IntEnum):
        """Enumeration for tasks.task_state"""
        OR = 1
        AND = 2

    def __init__(self, operator: Operator, argv, and_expr: WhereExpr = None):
        self._and_expr = and_expr
        self._operator = operator
        self._queries = argv  # type: Tuple[WhereExpr]

    @property
    def query(self):
        queries = []

        for query_item in self._queries:
            queries.append(query_item.query)

        if self._operator == self.Operator.AND:
            if self._and_expr is not None:
                return sqlalchemy.and_(self._and_expr.query, *queries)
            return sqlalchemy.and_(*queries)
        elif self._operator == self.Operator.OR:
            if self._and_expr is not None:
                return sqlalchemy.and_(self._and_expr.query, sqlalchemy.or_(*queries))
            return sqlalchemy.or_(*queries)
        else:
            raise ValueError("Invalid operator: {}".format(int(self._operator)))


class CompareExpr(WhereExpr):
    __slots__ = ['_column', '_operator', '_value']

    class Operator(IntEnum):
        """Enumeration for tasks.task_state"""
        NE = 1
        EQ = 2
        LT = 3
        LE = 4
        GT = 5
        GE = 6
        LIKE = 7
        IN = 8

    def __init__(self, column: sqlalchemy.Column, operator: Operator, value):
        self._column = column
        self._operator = operator
        self._value = value

    @property
    def query(self):
        if self._operator == self.Operator.NE:
            return self._column != self._value
        if self._operator == self.Operator.EQ:
            return self._column == self._value
        if self._operator == self.Operator.LT:
            return self._column < self._value
        if self._operator == self.Operator.LE:
            return self._column <= self._value
        if self._operator == self.Operator.GT:
            return self._column > self._value
        if self._operator == self.Operator.GE:
            return self._column >= self._value
        if self._operator == self.Operator.LIKE:
            return self._column.like(self._value)
        if self._operator == self.Operator.IN:
            return self._column.in_(self._value)

        raise ValueError("Invalid operator: {}".format(int(self._operator)))


class AttributeDesc:  # Forward declare
    pass


class Attribute(object):
    __slots__ = ['_column', '_desc']

    def __init__(self, column: sqlalchemy.Column):
        self._column = column
        self._desc = AttributeDesc(column)

    def in_(self, *argv):
        return CompareExpr(self._column, CompareExpr.Operator.IN, argv)

    def like(self, value):
        return CompareExpr(self._column, CompareExpr.Operator.LIKE, value)

    def __lt__(self, value):
        return CompareExpr(self._column, CompareExpr.Operator.LT, value)

    def __le__(self, value):
        return CompareExpr(self._column, CompareExpr.Operator.LE, value)

    def __eq__(self, value):
        return CompareExpr(self._column, CompareExpr.Operator.EQ, value)

    def __ne__(self, value):
        return CompareExpr(self._column, CompareExpr.Operator.NE, value)

    def __gt__(self, value):
        return CompareExpr(self._column, CompareExpr.Operator.GT, value)

    def __ge__(self, value):
        return CompareExpr(self._column, CompareExpr.Operator.GE, value)

    @property
    def column(self)->sqlalchemy.Column:
        return self._column

    @property
    def desc(self)->AttributeDesc:
        return self._desc


class AttributeDesc(Attribute):
    def __init__(self, column: sqlalchemy.Column):
        self._column = column.desc()


class Task(object):
    """A task represents an operating system process"""

    class State(IntEnum):
        """Enumeration for tasks.task_state"""
        RUNNING = 1
        COMPLETE = 2
        CANCELED = 3
        INTERRUPTED = 4

    # Class attributes
    attr = collections.namedtuple('TaskAttributes', ['state', 'process_name', 'start_time',
                                  'end_time', 'exit_code'])

    __slots__ = ['task_id', 'process_name', 'state', 'cancel_requested', 'start_time',
                 'end_time', 'state', 'exit_code', 'reason']

    def __init__(self):
        # Instance attributes
        self.task_id = None  # type: uuid.UUID
        """Unique identifier"""
        self.process_name = None  # type: str
        self.reason = None  # type: str
        self.state = None  # type: Task.State
        self.cancel_requested = None  # type: datetime.datetime
        self.start_time = None  # type: datetime.datetime
        self.end_time = None  # type: datetime.datetime
        self.exit_code = None  # type: int

    @classmethod
    def init(cls, tasks_tbl: sqlalchemy.Table)->None:
        """Initializes class attributes"""
        cls.attr.state = Attribute(tasks_tbl.c.state)
        cls.attr.process_name = Attribute(tasks_tbl.c.process_name)
        cls.attr.start_time = Attribute(tasks_tbl.c.start_time)
        cls.attr.end_time = Attribute(tasks_tbl.c.end_time)
        cls.attr.exit_code = Attribute(tasks_tbl.c.end_time)


class ScheduledProcess(object):
    """Represents a program that a Task can run"""

    __slots__ = ['name', 'script']

    def __init__(self):
        self.name = None  # type: str
        """Unique identifier"""
        self.script = None  # type: List[ str ]


class Schedule(object):
    class Type(IntEnum):
        """Enumeration for schedules.schedule_type"""
        STARTUP = 1
        TIMED = 2
        INTERVAL = 3
        MANUAL = 4

    """Schedule base class"""
    __slots__ = ['schedule_id', 'name', 'process_name', 'exclusive', 'repeat', 'schedule_type']

    def __init__(self, schedule_type: Type):
        self.schedule_id = None  # type: uuid.UUID
        self.name = None  # type: str
        self.exclusive = True
        self.repeat = None  # type: datetime.timedelta
        self.process_name = None  # type: str
        self.schedule_type = schedule_type  # type: Schedule.Type


class IntervalSchedule(Schedule):
    """Interval schedule"""
    def __init__(self):
        super().__init__(self.Type.INTERVAL)


class TimedSchedule(Schedule):
    """Timed schedule"""
    __slots__ = ['time', 'day']

    def __init__(self):
        super().__init__(self.Type.TIMED)
        self.time = None  # type: datetime.time
        self.day = None  # type: int
        """1 (Monday) to 7 (Sunday)"""


class ManualSchedule(Schedule):
    """A schedule that is run manually"""
    def __init__(self):
        super().__init__(self.Type.MANUAL)


class StartUpSchedule(Schedule):
    """A schedule that is run when the scheduler starts"""
    def __init__(self):
        super().__init__(self.Type.STARTUP)


class Scheduler(object):
    """FogLAMP Task Scheduler

    Starts and tracks 'tasks' that run periodically,
    start-up, and/or manually.

    Schedules specify when to start and restart Tasks. A Task
    is an operating system process. ScheduleProcesses
    specify process/command name and parameters.

    Most methods are coroutines and use the default
    event loop to create tasks.

    Usage:
        - Call :meth:`start`
        - Wait
        - Call :meth:`stop`
    """

    # TODO: Document the fields
    _ScheduleRow = collections.namedtuple('ScheduleRow', ['id', 'name', 'type', 'time', 'day',
                                                          'repeat', 'repeat_seconds', 'exclusive',
                                                          'process_name'])
    """Represents a row in the schedules table"""

    class _TaskProcess(object):
        """Tracks a running task with some flags"""
        __slots__ = ['task_id', 'process', 'cancel_requested', 'schedule', 'start_time']

        def __init__(self):
            self.task_id = None  # type: uuid.UUID
            self.process = None  # type: asyncio.subprocess.Process
            self.cancel_requested = None  # type: int
            """Epoch time when cancel was requested"""
            self.schedule = None  # Schedule._ScheduleRow
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
    _DEFAULT_MAX_RUNNING_TASKS = 50
    """Maximum number of running tasks allowed at any given time"""
    _DEFAULT_MAX_COMPLETED_TASK_AGE_DAYS = 30
    """Maximum age of rows in the task table that have finished, in days"""
    _DELETE_TASKS_LIMIT = 500
    """The maximum number of rows to delete in the tasks table in a single transaction"""

    _HOUR_SECONDS = 3600
    _DAY_SECONDS = 3600*24
    _WEEK_SECONDS = 3600*24*7
    _ONE_HOUR = datetime.timedelta(hours=1)
    _ONE_DAY = datetime.timedelta(days=1)

    _MAX_SLEEP = 9999999
    """When there is nothing to do, sleep for this number of seconds (forever)"""

    _STOP_WAIT_SECONDS = 5
    """Wait this number of seconds in :meth:`stop` for tasks to stop"""

    _PURGE_TASKS_FREQUENCY_SECONDS = _DAY_SECONDS
    """How frequently to purge the tasks table"""

    # Mostly constant class attributes
    _scheduled_processes_tbl = None  # type: sqlalchemy.Table
    _schedules_tbl = None  # type: sqlalchemy.Table
    _tasks_tbl = None  # type: sqlalchemy.Table
    _logger = None  # type: logging.Logger

    _core_management_host = None
    _core_management_port = None

    # TODO: Remove below '=None' after FOGL-521 is merged
    def __init__(self, core_management_host=None, core_management_port=None):
        """Constructor"""

        cls = Scheduler

        # Initialize class attributes

        if not cls._logger:
            cls._logger = logger.setup(__name__, level=20)
            # cls._logger = logger.setup(__name__, destination=logger.CONSOLE, level=logging.DEBUG)
            # cls._logger = logger.setup(__name__, level=logging.DEBUG)

        if not cls._core_management_port:
            cls._core_management_port = core_management_port
        if not cls._core_management_host:
            cls._core_management_host = core_management_host

        if cls._schedules_tbl is None:
            metadata = sqlalchemy.MetaData()

            cls._schedules_tbl = sqlalchemy.Table(
                'schedules',
                metadata,
                sqlalchemy.Column('id', pg_types.UUID),
                sqlalchemy.Column('schedule_name', sqlalchemy.types.VARCHAR(20)),
                sqlalchemy.Column('process_name', sqlalchemy.types.VARCHAR(20)),
                sqlalchemy.Column('schedule_type', sqlalchemy.types.SMALLINT),
                sqlalchemy.Column('schedule_time', sqlalchemy.types.TIME),
                sqlalchemy.Column('schedule_day', sqlalchemy.types.SMALLINT),
                sqlalchemy.Column('schedule_interval', sqlalchemy.types.Interval),
                sqlalchemy.Column('exclusive', sqlalchemy.types.BOOLEAN))

            cls._tasks_tbl = sqlalchemy.Table(
                'tasks',
                metadata,
                sqlalchemy.Column('id', pg_types.UUID),
                sqlalchemy.Column('process_name', sqlalchemy.types.VARCHAR(20)),
                sqlalchemy.Column('state', sqlalchemy.types.INT),
                sqlalchemy.Column('start_time', sqlalchemy.types.TIMESTAMP),
                sqlalchemy.Column('end_time', sqlalchemy.types.TIMESTAMP),
                sqlalchemy.Column('pid', sqlalchemy.types.INT),
                sqlalchemy.Column('exit_code', sqlalchemy.types.INT),
                sqlalchemy.Column('reason', sqlalchemy.types.VARCHAR(255)))

            Task.init(cls._tasks_tbl)

            cls._scheduled_processes_tbl = sqlalchemy.Table(
                'scheduled_processes',
                metadata,
                sqlalchemy.Column('name', pg_types.VARCHAR(20)),
                sqlalchemy.Column('script', pg_types.JSONB))

        # Instance attributes
        self._engine = None  # type: aiopg.sa.Engine
        """Database connection pool"""
        self._ready = False
        """True when the scheduler is ready to accept API calls"""
        self._start_time = None  # type: int
        """When the scheduler started"""
        self._max_running_tasks = None  # type: int
        """Maximum number of tasks that can execute at any given time"""
        self._paused = False
        """When True, the scheduler will not start any new tasks"""
        self._process_scripts = dict()
        """Dictionary of scheduled_processes.name to script"""
        self._schedules = dict()
        """Dictionary of schedules.id to _ScheduleRow"""
        self._schedule_executions = dict()
        """Dictionary of schedules.id to _ScheduleExecution"""
        self._task_processes = dict()
        """Dictionary of tasks.id to _TaskProcess"""
        self._check_processes_pending = False
        """bool: True when request to run check_processes"""
        self._scheduler_loop_task = None  # type: asyncio.Task
        """Task for :meth:`_scheduler_loop`, to ensure it has finished"""
        self._scheduler_loop_sleep_task = None  # type: asyncio.Task
        """Task for asyncio.sleep used by :meth:`_scheduler_loop`"""
        self.current_time = None  # type: int
        """Time to use when determining when to start tasks, for testing"""
        self._last_task_purge_time = None  # type: int
        """When the tasks table was last purged"""
        self._max_completed_task_age = None  # type: datetime.timedelta
        """Delete finished task rows when they become this old"""
        self._purge_tasks_task = None  # type: asyncio.Task
        """asynico task for :meth:`purge_tasks`, if scheduled to run"""

    @property
    def max_completed_task_age(self)->datetime.timedelta:
        return self._max_completed_task_age

    @max_completed_task_age.setter
    def max_completed_task_age(self, value: datetime.timedelta)->None:
        if not isinstance(value, datetime.timedelta):
            raise TypeError("value must be a datetime.timedelta")
        self._max_completed_task_age = value

    @property
    def max_running_tasks(self)->int:
        """Returns the maximum number of tasks that can run at any given time
        """
        return self._max_running_tasks

    @max_running_tasks.setter
    def max_running_tasks(self, value: int)->None:
        """Alters the maximum number of tasks that can run at any given time

        Use 0 or a negative value to suspend task creation
        """
        self._max_running_tasks = value
        self._resume_check_schedules()

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
            # Wait for tasks purge task to finish
            self._paused = True
            if self._purge_tasks_task is not None:
                try:
                    await self._purge_tasks_task
                except Exception:
                    self._logger.exception('An exception was raised by Scheduler._purge_tasks')

            self._resume_check_schedules()

            # Stop the main loop
            try:
                await self._scheduler_loop_task
            except Exception:
                self._logger.exception('An exception was raised by Scheduler._scheduler_loop')
            self._scheduler_loop_task = None

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

        # Wait for all processes to stop
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

        if self._engine is not None:
            try:
                self._engine.close()
            except Exception:
                self._logger.exception('Unable to close the database connection pool')
            finally:
                self._engine = None

        return True

    async def _get_connection_pool(self) -> aiopg.sa.Engine:
        """Returns a database connection pool object"""
        if self._engine is None:
            self._engine = await aiopg.sa.create_engine(_CONNECTION_STRING)
        return self._engine

    async def _start_task(self, schedule: _ScheduleRow) -> None:
        """Starts a task process

        Raises:
            EnvironmentError: If the process could not start
        """

        # This check is necessary only if significant time can elapse between "await" and
        # the start of the awaited coroutine.
        args = self._process_scripts[schedule.process_name]

        # add core management host and port to process script args
        args_to_exec = args.copy()
        args_to_exec.append("--port={}".format(self._core_management_port))
        args_to_exec.append("--address=127.0.0.1")
        args_to_exec.append("--name={}".format(schedule.process_name))

        task_process = self._TaskProcess()
        task_process.start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(*args_to_exec)
        except EnvironmentError:
            self._logger.exception(
                "Unable to start schedule '%s' process '%s'\n%s".format(
                    schedule.name, schedule.process_name, args_to_exec))
            raise

        task_id = uuid.uuid4()
        task_process.process = process
        task_process.schedule = schedule
        task_process.task_id = task_id

        self._task_processes[task_id] = task_process
        self._schedule_executions[schedule.id].task_processes[task_id] = task_process

        self._logger.info(
            "Process started: Schedule '%s' process '%s' task %s pid %s, %s running tasks\n%s",
            schedule.name, schedule.process_name, task_id, process.pid,
            len(self._task_processes), args_to_exec)

        # Startup tasks are not tracked in the tasks table
        if schedule.type != Schedule.Type.STARTUP:
            # The task row needs to exist before the completion handler runs
            insert = self._tasks_tbl.insert()
            insert = insert.values(id=str(task_id),
                                   pid=(self._schedule_executions[schedule.id].
                                        task_processes[task_id].process.pid),
                                   process_name=schedule.process_name,
                                   state=int(Task.State.RUNNING),
                                   start_time=datetime.datetime.now())

            self._logger.debug('Database command: %s', insert)

            try:
                async with (await self._get_connection_pool()).acquire() as conn:
                    await conn.execute(insert)
            except Exception:
                self._logger.exception('Insert failed: %s', insert)
                # The process has started. Regardless of this error it must be waited on.

        asyncio.ensure_future(self._wait_for_task_completion(task_process))

    async def _wait_for_task_completion(self, task_process: _TaskProcess)->None:
        exit_code = await task_process.process.wait()

        schedule = task_process.schedule

        self._logger.info(
            "Process terminated: Schedule '%s' process '%s' task %s pid %s exit %s,"
            " %s running tasks\n%s",
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

        if schedule.type != Schedule.Type.STARTUP:
            if exit_code < 0 and task_process.cancel_requested:
                state = Task.State.CANCELED
            else:
                state = Task.State.COMPLETE

            update = self._tasks_tbl.update()
            update = update.where(self._tasks_tbl.c.id == str(task_process.task_id))
            # TODO Populate reason?
            update = update.values(exit_code=exit_code,
                                   state=int(state),
                                   end_time=datetime.datetime.now())

            self._logger.debug('Database command: %s', update)

            # Update the task's status
            try:
                async with (await self._get_connection_pool()).acquire() as conn:
                    result = await conn.execute(update)

                    if result.rowcount == 0:
                        self._logger.warning('Task %s not found. Unable to update its status.',
                                             task_process.task_id)
            except Exception:
                self._logger.exception('Update failed: %s', update)
                # Must keep going!

        # Due to maximum running tasks reached, it is necessary to
        # look for schedules that are ready to run even if there
        # are only manual tasks waiting
        # TODO Do this only if len(_task_processes) >= max_processes or
        # an exclusive task finished and ( start_now or schedule.repeats )
        self._resume_check_schedules()

        # This must occur after all awaiting. The size of _task_processes
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
            if self._paused or len(self._task_processes) >= self._max_running_tasks:
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

            if next_start_time and not schedule_execution.start_now:
                now = self.current_time if self.current_time else time.time()
                right_time = now >= next_start_time
            else:
                right_time = False

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
        if schedule.repeat_seconds is not None and schedule.repeat_seconds < self._DAY_SECONDS:
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
        if schedule.type == Schedule.Type.MANUAL:
            return
                
        try:
            schedule_execution = self._schedule_executions[schedule.id]
        except KeyError:
            schedule_execution = self._ScheduleExecution()
            self._schedule_executions[schedule.id] = schedule_execution

        if schedule.type == Schedule.Type.INTERVAL:
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
        elif schedule.type == Schedule.Type.TIMED:
            self._schedule_next_timed_task(
                schedule,
                schedule_execution,
                datetime.datetime.fromtimestamp(current_time))
        elif schedule.type == Schedule.Type.STARTUP:
            schedule_execution.next_start_time = current_time

        if self._logger.isEnabledFor(logging.INFO):
            self._logger.info(
                "Scheduled task for schedule '%s' to start at %s", schedule.name,
                datetime.datetime.fromtimestamp(schedule_execution.next_start_time))

    def _schedule_next_task(self, schedule)->None:
        """Computes the next time to start a task for a schedule.

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

        if (schedule.exclusive and schedule_execution.next_start_time and
                now < schedule_execution.next_start_time):
            # The task was started manually
            # Or the schedule was modified after the task started (AVOID_ALTER_NEXT_START)
            return

        if advance_seconds:
            advance_seconds *= max([1, math.ceil(
                (now - schedule_execution.next_start_time) / advance_seconds)])

            if schedule.type == Schedule.Type.TIMED:
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
                if schedule.type == Schedule.Type.MANUAL:
                    schedule_execution.next_start_time = time.time()
                schedule_execution.next_start_time += advance_seconds

            self._logger.info(
                "Scheduled task for schedule '%s' to start at %s", schedule.name,
                datetime.datetime.fromtimestamp(schedule_execution.next_start_time))

    async def _get_process_scripts(self):
        query = sqlalchemy.select([self._scheduled_processes_tbl.c.name,
                                  self._scheduled_processes_tbl.c.script])

        query.select_from(self._scheduled_processes_tbl)

        self._logger.debug('Database command: %s', query)

        try:
            async with (await self._get_connection_pool()).acquire() as conn:
                async for row in conn.execute(query):
                    self._process_scripts[row.name] = row.script
        except Exception:
            self._logger.exception('Select failed: %s', query)
            raise

    async def _mark_tasks_interrupted(self):
        """The state for any task with a NULL end_time is set to interrupted"""
        update = self._tasks_tbl.update()
        update = update.where(self._tasks_tbl.c.end_time is None)
        update = update.values(state=int(Task.State.INTERRUPTED),
                               end_time=datetime.datetime.now())

        self._logger.debug('Database command: %s', update)

        try:
            async with (await self._get_connection_pool()).acquire() as conn:
                await conn.execute(update)
        except Exception:
            self._logger.exception('Update failed: %s', update)
            raise

    async def _get_schedules(self):
        # TODO: Get processes first, then add to Schedule
        query = sqlalchemy.select([self._schedules_tbl.c.id,
                                   self._schedules_tbl.c.schedule_name,
                                   self._schedules_tbl.c.schedule_type,
                                   self._schedules_tbl.c.schedule_time,
                                   self._schedules_tbl.c.schedule_day,
                                   self._schedules_tbl.c.schedule_interval,
                                   self._schedules_tbl.c.exclusive,
                                   self._schedules_tbl.c.process_name])

        query.select_from(self._schedules_tbl)

        self._logger.debug('Database command: %s', query)

        try:
            async with (await self._get_connection_pool()).acquire() as conn:
                async for row in conn.execute(query):
                    interval = row.schedule_interval

                    repeat_seconds = None
                    if interval is not None:
                        repeat_seconds = interval.total_seconds()

                    schedule_id = uuid.UUID(row.id)

                    schedule = self._ScheduleRow(
                                        id=schedule_id,
                                        name=row.schedule_name,
                                        type=row.schedule_type,
                                        day=row.schedule_day,
                                        time=row.schedule_time,
                                        repeat=interval,
                                        repeat_seconds=repeat_seconds,
                                        exclusive=row.exclusive,
                                        process_name=row.process_name)

                    self._schedules[schedule_id] = schedule
                    self._schedule_first_task(schedule, self._start_time)
        except Exception:
            self._logger.exception('Select failed: %s', query)
            raise

    async def _read_storage(self):
        """Reads schedule information from the storage server"""
        await self._get_process_scripts()
        await self._get_schedules()

    def _resume_check_schedules(self):
        """Wakes up :meth:`_scheduler_loop` so that
        :meth:`_check_schedules` will be called the next time 'await'
        is invoked.

        """
        if self._scheduler_loop_sleep_task:
            try:
                self._scheduler_loop_sleep_task.cancel()
                self._scheduler_loop_sleep_task = None
            except RuntimeError:
                self._check_processes_pending = True
        else:
            self._check_processes_pending = True

    async def _scheduler_loop(self):
        """Main loop for the scheduler"""
        # TODO: log exception here or add an exception handler in asyncio

        while True:
            next_start_time = await self._check_schedules()

            if self._paused:
                break

            self._check_purge_tasks()

            # Determine how long to sleep
            if self._check_processes_pending:
                self._check_processes_pending = False
                sleep_seconds = 0
            elif next_start_time:
                sleep_seconds = next_start_time - time.time()
            else:
                sleep_seconds = self._MAX_SLEEP

            if sleep_seconds > 0:
                self._logger.info("Sleeping for %s seconds", sleep_seconds)
                self._scheduler_loop_sleep_task = (
                    asyncio.ensure_future(asyncio.sleep(sleep_seconds)))

                try:
                    await self._scheduler_loop_sleep_task
                    self._scheduler_loop_sleep_task = None
                except asyncio.CancelledError:
                    self._logger.debug("Main loop awakened")
            else:
                # Relinquish control for each loop iteration to avoid starving
                # other coroutines
                await asyncio.sleep(0)

    async def populate_test_data(self):
        """Delete all schedule-related tables and insert processes for testing"""
        async with (await self._get_connection_pool()).acquire() as conn:
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

        # TODO should these checks be moved to the storage layer?
        if schedule.name is None or len(schedule.name) == 0:
            raise ValueError("name can not be empty")

        if schedule.repeat is not None and not isinstance(schedule.repeat, datetime.timedelta):
            raise ValueError('repeat must be of type datetime.time')

        if schedule.exclusive is None:
            raise ValueError('exclusive can not be None')

        if isinstance(schedule, TimedSchedule):
            schedule_time = schedule.time

            if schedule_time is not None and not isinstance(schedule_time, datetime.time):
                raise ValueError('time must be of type datetime.time')

            day = schedule.day

            # TODO Remove this check when the database has constraint
            if day is not None and (day < 1 or day > 7):
                raise ValueError('day must be between 1 and 7')
        else:
            day = None
            schedule_time = None

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
            update = self._schedules_tbl.update()
            update = update.where(self._schedules_tbl.c.id == str(schedule.schedule_id))
            update = update.values(schedule_name=schedule.name,
                                   schedule_type=int(schedule.schedule_type),
                                   schedule_interval=schedule.repeat,
                                   schedule_day=day,
                                   schedule_time=schedule_time,
                                   exclusive=schedule.exclusive,
                                   process_name=schedule.process_name)

            self._logger.debug('Database command: %s', update)

            try:
                async with (await self._get_connection_pool()).acquire() as conn:
                    result = await conn.execute(update)

                    if result.rowcount == 0:
                        is_new_schedule = True
            except Exception:
                self._logger.debug('Update failed: %s', update)
                raise

        if is_new_schedule:
            insert = self._schedules_tbl.insert()
            insert = insert.values(id=str(schedule.schedule_id),
                                   schedule_type=int(schedule.schedule_type),
                                   schedule_name=schedule.name,
                                   schedule_interval=schedule.repeat,
                                   schedule_day=day,
                                   schedule_time=schedule_time,
                                   exclusive=schedule.exclusive,
                                   process_name=schedule.process_name)

            self._logger.debug('Database command: %s', insert)

            try:
                async with (await self._get_connection_pool()).acquire() as conn:
                    await conn.execute(insert)
            except Exception:
                self._logger.exception('Insert failed: %s', insert)
                raise

        repeat_seconds = None
        if schedule.repeat is not None:
            repeat_seconds = schedule.repeat.total_seconds()

        schedule_row = self._ScheduleRow(
                                id=schedule.schedule_id,
                                name=schedule.name,
                                type=schedule.schedule_type,
                                time=schedule_time,
                                day=day,
                                repeat=schedule.repeat,
                                repeat_seconds=repeat_seconds,
                                exclusive=schedule.exclusive,
                                process_name=schedule.process_name)

        self._schedules[schedule.schedule_id] = schedule_row

        # Did the schedule change in a way that will affect task scheduling?
        if schedule.schedule_type in [Schedule.Type.INTERVAL, Schedule.Type.TIMED] and (
                is_new_schedule or
                prev_schedule_row.time != schedule_row.time or
                prev_schedule_row.day != schedule_row.day or
                prev_schedule_row.repeat_seconds != schedule_row.repeat_seconds or
                prev_schedule_row.exclusive != schedule_row.exclusive):

            now = self.current_time if self.current_time else time.time()
            self._schedule_first_task(schedule_row, now)
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

        delete = self._schedules_tbl.delete()
        delete = delete.where(self._schedules_tbl.c.id == str(schedule_id))

        self._logger.debug('Database command: %s', delete)

        try:
            async with (await self._get_connection_pool()).acquire() as conn:
                await conn.execute(self._schedules_tbl.delete().where(
                    self._schedules_tbl.c.id == str(schedule_id)))
        except Exception:
            self._logger.exception('Delete failed: %s', delete)
            raise

    @classmethod
    def _schedule_row_to_schedule(cls,
                                  schedule_id: uuid.UUID,
                                  schedule_row: _ScheduleRow) -> Schedule:
        schedule_type = schedule_row.type

        if schedule_type == Schedule.Type.STARTUP:
            schedule = StartUpSchedule()
        elif schedule_type == Schedule.Type.TIMED:
            schedule = TimedSchedule()
        elif schedule_type == Schedule.Type.INTERVAL:
            schedule = IntervalSchedule()
        elif schedule_type == Schedule.Type.MANUAL:
            schedule = ManualSchedule()
        else:
            raise ValueError("Unknown schedule type {}", schedule_type)

        schedule.schedule_id = schedule_id
        schedule.exclusive = schedule_row.exclusive
        schedule.name = schedule_row.name
        schedule.process_name = schedule_row.process_name
        schedule.repeat = schedule_row.repeat

        if schedule_type == Schedule.Type.TIMED:
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
        query = sqlalchemy.select([self._tasks_tbl.c.id,
                                   self._tasks_tbl.c.process_name,
                                   self._tasks_tbl.c.state,
                                   self._tasks_tbl.c.start_time,
                                   self._tasks_tbl.c.end_time,
                                   self._tasks_tbl.c.exit_code,
                                   self._tasks_tbl.c.reason])
        query.select_from(self._tasks_tbl)
        query = query.where(self._tasks_tbl.c.id == str(task_id))

        self._logger.debug('Database command: %s', query)

        try:
            async with (await self._get_connection_pool()).acquire() as conn:
                async for row in conn.execute(query):
                    task = Task()
                    task.task_id = uuid.UUID(row.id)
                    task.state = Task.State(row.state)
                    task.start_time = row.start_time
                    task.process_name = row.process_name
                    task.end_time = row.end_time
                    task.exit_code = row.exit_code
                    task.reason = row.reason

                    return task
        except Exception:
            self._logger.exception('Select failed: %s', query)
            raise

        raise TaskNotFoundError(task_id)

    async def get_tasks(self, limit: int = 100, offset: int = 0,
                        where: WhereExpr = None,
                        sort: Union[Attribute, Iterable[Attribute]] = None)->List[Task]:
        """Retrieves tasks
        The result set is ordered by start_time descending
        Args:
            offset:
                Ignore this number of rows at the beginning of the result set.
                Results are unpredictable unless order_by is used.
            limit: Return at most this number of rows
            where: A query
            sort:
                A list of Task attributes to sort by. Defaults to
                Task.attr.start_time.desc
        """
        query = sqlalchemy.select([self._tasks_tbl.c.id,
                                   self._tasks_tbl.c.process_name,
                                   self._tasks_tbl.c.state,
                                   self._tasks_tbl.c.start_time,
                                   self._tasks_tbl.c.end_time,
                                   self._tasks_tbl.c.exit_code,
                                   self._tasks_tbl.c.reason])

        query.select_from(self._tasks_tbl)

        if where:
            query = query.where(where.query)

        if sort:
            if isinstance(sort, collections.Iterable):
                for order in sort:
                    query = query.order_by(order.column)
            else:
                query = query.order_by(sort.column)
        else:
            query = query.order_by(self._tasks_tbl.c.start_time.desc())

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        tasks = []

        self._logger.debug('Database command: %s', query)

        try:
            async with (await self._get_connection_pool()).acquire() as conn:
                async for row in conn.execute(query):
                    task = Task()
                    task.task_id = uuid.UUID(row.id)
                    task.state = Task.State(row.state)
                    task.start_time = row.start_time
                    task.process_name = row.process_name
                    task.end_time = row.end_time
                    task.exit_code = row.exit_code
                    task.reason = row.reason

                    tasks.append(task)
        except Exception:
            self._logger.exception('Select failed: %s', query)
            raise
            
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

    def _check_purge_tasks(self):
        """Schedules :meth:`_purge_tasks` to run if sufficient time has elapsed
        since it last ran
        """

        if self._purge_tasks_task is None and (self._last_task_purge_time is None or (
                time.time() - self._last_task_purge_time) >= self._PURGE_TASKS_FREQUENCY_SECONDS):
            self._purge_tasks_task = asyncio.ensure_future(self.purge_tasks())

    async def purge_tasks(self):
        """Deletes rows from the tasks table"""
        if self._paused:
            return

        if not self._ready:
            raise NotReadyError()

        query = sqlalchemy.select([self._tasks_tbl.c.id])
        query.select_from(self._tasks_tbl)
        query = query.where((self._tasks_tbl.c.state != int(Task.State.RUNNING)) & (
                                self._tasks_tbl.c.start_time < datetime.datetime.now() -
                                self._max_completed_task_age))
        query = query.limit(self._DELETE_TASKS_LIMIT)

        delete = self._tasks_tbl.delete()
        delete = delete.where(self._tasks_tbl.c.id == query.as_scalar())

        self._logger.debug('Database command: %s', delete)

        try:
            async with (await self._get_connection_pool()).acquire() as conn:
                while not self._paused:
                    result = await conn.execute(delete)
                    if result.rowcount < self._DELETE_TASKS_LIMIT:
                        break
        except Exception:
            self._logger.exception('Delete failed: %s', delete)
            raise
        finally:
            self._purge_tasks_task = None

        self._last_task_purge_time = time.time()

    async def _read_config(self):
        """Reads configuration"""
        default_config = {
            "max_running_tasks": {
                "description": "The maximum number of tasks that can be running at any given time",
                "type": "integer",
                "default": str(self._DEFAULT_MAX_RUNNING_TASKS)
            },
            "max_completed_task_age_days": {
                "description": "The maximum age, in days (based on the start time), for a rows "
                               "in the tasks table that do not have a status of 'running'",
                "type": "integer",
                "default": str(self._DEFAULT_MAX_COMPLETED_TASK_AGE_DAYS)
            },
        }

        await configuration_manager.create_category('SCHEDULER', default_config,
                                                    'Scheduler configuration')

        config = await configuration_manager.get_category_all_items('SCHEDULER')

        self._max_running_tasks = int(config['max_running_tasks']['value'])
        self._max_completed_task_age = datetime.timedelta(
            seconds=int(config['max_completed_task_age_days']['value']) * self._DAY_SECONDS)

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

        self._start_time = self.current_time if self.current_time else time.time()
        # FIXME: This is an inefficient way of waiting for the storage to register.
        # The spec describes a way to trigger the continued startup on receipt of the registration record.
        # this will work but is not very elegant.

        # make sure that it go forward only when storage service is ready
        storage_service = None

        # TODO: Remove below 'if' after FOGL-521 is merged, as till we do not use storage layer in scheduler, we need
        #       to bypass storage discovery/registration in scheduler
        if Scheduler._core_management_port is not None:
            while storage_service is None:  # TODO: wait for x minutes?
                try:
                    found_services = Service.Instances.get(name="FogLAMP Storage")
                    storage_service = found_services[0]
                except Exception:
                    await asyncio.sleep(5)
            self._logger.info("Starting Scheduler; Management port received is %d", self._core_management_port)

        await self._read_config()
        await self._mark_tasks_interrupted()
        await self._read_storage()

        self._ready = True

        self._scheduler_loop_task = asyncio.ensure_future(self._scheduler_loop())
