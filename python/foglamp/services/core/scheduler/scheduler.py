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
import os
import subprocess
import signal
from typing import List
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common import logger
from foglamp.common.audit_logger import AuditLogger
from foglamp.services.core.scheduler.entities import *
from foglamp.services.core.scheduler.exceptions import *
from foglamp.common.storage_client.exceptions import *
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions
from foglamp.services.common import utils

__author__ = "Terris Linenbach, Amarendra K Sinha, Massimiliano Pinto"
__copyright__ = "Copyright (c) 2017-2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# FOGLAMP_ROOT env variable
_FOGLAMP_ROOT = os.getenv("FOGLAMP_ROOT", default='/usr/local/foglamp')
_SCRIPTS_DIR = os.path.expanduser(_FOGLAMP_ROOT + '/scripts')


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
                                                          'enabled', 'process_name'])
    """Represents a row in the schedules table"""

    class _TaskProcess(object):
        """Tracks a running task with some flags"""
        __slots__ = ['task_id', 'process', 'cancel_requested', 'schedule', 'start_time', 'future']

        def __init__(self):
            self.task_id = None  # type: uuid.UUID
            self.process = None  # type: asyncio.subprocess.Process
            self.cancel_requested = None  # type: int
            """Epoch time when cancel was requested"""
            self.schedule = None  # Schedule._ScheduleRow
            self.start_time = None  # type: int
            """Epoch time when the task was started"""
            self.future = None

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
    _DAY_SECONDS = 3600 * 24
    _WEEK_SECONDS = 3600 * 24 * 7
    _ONE_HOUR = datetime.timedelta(hours=1)
    _ONE_DAY = datetime.timedelta(days=1)

    _MAX_SLEEP = 9999999
    """When there is nothing to do, sleep for this number of seconds (forever)"""

    _STOP_WAIT_SECONDS = 5
    """Wait this number of seconds in :meth:`stop` for tasks to stop"""

    _PURGE_TASKS_FREQUENCY_SECONDS = _DAY_SECONDS
    """How frequently to purge the tasks table"""

    # Mostly constant class attributes
    _logger = None  # type: logging.Logger

    _core_management_host = None
    _core_management_port = None
    _storage = None

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

        # Instance attributes

        self._storage = None

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
    def max_completed_task_age(self) -> datetime.timedelta:
        return self._max_completed_task_age

    @max_completed_task_age.setter
    def max_completed_task_age(self, value: datetime.timedelta) -> None:
        if not isinstance(value, datetime.timedelta):
            raise TypeError("value must be a datetime.timedelta")
        self._max_completed_task_age = value

    @property
    def max_running_tasks(self) -> int:
        """Returns the maximum number of tasks that can run at any given time
        """
        return self._max_running_tasks

    @max_running_tasks.setter
    def max_running_tasks(self, value: int) -> None:
        """Alters the maximum number of tasks that can run at any given time

        Use 0 or a negative value to suspend task creation
        """
        self._max_running_tasks = value
        self._resume_check_schedules()

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

    async def _wait_for_task_completion(self, task_process: _TaskProcess) -> None:
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
            len(self._task_processes) - 1,
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
            # Update the task's status
            update_payload = PayloadBuilder() \
                .SET(exit_code=exit_code,
                     state=int(state),
                     end_time=str(datetime.datetime.now())) \
                .WHERE(['id', '=', str(task_process.task_id)]) \
                .payload()
            try:
                self._logger.debug('Database command: %s', update_payload)
                res = self._storage.update_tbl("tasks", update_payload)
            except Exception:
                self._logger.exception('Update failed: %s', update_payload)
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
            process = await asyncio.create_subprocess_exec(*args_to_exec, cwd=_SCRIPTS_DIR)
        except EnvironmentError:
            self._logger.exception(
                "Unable to start schedule '%s' process '%s'\n%s",
                schedule.name, schedule.process_name, args_to_exec)
            raise

        task_id = uuid.uuid4()
        task_process.process = process
        task_process.schedule = schedule
        task_process.task_id = task_id

        # All tasks including STARTUP tasks go into both self._task_processes and self._schedule_executions
        self._task_processes[task_id] = task_process
        self._schedule_executions[schedule.id].task_processes[task_id] = task_process

        self._logger.info(
            "Process started: Schedule '%s' process '%s' task %s pid %s, %s running tasks\n%s",
            schedule.name, schedule.process_name, task_id, process.pid,
            len(self._task_processes), args_to_exec)

        # Startup tasks are not tracked in the tasks table and do not have any future associated with them.
        if schedule.type != Schedule.Type.STARTUP:
            # The task row needs to exist before the completion handler runs
            insert_payload = PayloadBuilder() \
                .INSERT(id=str(task_id),
                        pid=(self._schedule_executions[schedule.id].
                             task_processes[task_id].process.pid),
                        process_name=schedule.process_name,
                        state=int(Task.State.RUNNING),
                        start_time=str(datetime.datetime.now())) \
                .payload()
            try:
                self._logger.debug('Database command: %s', insert_payload)
                res = self._storage.insert_into_tbl("tasks", insert_payload)
            except Exception:
                self._logger.exception('Insert failed: %s', insert_payload)
                # The process has started. Regardless of this error it must be waited on.
            self._task_processes[task_id].future = asyncio.ensure_future(self._wait_for_task_completion(task_process))

    async def purge_tasks(self):
        """Deletes rows from the tasks table"""
        if self._paused:
            return

        if not self._ready:
            raise NotReadyError()

        delete_payload = PayloadBuilder() \
            .WHERE(["state", "!=", int(Task.State.RUNNING)]) \
            .AND_WHERE(["start_time", "<", str(datetime.datetime.now() - self._max_completed_task_age)]) \
            .LIMIT(self._DELETE_TASKS_LIMIT) \
            .payload()
        try:
            self._logger.debug('Database command: %s', delete_payload)
            while not self._paused:
                res = self._storage.delete_from_tbl("tasks", delete_payload)
                # TODO: Uncomment below when delete count becomes available in storage layer
                # if res.get("count") < self._DELETE_TASKS_LIMIT:
                break
        except Exception:
            self._logger.exception('Delete failed: %s', delete_payload)
            raise
        finally:
            self._purge_tasks_task = None

        self._last_task_purge_time = time.time()

    def _check_purge_tasks(self):
        """Schedules :meth:`_purge_tasks` to run if sufficient time has elapsed
        since it last ran
        """

        if self._purge_tasks_task is None and (self._last_task_purge_time is None or (
                    time.time() - self._last_task_purge_time) >= self._PURGE_TASKS_FREQUENCY_SECONDS):
            self._purge_tasks_task = asyncio.ensure_future(self.purge_tasks())

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

            if schedule.enabled is False:
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

    def _schedule_next_task(self, schedule) -> None:
        """Computes the next time to start a task for a schedule.

        For nonexclusive schedules, this method is called after starting
        a task automatically (it is not called when a task is started
        manually).

        For exclusive schedules, this method is called after the task
        has completed.
        """
        if schedule.enabled is False:
            return

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

    def _schedule_first_task(self, schedule, current_time):
        """Determines the time when a task for a schedule will start.

        Args:
            schedule: The schedule to consider

            current_time:
                Epoch time to use as the current time when determining
                when to schedule tasks

        """
        if schedule.enabled is False:
            return

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

    async def _get_process_scripts(self):
        try:
            self._logger.debug('Database command: %s', "scheduled_processes")
            res = self._storage.query_tbl("scheduled_processes")
            for row in res['rows']:
                self._process_scripts[row.get('name')] = row.get('script')
        except Exception:
            self._logger.exception('Query failed: %s', "scheduled_processes")
            raise

    async def _get_schedules(self):
        # TODO: Get processes first, then add to Schedule
        try:
            self._logger.debug('Database command: %s', 'schedules')
            res = self._storage.query_tbl("schedules")
            for row in res['rows']:
                if 'days' in row.get('schedule_interval'):
                    interval_split = row.get('schedule_interval').split('days')
                    interval_days = interval_split[0].strip()
                    interval_time = interval_split[1].strip()
                elif 'day' in row.get('schedule_interval'):
                    interval_split = row.get('schedule_interval').split('day')
                    interval_days = interval_split[0].strip()
                    interval_time = interval_split[1].strip()
                else:
                    interval_days = 0
                    interval_time = row.get('schedule_interval')
                s_days = int(interval_days)
                s_interval = datetime.datetime.strptime(interval_time, "%H:%M:%S")
                interval = datetime.timedelta(days=s_days, hours=s_interval.hour, minutes=s_interval.minute,
                                              seconds=s_interval.second)

                repeat_seconds = None
                if interval is not None and interval != datetime.timedelta(0):
                    repeat_seconds = interval.total_seconds()

                s_ti = row.get('schedule_time') if row.get('schedule_time') else '00:00:00'
                s_tim = datetime.datetime.strptime(s_ti, "%H:%M:%S")
                schedule_time = datetime.time().replace(hour=s_tim.hour, minute=s_tim.minute, second=s_tim.second)

                schedule_id = uuid.UUID(row.get('id'))

                #
                # row.get('schedule_day') returns an int, say 0, from SQLite
                # and "0", as a string, from Postgres
                # We handle here this difference
                #

                if type(row.get('schedule_day')) is str:
                    s_day = int(row.get('schedule_day')) if row.get('schedule_day').strip() else None
                else:
                    s_day = int(row.get('schedule_day'))

                schedule = self._ScheduleRow(
                    id=schedule_id,
                    name=row.get('schedule_name'),
                    type=int(row.get('schedule_type')),
                    day=s_day,
                    time=schedule_time,
                    repeat=interval,
                    repeat_seconds=repeat_seconds,
                    exclusive=True if row.get('exclusive') == 't' else False,
                    enabled=True if row.get('enabled') == 't' else False,
                    process_name=row.get('process_name'))

                self._schedules[schedule_id] = schedule
                self._schedule_first_task(schedule, self._start_time)
        except Exception:
            self._logger.exception('Query failed: %s', 'schedules')
            raise

    async def _read_storage(self):
        """Reads schedule information from the storage server"""
        await self._get_process_scripts()
        await self._get_schedules()

    async def _mark_tasks_interrupted(self):
        """The state for any task with a NULL end_time is set to interrupted"""
        # TODO FOGL-722 NULL can not be passed like this

        """ # Update the task's status
        update_payload = PayloadBuilder() \
            .SET(state=int(Task.State.INTERRUPTED),
                 end_time=str(datetime.datetime.now())) \
            .WHERE(['end_time', '=', "NULL"]) \
            .payload()
        try:
            self._logger.debug('Database command: %s', update_payload)
            res = self._storage.update_tbl("tasks", update_payload)
        except Exception:
            self._logger.exception('Update failed: %s', update_payload)
            raise
        """
        pass

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
                               "in the tasks table that do not have a status of running",
                "type": "integer",
                "default": str(self._DEFAULT_MAX_COMPLETED_TASK_AGE_DAYS)
            },
        }

        cfg_manager = ConfigurationManager(self._storage)
        await cfg_manager.create_category('SCHEDULER', default_config, 'Scheduler configuration')

        config = await cfg_manager.get_category_all_items('SCHEDULER')
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

        self._logger.info("Starting")

        self._start_time = self.current_time if self.current_time else time.time()

        # FIXME: Move below part code to server.py->_start_core(), line 123, after start of storage and before start
        #        of scheduler. May need to either pass the storage object or create a storage object here itself.
        #        Also provide a timeout option.
        # ************ make sure that it go forward only when storage service is ready
        storage_service = None

        while storage_service is None and self._storage is None:
            try:
                found_services = ServiceRegistry.get(name="FogLAMP Storage")
                storage_service = found_services[0]
                self._storage = StorageClient(self._core_management_host, self._core_management_port,
                                              svc=storage_service)

            except (service_registry_exceptions.DoesNotExist, InvalidServiceInstance, StorageServiceUnavailable,
                    Exception) as ex:
                # traceback.print_exc()
                await asyncio.sleep(5)
        # **************

        # Everything OK, so now start Scheduler and create Storage instance
        self._logger.info("Starting Scheduler: Management port received is %d", self._core_management_port)

        await self._read_config()
        await self._mark_tasks_interrupted()
        await self._read_storage()

        self._ready = True

        self._scheduler_loop_task = asyncio.ensure_future(self._scheduler_loop())

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
                except Exception as ex:
                    self._logger.exception('An exception was raised by Scheduler._purge_tasks %s', str(ex))

            self._resume_check_schedules()

            # Stop the main loop
            try:
                await self._scheduler_loop_task
            except Exception as ex:
                self._logger.exception('An exception was raised by Scheduler._scheduler_loop %s', str(ex))
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

            # Stopping of STARTUP tasks aka microservices will be taken up separately by Core
            if schedule.type != Schedule.Type.STARTUP:
                self._logger.info(
                    "Stopping process: Schedule '%s' process '%s' task %s pid %s\n%s",
                    schedule.name,
                    schedule.process_name,
                    task_id,
                    task_process.process.pid,
                    self._process_scripts[schedule.process_name])
                try:
                    # We need to terminate the child processes because now all tasks are started vide a script and
                    # this creates two unix processes. Scheduler can store pid of the parent shell script process only
                    # and on termination of the task, both the script shell process and actual task process need to
                    # be stopped.
                    self._terminate_child_processes(task_process.process.pid)
                    task_process.process.terminate()
                except ProcessLookupError:
                    pass  # Process has terminated

        # Wait for all processes to stop
        for _ in range(self._STOP_WAIT_SECONDS):
            if not self._task_processes:
                break
            await asyncio.sleep(1)

        if self._task_processes:
            # Before throwing timeout error, just check if there are still any tasks pending for cancellation
            task_count = 0
            for task_id in list(self._task_processes.keys()):
                try:
                    task_process = self._task_processes[task_id]
                    schedule = task_process.schedule
                    task_count += 1 if schedule.type != Schedule.Type.STARTUP else 0
                except KeyError:
                    continue
            if task_count != 0:
                raise TimeoutError("Timeout Error: Could not stop scheduler as {} tasks are pending".format(task_count))

        self._schedule_executions = None
        self._task_processes = None
        self._schedules = None
        self._process_scripts = None

        self._ready = False
        self._paused = False
        self._start_time = None

        self._logger.info("Stopped")
        return True

    # CRUD methods for scheduled_processes, schedules, tasks

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
        schedule.enabled = schedule_row.enabled
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

    async def get_schedule_by_name(self, name) -> Schedule:
        """Retrieves a schedule from its id

        Raises:
            ScheduleNotFoundException
        """
        if not self._ready:
            raise NotReadyError()

        found_id = None
        for (schedule_id, schedule_row) in self._schedules.items():
            if self._schedules[schedule_id].name == name:
                found_id = schedule_id
        if found_id is None:
            raise ScheduleNotFoundError(name)

        return self._schedule_row_to_schedule(found_id, schedule_row)

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
            raise ValueError('repeat must be of type datetime.timedelta')

        if schedule.exclusive is None or not (schedule.exclusive == True or schedule.exclusive == False):
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
            update_payload = PayloadBuilder() \
                .SET(schedule_name=schedule.name,
                     schedule_type=int(schedule.schedule_type),
                     schedule_interval=str(schedule.repeat),
                     schedule_day=day if day else 0,
                     schedule_time=str(schedule_time) if schedule_time else '00:00:00',
                     exclusive='t' if schedule.exclusive else 'f',
                     enabled='t' if schedule.enabled else 'f',
                     process_name=schedule.process_name) \
                .WHERE(['id', '=', str(schedule.schedule_id)]) \
                .payload()
            try:
                self._logger.debug('Database command: %s', update_payload)
                res = self._storage.update_tbl("schedules", update_payload)
                if res.get('count') == 0:
                    is_new_schedule = True
            except Exception:
                self._logger.exception('Update failed: %s', update_payload)
                raise
            audit = AuditLogger(self._storage)
            await audit.information('SCHCH', {'schedule': schedule.toDict()})

        if is_new_schedule:
            insert_payload = PayloadBuilder() \
                .INSERT(id=str(schedule.schedule_id),
                        schedule_type=int(schedule.schedule_type),
                        schedule_name=schedule.name,
                        schedule_interval=str(schedule.repeat),
                        schedule_day=day if day else 0,
                        schedule_time=str(schedule_time) if schedule_time else '00:00:00',
                        exclusive='t' if schedule.exclusive else 'f',
                        enabled='t' if schedule.enabled else 'f',
                        process_name=schedule.process_name) \
                .payload()
            try:
                self._logger.debug('Database command: %s', insert_payload)
                res = self._storage.insert_into_tbl("schedules", insert_payload)
            except Exception:
                self._logger.exception('Insert failed: %s', insert_payload)
                raise
            audit = AuditLogger(self._storage)
            await audit.information('SCHAD', {'schedule': schedule.toDict()})

        repeat_seconds = None
        if schedule.repeat is not None and schedule.repeat != datetime.timedelta(0):
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
            enabled=schedule.enabled,
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

    async def remove_service_from_task_processes(self, service_name):
        """
        This method caters to the use case when a microservice, e.g. South service, which has been started by the
        Scheduler and then is shutdown vide api and then is needed to be restarted. It removes the Scheduler's record
        of the task related to the STARTUP schedule (which is not removed when shutdown action is taken by the
        microservice api as the microservice is running in a separate process and hinders starting a schedule by
        Scheduler's queue_task() method).

        Args: service_name:
        Returns:
        """
        if not self._ready:
            return False

        # Find task_id for the service
        task_id = None
        task_process = None
        schedule_type = None
        try:
            for key in list(self._task_processes.keys()):
                if self._task_processes[key].schedule.process_name == service_name:
                    task_id = key
                    break
            if task_id is None:
                raise KeyError

            task_process = self._task_processes[task_id]

            if task_id is not None:
                schedule = task_process.schedule
                schedule_type = schedule.type
                if schedule_type == Schedule.Type.STARTUP: # If schedule is a service e.g. South services
                    del self._schedule_executions[schedule.id]
                    del self._task_processes[task_process.task_id]
                    self._logger.info("Service {} records successfully removed".format(service_name))
                    return True
        except KeyError:
            pass

        self._logger.exception("Service {} records could not be removed with task id {} type {}".format(service_name, str(task_id), schedule_type))
        return False

    async def disable_schedule(self, schedule_id: uuid.UUID):
        """
        Find running Schedule, Terminate running process, Disable Schedule, Update database

        Args: schedule_id:
        Returns:
        """
        if self._paused or not self._ready:
            raise NotReadyError()

        # Find running task for the schedule.
        # self._task_processes contains ALL tasks including STARTUP tasks.
        try:
            schedule = await self.get_schedule(schedule_id)
        except ScheduleNotFoundError:
            self._logger.exception("No such Schedule %s", str(schedule_id))
            return False, "No such Schedule"

        if schedule.enabled is False:
            self._logger.info("Schedule %s already disabled", str(schedule_id))
            return True, "Schedule {} already disabled".format(str(schedule_id))

        # Disable Schedule - update the schedule in memory
        self._schedules[schedule_id] = self._schedules[schedule_id]._replace(enabled=False)

        # Update database
        update_payload = PayloadBuilder().SET(enabled='f').WHERE(['id', '=', str(schedule_id)]).payload()
        try:
            self._logger.debug('Database command: %s', update_payload)
            res = self._storage.update_tbl("schedules", update_payload)
        except Exception:
            self._logger.exception('Update failed: %s', update_payload)
            raise RuntimeError('Update failed: %s', update_payload)
        await asyncio.sleep(1)

        # If a task is running for the schedule, then terminate the process
        task_id = None
        task_process = None
        try:
            for key in list(self._task_processes.keys()):
                if self._task_processes[key].schedule.id == schedule_id:
                    task_id = key
                    break
            if task_id is None:
                raise KeyError
            task_process = self._task_processes[task_id]
        except KeyError:
            self._logger.info("No Task running for Schedule %s", str(schedule_id))

        if task_id is not None:
            schedule = task_process.schedule
            if schedule.type == Schedule.Type.STARTUP:  # If schedule is a service e.g. South services
                try:
                    found_services = ServiceRegistry.get(name=schedule.process_name)
                    service = found_services[0]
                    if await utils.ping_service(service) is True:
                        # Shutdown will take care of unregistering the service from core
                        await utils.shutdown_service(service)
                except:
                    pass
                try:
                    # As of now, script starts the process and therefore, we need to explicitly stop this script process
                    # as shutdown caters to stopping of the actual service only.
                    task_process.process.terminate()
                except ProcessLookupError:
                    pass  # Process has terminated
            else: # else it is a Task e.g. North tasks
                # Terminate process
                try:
                    # We need to terminate the child processes because now all tasks are started vide a script and
                    # this creates two unix processes. Scheduler can store pid of the parent shell script process only
                    # and on termination of the task, both the script shell process and actual task process need to
                    # be stopped.
                    self._terminate_child_processes(task_process.process.pid)
                    task_process.process.terminate()
                except ProcessLookupError:
                    pass  # Process has terminated
                self._logger.info(
                    "Terminated Task '%s/%s' process '%s' task %s pid %s\n%s",
                    schedule.name,
                    str(schedule.id),
                    schedule.process_name,
                    task_id,
                    task_process.process.pid,
                    self._process_scripts[schedule.process_name])
                # TODO: FOGL-356 track the last time TERM was sent to each task
                task_process.cancel_requested = time.time()
                task_future = task_process.future
                if task_future.cancel() is True:
                    await self._wait_for_task_completion(task_process)

        self._logger.info(
            "Disabled Schedule '%s/%s' process '%s'\n",
            schedule.name,
            str(schedule_id),
            schedule.process_name)
        audit = AuditLogger(self._storage)
        sch = await self.get_schedule(schedule_id)
        await audit.information('SCHCH', {'schedule': sch.toDict()})
        return True, "Schedule successfully disabled"

    async def enable_schedule(self, schedule_id: uuid.UUID):
        """
        Get Schedule, Enable Schedule, Update database, Start Schedule

        Args: schedule_id:
        Returns:
        """
        if self._paused or not self._ready:
            raise NotReadyError()

        try:
            schedule = await self.get_schedule(schedule_id)
        except ScheduleNotFoundError:
            self._logger.exception("No such Schedule %s", str(schedule_id))
            return False, "No such Schedule"

        if schedule.enabled is True:
            self._logger.info("Schedule %s already enabled", str(schedule_id))
            return True, "Schedule is already enabled"

        # Enable Schedule
        self._schedules[schedule_id] = self._schedules[schedule_id]._replace(enabled=True)

        # Update database
        update_payload = PayloadBuilder().SET(enabled='t').WHERE(['id', '=', str(schedule_id)]).payload()
        try:
            self._logger.debug('Database command: %s', update_payload)
            res = self._storage.update_tbl("schedules", update_payload)
        except Exception:
            self._logger.exception('Update failed: %s', update_payload)
            raise RuntimeError('Update failed: %s', update_payload)
        await asyncio.sleep(1)

        # Start schedule
        await self.queue_task(schedule_id)

        self._logger.info(
            "Enabled Schedule '%s/%s' process '%s'\n",
            schedule.name,
            str(schedule_id),
            schedule.process_name)
        audit = AuditLogger(self._storage)
        sch = await self.get_schedule(schedule_id)
        await audit.information('SCHCH', { 'schedule': sch.toDict() })
        return True, "Schedule successfully enabled"

    async def queue_task(self, schedule_id: uuid.UUID) -> None:
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

        if schedule_row.enabled is False:
            self._logger.info("Schedule '%s' is not enabled", schedule_row.name)
            return False

        try:
            schedule_execution = self._schedule_executions[schedule_id]
        except KeyError:
            schedule_execution = self._ScheduleExecution()
            self._schedule_executions[schedule_row.id] = schedule_execution

        schedule_execution.start_now = True

        self._logger.info("Queued schedule '%s' for execution", schedule_row.name)
        self._resume_check_schedules()
        return True

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

        try:
            schedule = self._schedules[schedule_id]
            if schedule.enabled is True:
                self._logger.exception('Attempt to delete an enabled Schedule %s. Not deleted.', str(schedule_id))
                raise RuntimeWarning("Enabled Schedule {} cannot be deleted.".format(str(schedule_id)))
        except KeyError:
            raise ScheduleNotFoundError(schedule_id)

        del self._schedules[schedule_id]

        # TODO: Inspect race conditions with _set_first
        delete_payload = PayloadBuilder() \
            .WHERE(['id', '=', str(schedule_id)]) \
            .payload()
        try:
            self._logger.debug('Database command: %s', delete_payload)
            res = self._storage.delete_from_tbl("schedules", delete_payload)
        except Exception:
            self._logger.exception('Delete failed: %s', delete_payload)
            raise

        return True, "Schedule deleted successfully."

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

    async def get_task(self, task_id: uuid.UUID) -> Task:
        """Retrieves a task given its id"""
        query_payload = PayloadBuilder().WHERE(["id", "=", str(task_id)]).payload()

        try:
            self._logger.debug('Database command: %s', query_payload)
            res = self._storage.query_tbl_with_payload("tasks", query_payload)
            for row in res['rows']:
                task = Task()
                task.task_id = row.get('id')
                task.state = Task.State(int(row.get('state')))
                task.start_time = row.get('start_time')
                task.process_name = row.get('process_name')
                task.end_time = row.get('end_time')
                task.exit_code = row.get('exit_code')
                task.reason = row.get('reason')
                return task
        except Exception:
            self._logger.exception('Query failed: %s', query_payload)
            raise

        raise TaskNotFoundError(task_id)

    async def get_tasks(self, limit=100, offset=0, where=None, and_where=None, or_where=None, sort=None) -> List[Task]:
        """Retrieves tasks
        The result set is ordered by start_time descending
        Args:
            offset:
                Ignore this number of rows at the beginning of the result set.
                Results are unpredictable unless order_by is used.
            limit: Return at most this number of rows
            where: A query
            sort:
                A tuple of Task attributes to sort by.
                Defaults to ("start_time", "desc")
        """

        chain_payload = PayloadBuilder().LIMIT(limit).chain_payload()
        if offset:
            chain_payload = PayloadBuilder(chain_payload).OFFSET(offset).chain_payload()
        if where:
            chain_payload = PayloadBuilder(chain_payload).WHERE(where).chain_payload()
        if and_where:
            chain_payload = PayloadBuilder(chain_payload).AND_WHERE(and_where).chain_payload()
        if or_where:
            chain_payload = PayloadBuilder(chain_payload).OR_WHERE(or_where).chain_payload()
        if sort:
            chain_payload = PayloadBuilder(chain_payload).ORDER_BY(sort).chain_payload()

        query_payload = PayloadBuilder(chain_payload).payload()
        tasks = []

        try:
            self._logger.debug('Database command: %s', query_payload)
            res = self._storage.query_tbl_with_payload("tasks", query_payload)
            for row in res['rows']:
                task = Task()
                task.task_id = row.get('id')
                task.state = Task.State(int(row.get('state')))
                task.start_time = row.get('start_time')
                task.process_name = row.get('process_name')
                task.end_time = row.get('end_time')
                task.exit_code = row.get('exit_code')
                task.reason = row.get('reason')
                tasks.append(task)
        except Exception:
            self._logger.exception('Query failed: %s', query_payload)
            raise

        return tasks

    async def cancel_task(self, task_id: uuid.UUID) -> None:
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
            # We need to terminate the child processes because now all tasks are started vide a script and
            # this creates two unix processes. Scheduler can store pid of the parent shell script process only
            # and on termination of the task, both the script shell process and actual task process need to
            # be stopped.
            self._terminate_child_processes(task_process.process.pid)
            task_process.process.terminate()
        except ProcessLookupError:
            pass  # Process has terminated

        if task_process.future.cancel() is True:
            await self._wait_for_task_completion(task_process)

    def _terminate_child_processes(self, parent_id):
        ps_command = subprocess.Popen("ps -o pid --ppid {} --noheaders".format(parent_id), shell=True,
                                      stdout=subprocess.PIPE)
        ps_output, err = ps_command.communicate()
        pids = ps_output.decode().strip().split("\n")
        for pid_str in pids:
            if pid_str.strip():
                os.kill(int(pid_str.strip()), signal.SIGTERM)
