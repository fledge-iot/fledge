# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import datetime
import uuid
import time
import json
from unittest.mock import MagicMock, call

import copy
import pytest
from foglamp.services.core.scheduler.scheduler import Scheduler, AuditLogger, ConfigurationManager
from foglamp.services.core.scheduler.entities import *
from foglamp.services.core.scheduler.exceptions import *
from foglamp.common.storage_client.storage_client import StorageClientAsync

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_task():
    return ""

async def mock_process():
    m = MagicMock()
    m.pid = 9999
    m.terminate = lambda: True
    return m


@pytest.allure.feature("unit")
@pytest.allure.story("scheduler")
class TestScheduler:
    async def scheduler_fixture(self, mocker):
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.object(scheduler, '_schedule_first_task')
        mocker.patch.object(scheduler, '_ready', True)
        mocker.patch.object(scheduler, '_paused', False)
        mocker.patch.object(scheduler, '_process_scripts', return_value="North Readings to PI")
        mocker.patch.object(scheduler, '_wait_for_task_completion', return_value=asyncio.ensure_future(mock_task()))
        mocker.patch.object(scheduler, '_terminate_child_processes')
        mocker.patch.object(asyncio, 'create_subprocess_exec', return_value=asyncio.ensure_future(mock_process()))

        await scheduler._get_schedules()

        schedule = scheduler._ScheduleRow(
            id=uuid.UUID("2b614d26-760f-11e7-b5a5-be2e44b06b34"),
            process_name="North Readings to PI",
            name="OMF to PI north",
            type=Schedule.Type.INTERVAL,
            repeat=datetime.timedelta(seconds=30),
            repeat_seconds=30,
            time=None,
            day=None,
            exclusive=True,
            enabled=True)

        log_exception = mocker.patch.object(scheduler._logger, "exception")
        log_error = mocker.patch.object(scheduler._logger, "error")
        log_debug = mocker.patch.object(scheduler._logger, "debug")
        log_info = mocker.patch.object(scheduler._logger, "info")

        return scheduler, schedule, log_info, log_exception, log_error, log_debug

    @pytest.mark.asyncio
    async def test__resume_check_schedules(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)

        # WHEN
        # Check IF part
        mocker.patch.object(scheduler, '_scheduler_loop_sleep_task', asyncio.Task(asyncio.sleep(5)))
        scheduler._resume_check_schedules()

        # THEN
        assert scheduler._check_processes_pending is False

        # WHEN
        # Check ELSE part
        mocker.patch.object(scheduler, '_scheduler_loop_sleep_task', None)
        scheduler._resume_check_schedules()

        # THEN
        assert scheduler._check_processes_pending is True

    @pytest.mark.asyncio
    async def test__wait_for_task_completion(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_info = mocker.patch.object(scheduler._logger, "info")

        mock_schedules = dict()
        mock_schedule = scheduler._ScheduleRow(
            id=uuid.UUID("2b614d26-760f-11e7-b5a5-be2e44b06b34"),
            process_name="North Readings to PI",
            name="OMF to PI north",
            type=Schedule.Type.INTERVAL,
            repeat=datetime.timedelta(seconds=30),
            repeat_seconds=30,
            time=None,
            day=None,
            exclusive=True,
            enabled=True)
        mock_schedules[mock_schedule.id] = mock_schedule

        mock_task_process = scheduler._TaskProcess()
        mock_task_processes = dict()
        mock_task_process.process = await asyncio.create_subprocess_exec("sleep", ".1")
        mock_task_process.schedule = mock_schedule
        mock_task_id = uuid.uuid4()
        mock_task_process.task_id = mock_task_id
        mock_task_processes[mock_task_process.task_id] = mock_task_process

        mock_schedule_executions = dict()
        mock_schedule_execution = scheduler._ScheduleExecution()
        mock_schedule_executions[mock_schedule.id] = mock_schedule_execution
        mock_schedule_executions[mock_schedule.id].task_processes[mock_task_id] = mock_task_process

        mocker.patch.object(scheduler, '_resume_check_schedules')
        mocker.patch.object(scheduler, '_schedule_next_task')
        mocker.patch.multiple(scheduler, _schedules=mock_schedules,
                              _task_processes=mock_task_processes,
                              _schedule_executions=mock_schedule_executions)
        mocker.patch.object(scheduler, '_process_scripts', return_value="North Readings to PI")

        # WHEN
        await scheduler._wait_for_task_completion(mock_task_process)

        # THEN
        # After task completion, sleep above, no task processes should be left pending
        assert 0 == len(scheduler._task_processes)
        assert 0 == len(scheduler._schedule_executions[mock_schedule.id].task_processes)
        args, kwargs = log_info.call_args_list[0]
        assert 'OMF to PI north' in args
        assert 'North Readings to PI' in args

    @pytest.mark.asyncio
    async def test__start_task(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_info = mocker.patch.object(scheduler._logger, "info")
        mocker.patch.object(scheduler, '_schedule_first_task')
        await scheduler._get_schedules()

        schedule = scheduler._ScheduleRow(
            id=uuid.UUID("2b614d26-760f-11e7-b5a5-be2e44b06b34"),
            process_name="North Readings to PI",
            name="OMF to PI north",
            type=Schedule.Type.INTERVAL,
            repeat=datetime.timedelta(seconds=30),
            repeat_seconds=30,
            time=None,
            day=None,
            exclusive=True,
            enabled=True)

        mocker.patch.object(scheduler, '_ready', True)
        mocker.patch.object(scheduler, '_resume_check_schedules')

        # Assert that there is no task queued for mock_schedule
        with pytest.raises(KeyError) as excinfo:
            assert scheduler._schedule_executions[schedule.id] is True
        # Now queue task and assert that the task has been queued
        await scheduler.queue_task(schedule.id)
        assert isinstance(scheduler._schedule_executions[schedule.id], scheduler._ScheduleExecution)

        mocker.patch.object(asyncio, 'create_subprocess_exec', return_value=asyncio.ensure_future(mock_process()))
        mocker.patch.object(asyncio, 'ensure_future', return_value=asyncio.ensure_future(mock_task()))
        mocker.patch.object(scheduler, '_resume_check_schedules')
        mocker.patch.object(scheduler, '_process_scripts', return_value="North Readings to PI")
        mocker.patch.object(scheduler, '_wait_for_task_completion')

        # Confirm that task has not started yet
        assert 0 == len(scheduler._schedule_executions[schedule.id].task_processes)

        # WHEN
        await scheduler._start_task(schedule)

        # THEN
        # Confirm that task has started
        assert 1 == len(scheduler._schedule_executions[schedule.id].task_processes)
        assert 2 == log_info.call_count
        assert call("Queued schedule '%s' for execution", 'OMF to PI north') == log_info.call_args_list[0]
        args, kwargs = log_info.call_args_list[1]
        assert "Process started: Schedule '%s' process '%s' task %s pid %s, %s running tasks\n%s" in args
        assert 'OMF to PI north' in args
        assert 'North Readings to PI' in args

    @pytest.mark.asyncio
    async def test_purge_tasks(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.multiple(scheduler, _ready=True, _paused=False)
        mocker.patch.object(scheduler, '_max_completed_task_age', datetime.datetime.now())

        # WHEN
        await scheduler.purge_tasks()

        # THEN
        assert scheduler._purge_tasks_task is None
        assert scheduler._last_task_purge_time is not None

    @pytest.mark.asyncio
    async def test__check_purge_tasks(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.multiple(scheduler, _purge_tasks_task=None,
                              _last_task_purge_time=None)
        mocker.patch.object(scheduler, 'purge_tasks', return_value=asyncio.ensure_future(mock_task()))

        # WHEN
        scheduler._check_purge_tasks()

        # THEN
        assert scheduler._purge_tasks_task is not None

    @pytest.mark.asyncio
    async def test__check_schedules(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_info = mocker.patch.object(scheduler._logger, "info")

        current_time = time.time()
        mocker.patch.multiple(scheduler, _max_running_tasks=10,
                              _start_time=current_time)
        await scheduler._get_schedules()
        mocker.patch.object(scheduler, '_start_task', return_value=asyncio.ensure_future(mock_task()))

        # WHEN
        earliest_start_time = await scheduler._check_schedules()

        # THEN
        assert earliest_start_time is not None
        assert 3 == log_info.call_count
        args0, kwargs0 = log_info.call_args_list[0]
        args1, kwargs1 = log_info.call_args_list[1]
        args2, kwargs2 = log_info.call_args_list[2]
        assert 'stats collection' in args0
        assert 'COAP listener south' in args1
        assert 'OMF to PI north' in args2

    @pytest.mark.asyncio
    @pytest.mark.skip("_scheduler_loop() not suitable for unit testing. Will be tested during System tests.")
    async def test__scheduler_loop(self, mocker):
        pass

    @pytest.mark.asyncio
    async def test__schedule_next_timed_task(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_info = mocker.patch.object(scheduler._logger, "info")

        current_time = time.time()
        mocker.patch.multiple(scheduler, _max_running_tasks=10,
                              _start_time=current_time)
        await scheduler._get_schedules()

        sch_id = uuid.UUID("2176eb68-7303-11e7-8cf7-a6006ad3dba0")  # stat collector
        sch = scheduler._schedules[sch_id]
        sch_execution = scheduler._schedule_executions[sch_id]
        time_before_call = sch_execution.next_start_time

        # WHEN
        next_dt = datetime.datetime.fromtimestamp(sch_execution.next_start_time)
        next_dt += datetime.timedelta(seconds=sch.repeat_seconds)
        scheduler._schedule_next_timed_task(sch, sch_execution, next_dt)
        time_after_call = sch_execution.next_start_time

        # THEN
        assert time_after_call > time_before_call
        assert 3 == log_info.call_count
        args0, kwargs0 = log_info.call_args_list[0]
        args1, kwargs1 = log_info.call_args_list[1]
        args2, kwargs2 = log_info.call_args_list[2]
        assert 'stats collection' in args0
        assert 'COAP listener south' in args1
        assert 'OMF to PI north' in args2

    @pytest.mark.asyncio
    async def test__schedule_next_task(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_info = mocker.patch.object(scheduler._logger, "info")

        current_time = time.time()
        mocker.patch.multiple(scheduler, _max_running_tasks=10,
                              _start_time=current_time-3600)
        await scheduler._get_schedules()

        sch_id = uuid.UUID("2176eb68-7303-11e7-8cf7-a6006ad3dba0")  # stat collector
        sch = scheduler._schedules[sch_id]
        sch_execution = scheduler._schedule_executions[sch_id]
        time_before_call = sch_execution.next_start_time

        # WHEN
        scheduler._schedule_next_task(sch)
        time_after_call = sch_execution.next_start_time

        # THEN
        assert time_after_call > time_before_call
        assert 4 == log_info.call_count
        args0, kwargs0 = log_info.call_args_list[0]
        args1, kwargs1 = log_info.call_args_list[1]
        args2, kwargs2 = log_info.call_args_list[2]
        args3, kwargs3 = log_info.call_args_list[3]
        assert 'stats collection' in args0
        assert 'COAP listener south' in args1
        assert 'OMF to PI north' in args2
        # As part of scheduler._get_schedules(), scheduler._schedule_first_task() also gets executed, hence
        # "stat collector" appears twice in this list.
        assert 'stats collection' in args3

    @pytest.mark.asyncio
    async def test__schedule_first_task(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_info = mocker.patch.object(scheduler._logger, "info")

        current_time = time.time()
        curr_time = datetime.datetime.fromtimestamp(current_time)
        mocker.patch.multiple(scheduler, _max_running_tasks=10,
                              _start_time=current_time)
        await scheduler._get_schedules()

        sch_id = uuid.UUID("2176eb68-7303-11e7-8cf7-a6006ad3dba0")  # stat collector
        sch = scheduler._schedules[sch_id]
        sch_execution = scheduler._schedule_executions[sch_id]

        # WHEN
        scheduler._schedule_first_task(sch, current_time)
        time_after_call = sch_execution.next_start_time

        # THEN
        assert time_after_call > time.mktime(curr_time.timetuple())
        assert 4 == log_info.call_count
        args0, kwargs0 = log_info.call_args_list[0]
        args1, kwargs1 = log_info.call_args_list[1]
        args2, kwargs2 = log_info.call_args_list[2]
        args3, kwargs3 = log_info.call_args_list[3]
        assert 'stats collection' in args0
        assert 'COAP listener south' in args1
        assert 'OMF to PI north' in args2
        # As part of scheduler._get_schedules(), scheduler._schedule_first_task() also gets executed, hence
        # "stat collector" appears twice in this list.
        assert 'stats collection' in args3

    @pytest.mark.asyncio
    async def test__get_process_scripts(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)

        # WHEN
        await scheduler._get_process_scripts()

        # THEN
        assert len(scheduler._storage_async.scheduled_processes) == len(scheduler._process_scripts)

    @pytest.mark.asyncio
    async def test__get_process_scripts_exception(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_debug = mocker.patch.object(scheduler._logger, "debug", side_effect=Exception())
        log_exception = mocker.patch.object(scheduler._logger, "exception")

        # WHEN
        # THEN
        with pytest.raises(Exception):
            await scheduler._get_process_scripts()

        log_args = 'Query failed: %s', 'scheduled_processes'
        log_exception.assert_called_once_with(*log_args)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_interval, is_exception", [
        ('"Blah" 0 days', True),
        ('12:30:11', False),
        ('0 day 12:30:11', False),
        ('1 day 12:40:11', False),
        ('2 days', True),
        ('2 days 00:00:59', False),
        ('00:25:61', True)
    ])
    async def test__get_schedules(self, test_interval, is_exception, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.object(scheduler, '_schedule_first_task')
        log_exception = mocker.patch.object(scheduler._logger, "exception")

        new_schedules = copy.deepcopy(MockStorageAsync.schedules)
        new_schedules[5]['schedule_interval'] = test_interval
        mocker.patch.object(MockStorageAsync, 'schedules', new_schedules)

        # WHEN
        # THEN
        if is_exception is True:
            with pytest.raises(Exception):
                await scheduler._get_schedules()
                assert 1 == log_exception.call_count
        else:
            await scheduler._get_schedules()
            assert len(scheduler._storage_async.schedules) == len(scheduler._schedules)

    @pytest.mark.asyncio
    async def test__get_schedules_exception(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_debug = mocker.patch.object(scheduler._logger, "debug", side_effect=Exception())
        log_exception = mocker.patch.object(scheduler._logger, "exception")
        mocker.patch.object(scheduler, '_schedule_first_task', side_effect=Exception())

        # WHEN
        # THEN
        with pytest.raises(Exception):
            await scheduler._get_schedules()

        log_args = 'Query failed: %s', 'schedules'
        log_exception.assert_called_once_with(*log_args)

    @pytest.mark.asyncio
    async def test__read_storage(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.object(scheduler, '_schedule_first_task')

        # WHEN
        await scheduler._read_storage()

        # THEN
        assert len(scheduler._storage_async.scheduled_processes) == len(scheduler._process_scripts)
        assert len(scheduler._storage_async.schedules) == len(scheduler._schedules)

    @pytest.mark.asyncio
    @pytest.mark.skip("_mark_tasks_interrupted() not implemented in main Scheduler class.")
    async def test__mark_tasks_interrupted(self, mocker):
        pass

    @pytest.mark.asyncio
    async def test__read_config(self, mocker):
        async def get_cat():
            return {
                    "max_running_tasks": {
                        "description": "The maximum number of tasks that can be running at any given time",
                        "type": "integer",
                        "default": str(Scheduler._DEFAULT_MAX_RUNNING_TASKS),
                        "value": str(Scheduler._DEFAULT_MAX_RUNNING_TASKS)
                    },
                    "max_completed_task_age_days": {
                        "description": "The maximum age, in days (based on the start time), for a rows "
                                       "in the tasks table that do not have a status of running",
                        "type": "integer",
                        "default": str(Scheduler._DEFAULT_MAX_COMPLETED_TASK_AGE_DAYS),
                        "value": str(Scheduler._DEFAULT_MAX_COMPLETED_TASK_AGE_DAYS)
                    },
            }
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        cr_cat = mocker.patch.object(ConfigurationManager, "create_category", return_value=asyncio.ensure_future(mock_task()))
        get_cat = mocker.patch.object(ConfigurationManager, "get_category_all_items", return_value=get_cat())

        # WHEN
        assert scheduler._max_running_tasks is None
        assert scheduler._max_completed_task_age is None
        await scheduler._read_config()

        # THEN
        assert 1 == cr_cat.call_count
        assert 1 == get_cat.call_count
        assert scheduler._max_running_tasks is not None
        assert scheduler._max_completed_task_age is not None

    @pytest.mark.asyncio
    async def test_start(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_debug = mocker.patch.object(scheduler._logger, "debug")
        log_info = mocker.patch.object(scheduler._logger, "info")

        current_time = time.time()
        mocker.patch.object(scheduler, '_schedule_first_task')
        mocker.patch.object(scheduler, '_scheduler_loop', return_value=asyncio.ensure_future(mock_task()))
        mocker.patch.multiple(scheduler, _core_management_port=9999,
                              _core_management_host="0.0.0.0",
                              current_time=current_time - 3600)

        # TODO: Remove after implementation of above test test__read_config()
        mocker.patch.object(scheduler, '_read_config', return_value=asyncio.ensure_future(mock_task()))

        assert scheduler._ready is False

        # WHEN
        await scheduler.start()

        # THEN
        assert scheduler._ready is True
        assert len(scheduler._storage_async.scheduled_processes) == len(scheduler._process_scripts)
        assert len(scheduler._storage_async.schedules) == len(scheduler._schedules)
        calls = [call('Starting'),
                 call('Starting Scheduler: Management port received is %d', 9999)]
        log_info.assert_has_calls(calls, any_order=True)
        calls = [call('Database command: %s', 'scheduled_processes'),
                 call('Database command: %s', 'schedules')]
        log_debug.assert_has_calls(calls, any_order=True)

    @pytest.mark.asyncio
    async def test_stop(self, mocker):
        # TODO: Mandatory - Add negative tests for full code coverage
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        log_info = mocker.patch.object(scheduler._logger, "info")
        log_exception = mocker.patch.object(scheduler._logger, "exception")

        mocker.patch.object(scheduler, '_scheduler_loop', return_value=asyncio.ensure_future(mock_task()))
        mocker.patch.object(scheduler, '_resume_check_schedules', return_value=asyncio.ensure_future(mock_task()))
        mocker.patch.object(scheduler, '_purge_tasks_task', return_value=asyncio.ensure_future(asyncio.sleep(.1)))
        mocker.patch.object(scheduler, '_scheduler_loop_task', return_value=asyncio.ensure_future(asyncio.sleep(.1)))
        current_time = time.time()
        mocker.patch.multiple(scheduler, _core_management_port=9999,
                              _core_management_host="0.0.0.0",
                              _start_time=current_time - 3600,
                              _paused=False,
                              _task_processes={})

        # WHEN
        retval = await scheduler.stop()

        # THEN
        assert retval is True
        assert scheduler._schedule_executions is None
        assert scheduler._task_processes is None
        assert scheduler._schedules is None
        assert scheduler._process_scripts is None
        assert scheduler._ready is False
        assert scheduler._paused is False
        assert scheduler._start_time is None
        calls = [call('Processing stop request'), call('Stopped')]
        log_info.assert_has_calls(calls, any_order=True)

        # TODO: Find why these exceptions are being raised despite mocking _purge_tasks_task, _scheduler_loop_task
        calls = [call('An exception was raised by Scheduler._purge_tasks %s', "object MagicMock can't be used in 'await' expression"),
                 call('An exception was raised by Scheduler._scheduler_loop %s', "object MagicMock can't be used in 'await' expression")]
        log_exception.assert_has_calls(calls)

    @pytest.mark.asyncio
    async def test_get_scheduled_processes(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        await scheduler._get_process_scripts()
        mocker.patch.object(scheduler, '_ready', True)

        # WHEN
        processes = await scheduler.get_scheduled_processes()

        # THEN
        assert len(scheduler._storage_async.scheduled_processes) == len(processes)

    @pytest.mark.asyncio
    async def test_schedule_row_to_schedule(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        schedule_id = uuid.uuid4()
        schedule_row = scheduler._ScheduleRow(
            id=schedule_id,
            name='Test Schedule',
            type=Schedule.Type.INTERVAL,
            day=0,
            time=0,
            repeat=10,
            repeat_seconds=10,
            exclusive=False,
            enabled=True,
            process_name='TestProcess')

        # WHEN
        schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)

        # THEN
        assert isinstance(schedule, Schedule)
        assert schedule.schedule_id == schedule_row[0]
        assert schedule.name == schedule_row[1]
        assert schedule.schedule_type == schedule_row[2]
        assert schedule_row[3] is 0  # 0 for Interval Schedule
        assert schedule_row[4] is 0  # 0 for Interval Schedule
        assert schedule.repeat == schedule_row[5]
        assert schedule.exclusive == schedule_row[7]
        assert schedule.enabled == schedule_row[8]
        assert schedule.process_name == schedule_row[9]

    @pytest.mark.asyncio
    async def test_get_schedules(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)

        # WHEN
        schedules = await scheduler.get_schedules()

        # THEN
        assert len(scheduler._storage_async.schedules) == len(schedules)

    @pytest.mark.asyncio
    async def test_get_schedule(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        schedule_id = uuid.UUID("cea17db8-6ccc-11e7-907b-a6006ad3dba0")  # purge schedule

        # WHEN
        schedule = await scheduler.get_schedule(schedule_id)

        # THEN
        assert isinstance(schedule, Schedule)
        assert schedule.schedule_id == schedule_id
        assert schedule.name == "purge"
        assert schedule.schedule_type == Schedule.Type.MANUAL
        assert schedule.repeat == datetime.timedelta(0, 3600)
        assert schedule.exclusive is True
        assert schedule.enabled is True
        assert schedule.process_name == "purge"

    @pytest.mark.asyncio
    async def test_get_schedule_exception(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        schedule_id = uuid.uuid4()

        # WHEN
        # THEN
        with pytest.raises(ScheduleNotFoundError):
            schedule = await scheduler.get_schedule(schedule_id)

    @pytest.mark.asyncio
    async def test_save_schedule_new(self, mocker):
        @asyncio.coroutine
        def mock_coro():
            return ""

        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        audit_logger = mocker.patch.object(AuditLogger, 'information', return_value=asyncio.ensure_future(mock_task()))
        first_task = mocker.patch.object(scheduler, '_schedule_first_task')
        resume_sch = mocker.patch.object(scheduler, '_resume_check_schedules')
        log_info = mocker.patch.object(scheduler._logger, "info")

        enable_schedule = mocker.patch.object(scheduler, "enable_schedule", return_value=mock_coro())
        disable_schedule = mocker.patch.object(scheduler, "disable_schedule", return_value=mock_coro())

        schedule_id = uuid.uuid4()
        schedule_row = scheduler._ScheduleRow(
            id=schedule_id,
            name='Test Schedule',
            type=Schedule.Type.INTERVAL,
            day=0,
            time=0,
            repeat=datetime.timedelta(seconds=30),
            repeat_seconds=30,
            exclusive=False,
            enabled=True,
            process_name='TestProcess')
        schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)

        # WHEN
        await scheduler.save_schedule(schedule)

        # THEN
        assert len(scheduler._storage_async.schedules) + 1 == len(scheduler._schedules)
        assert 1 == audit_logger.call_count
        calls =[call('SCHAD', {'schedule': {'name': 'Test Schedule', 'processName': 'TestProcess',
                                            'type': Schedule.Type.INTERVAL, 'repeat': 30.0, 'enabled': True,
                                            'exclusive': False}})]
        audit_logger.assert_has_calls(calls, any_order=True)
        assert 1 == first_task.call_count
        assert 1 == resume_sch.call_count
        assert 0 == enable_schedule.call_count
        assert 0 == disable_schedule.call_count

    @pytest.mark.asyncio
    async def test_save_schedule_new_with_enable_modified(self, mocker):
        @asyncio.coroutine
        def mock_coro():
            return ""

        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        audit_logger = mocker.patch.object(AuditLogger, 'information', return_value=asyncio.ensure_future(mock_task()))
        first_task = mocker.patch.object(scheduler, '_schedule_first_task')
        resume_sch = mocker.patch.object(scheduler, '_resume_check_schedules')
        log_info = mocker.patch.object(scheduler._logger, "info")

        enable_schedule = mocker.patch.object(scheduler, "enable_schedule", return_value=mock_coro())
        disable_schedule = mocker.patch.object(scheduler, "disable_schedule", return_value=mock_coro())

        schedule_id = uuid.uuid4()
        schedule_row = scheduler._ScheduleRow(
            id=schedule_id,
            name='Test Schedule',
            type=Schedule.Type.INTERVAL,
            day=0,
            time=0,
            repeat=datetime.timedelta(seconds=30),
            repeat_seconds=30,
            exclusive=False,
            enabled=True,
            process_name='TestProcess')
        schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)

        # WHEN
        await scheduler.save_schedule(schedule, is_enabled_modified=True)

        # THEN
        assert len(scheduler._storage_async.schedules) + 1 == len(scheduler._schedules)
        assert 1 == audit_logger.call_count
        calls =[call('SCHAD', {'schedule': {'name': 'Test Schedule', 'processName': 'TestProcess',
                                            'type': Schedule.Type.INTERVAL, 'repeat': 30.0, 'enabled': True,
                                            'exclusive': False}})]
        audit_logger.assert_has_calls(calls, any_order=True)
        assert 1 == first_task.call_count
        assert 1 == resume_sch.call_count
        assert 1 == enable_schedule.call_count
        assert 0 == disable_schedule.call_count

        # WHEN
        await scheduler.save_schedule(schedule, is_enabled_modified=False)
        # THEN
        assert 1 == disable_schedule.call_count

    @pytest.mark.asyncio
    async def test_save_schedule_update(self, mocker):
        @asyncio.coroutine
        def mock_coro():
            return ""

        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        audit_logger = mocker.patch.object(AuditLogger, 'information', return_value=asyncio.ensure_future(mock_task()))
        first_task = mocker.patch.object(scheduler, '_schedule_first_task')
        resume_sch = mocker.patch.object(scheduler, '_resume_check_schedules')
        log_info = mocker.patch.object(scheduler._logger, "info")
        schedule_id = uuid.UUID("2b614d26-760f-11e7-b5a5-be2e44b06b34")  # OMF to PI North
        schedule_row = scheduler._ScheduleRow(
            id=schedule_id,
            name='Test Schedule',
            type=Schedule.Type.TIMED,
            day=1,
            time=datetime.time(),
            repeat=datetime.timedelta(seconds=30),
            repeat_seconds=30,
            exclusive=False,
            enabled=True,
            process_name='TestProcess')
        schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)

        enable_schedule = mocker.patch.object(scheduler, "enable_schedule", return_value=mock_coro())
        disable_schedule = mocker.patch.object(scheduler, "disable_schedule", return_value=mock_coro())

        # WHEN
        await scheduler.save_schedule(schedule)

        # THEN
        assert len(scheduler._storage_async.schedules) == len(scheduler._schedules)
        assert 1 == audit_logger.call_count
        calls = [call('SCHCH', {'schedule': {'name': 'Test Schedule', 'enabled': True, 'repeat': 30.0,
                                             'exclusive': False, 'day': 1, 'time': '0:0:0',
                                             'processName': 'TestProcess', 'type': Schedule.Type.TIMED}})]
        audit_logger.assert_has_calls(calls, any_order=True)
        assert 1 == first_task.call_count
        assert 1 == resume_sch.call_count
        assert 0 == enable_schedule.call_count
        assert 0 == disable_schedule.call_count

    @pytest.mark.asyncio
    async def test_save_schedule_update_with_enable_modified(self, mocker):
        @asyncio.coroutine
        def mock_coro():
            return ""

        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        audit_logger = mocker.patch.object(AuditLogger, 'information', return_value=asyncio.ensure_future(mock_task()))
        first_task = mocker.patch.object(scheduler, '_schedule_first_task')
        resume_sch = mocker.patch.object(scheduler, '_resume_check_schedules')
        log_info = mocker.patch.object(scheduler._logger, "info")
        schedule_id = uuid.UUID("2b614d26-760f-11e7-b5a5-be2e44b06b34")  # OMF to PI North
        schedule_row = scheduler._ScheduleRow(
            id=schedule_id,
            name='Test Schedule',
            type=Schedule.Type.TIMED,
            day=1,
            time=datetime.time(),
            repeat=datetime.timedelta(seconds=30),
            repeat_seconds=30,
            exclusive=False,
            enabled=True,
            process_name='TestProcess')
        schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)

        enable_schedule = mocker.patch.object(scheduler, "enable_schedule", return_value=mock_coro())
        disable_schedule = mocker.patch.object(scheduler, "disable_schedule", return_value=mock_coro())

        # WHEN
        await scheduler.save_schedule(schedule, is_enabled_modified=True)

        # THEN
        assert len(scheduler._storage_async.schedules) == len(scheduler._schedules)
        assert 1 == audit_logger.call_count
        calls = [call('SCHCH', {'schedule': {'name': 'Test Schedule', 'enabled': True, 'repeat': 30.0,
                                             'exclusive': False, 'day': 1, 'time': '0:0:0',
                                             'processName': 'TestProcess', 'type': Schedule.Type.TIMED}})]
        audit_logger.assert_has_calls(calls, any_order=True)
        assert 1 == first_task.call_count
        assert 1 == resume_sch.call_count
        assert 1 == enable_schedule.call_count
        assert 0 == disable_schedule.call_count

        # WHEN
        await scheduler.save_schedule(schedule, is_enabled_modified=False)
        # THEN
        assert 1 == disable_schedule.call_count

    @pytest.mark.asyncio
    async def test_save_schedule_exception(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        schedule_id = uuid.uuid4()
        schedule_row = scheduler._ScheduleRow(
            id=schedule_id,
            name='Test Schedule',
            type=Schedule.Type.TIMED,
            day=0,
            time=0,
            repeat=datetime.timedelta(seconds=30),
            repeat_seconds=30,
            exclusive=False,
            enabled=True,
            process_name='TestProcess')

        # WHEN
        # THEN
        with pytest.raises(ValueError) as ex:
            temp_schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)
            temp_schedule.name = None
            await scheduler.save_schedule(temp_schedule)
            del temp_schedule
        assert str(ex).endswith("name can not be empty")

        with pytest.raises(ValueError) as ex:
            temp_schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)
            temp_schedule.name = ""
            await scheduler.save_schedule(temp_schedule)
            del temp_schedule
        assert str(ex).endswith("name can not be empty")

        with pytest.raises(ValueError) as ex:
            temp_schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)
            temp_schedule.repeat = 1234
            await scheduler.save_schedule(temp_schedule)
            del temp_schedule
        assert str(ex).endswith('repeat must be of type datetime.timedelta')

        with pytest.raises(ValueError) as ex:
            temp_schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)
            temp_schedule.exclusive = None
            await scheduler.save_schedule(temp_schedule)
            del temp_schedule
        assert str(ex).endswith('exclusive can not be None')

        with pytest.raises(ValueError) as ex:
            temp_schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)
            temp_schedule.time = 1234
            await scheduler.save_schedule(temp_schedule)
            del temp_schedule
        assert str(ex).endswith('time must be of type datetime.time')

        with pytest.raises(ValueError) as ex:
            temp_schedule = scheduler._schedule_row_to_schedule(schedule_id, schedule_row)
            temp_schedule.day = 0
            temp_schedule.time = datetime.time()
            await scheduler.save_schedule(temp_schedule)
            del temp_schedule
        assert str(ex).endswith('day must be between 1 and 7')

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be done")
    async def test_remove_service_from_task_processes(self):
        pass

    @pytest.mark.asyncio
    async def test_disable_schedule(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.object(scheduler, '_schedule_first_task')
        await scheduler._get_schedules()
        mocker.patch.object(scheduler, '_ready', True)
        mocker.patch.object(scheduler, '_task_processes')
        audit_logger = mocker.patch.object(AuditLogger, 'information', return_value=asyncio.ensure_future(mock_task()))
        log_info = mocker.patch.object(scheduler._logger, "info")
        sch_id = uuid.UUID("2b614d26-760f-11e7-b5a5-be2e44b06b34")  # OMF to PI North

        # WHEN
        status, message = await scheduler.disable_schedule(sch_id)

        # THEN
        assert status is True
        assert message == "Schedule successfully disabled"
        assert (scheduler._schedules[sch_id]).id == sch_id
        assert (scheduler._schedules[sch_id]).enabled is False
        assert 2 == log_info.call_count
        calls = [call('No Task running for Schedule %s', '2b614d26-760f-11e7-b5a5-be2e44b06b34'),
                 call("Disabled Schedule '%s/%s' process '%s'\n", 'OMF to PI north',
                      '2b614d26-760f-11e7-b5a5-be2e44b06b34', 'North Readings to PI')]
        log_info.assert_has_calls(calls)
        assert 1 == audit_logger.call_count
        calls = [call('SCHCH', {'schedule': {'name': 'OMF to PI north', 'repeat': 30.0, 'enabled': False,
                                             'type': Schedule.Type.INTERVAL, 'exclusive': True,
                                             'processName': 'North Readings to PI'}})]
        audit_logger.assert_has_calls(calls, any_order=True)

    @pytest.mark.asyncio
    async def test_disable_schedule_wrong_schedule_id(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.object(scheduler, '_schedule_first_task')
        await scheduler._get_schedules()
        mocker.patch.object(scheduler, '_ready', True)
        mocker.patch.object(scheduler, '_task_processes')
        log_exception = mocker.patch.object(scheduler._logger, "exception")
        random_schedule_id = uuid.uuid4()

        # WHEN
        await scheduler.disable_schedule(random_schedule_id)

        # THEN
        log_params = "No such Schedule %s", str(random_schedule_id)
        log_exception.assert_called_with(*log_params)

    @pytest.mark.asyncio
    async def test_disable_schedule_already_disabled(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.object(scheduler, '_schedule_first_task')
        await scheduler._get_schedules()
        mocker.patch.object(scheduler, '_ready', True)
        mocker.patch.object(scheduler, '_task_processes')
        log_info = mocker.patch.object(scheduler._logger, "info")
        sch_id = uuid.UUID("d1631422-9ec6-11e7-abc4-cec278b6b50a")  # backup

        # WHEN
        status, message = await scheduler.disable_schedule(sch_id)

        # THEN
        assert status is True
        assert message == "Schedule {} already disabled".format(str(sch_id))
        assert (scheduler._schedules[sch_id]).id == sch_id
        assert (scheduler._schedules[sch_id]).enabled is False
        log_params = "Schedule %s already disabled", str(sch_id)
        log_info.assert_called_with(*log_params)

    @pytest.mark.asyncio
    async def test_enable_schedule(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        sch_id = uuid.UUID("d1631422-9ec6-11e7-abc4-cec278b6b50a")  # backup
        queue_task = mocker.patch.object(scheduler, 'queue_task', return_value=asyncio.ensure_future(mock_task()))
        audit_logger = mocker.patch.object(AuditLogger, 'information', return_value=asyncio.ensure_future(mock_task()))

        # WHEN
        status, message = await scheduler.enable_schedule(sch_id)

        # THEN
        assert status is True
        assert message == "Schedule successfully enabled"
        assert (scheduler._schedules[sch_id]).id == sch_id
        assert (scheduler._schedules[sch_id]).enabled is True
        assert 1 == queue_task.call_count
        calls = [call("Enabled Schedule '%s/%s' process '%s'\n", 'backup hourly', 'd1631422-9ec6-11e7-abc4-cec278b6b50a', 'backup')]
        log_info.assert_has_calls(calls, any_order=True)
        assert 1 == audit_logger.call_count
        calls = [call('SCHCH', {'schedule': {'name': 'backup hourly', 'type': Schedule.Type.INTERVAL, 'processName': 'backup', 'exclusive': True, 'repeat': 3600.0, 'enabled': True}})]
        audit_logger.assert_has_calls(calls, any_order=True)

    @pytest.mark.asyncio
    async def test_enable_schedule_already_enabled(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        sch_id = uuid.UUID("ada12840-68d3-11e7-907b-a6006ad3dba0")  #Coap
        mocker.patch.object(scheduler, 'queue_task', return_value=asyncio.ensure_future(mock_task()))

        # WHEN
        status, message = await scheduler.enable_schedule(sch_id)

        # THEN
        assert status is True
        assert message == "Schedule is already enabled"
        assert (scheduler._schedules[sch_id]).id == sch_id
        assert (scheduler._schedules[sch_id]).enabled is True
        log_params = "Schedule %s already enabled", str(sch_id)
        log_info.assert_called_with(*log_params)

    @pytest.mark.asyncio
    async def test_enable_schedule_wrong_schedule_id(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        random_schedule_id = uuid.uuid4()

        # WHEN
        await scheduler.enable_schedule(random_schedule_id)

        # THEN
        log_params = "No such Schedule %s", str(random_schedule_id)
        log_exception.assert_called_with(*log_params)

    @pytest.mark.asyncio
    async def test_queue_task(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.object(scheduler, '_schedule_first_task')
        log_info = mocker.patch.object(scheduler._logger, "info")
        await scheduler._get_schedules()
        sch_id = uuid.UUID("cea17db8-6ccc-11e7-907b-a6006ad3dba0")  # backup

        mocker.patch.object(scheduler, '_ready', True)
        mocker.patch.object(scheduler, '_resume_check_schedules')

        # Assert that there is no task queued for this schedule at first
        with pytest.raises(KeyError) as excinfo:
            assert scheduler._schedule_executions[sch_id] is True

        # WHEN
        await scheduler.queue_task(sch_id)

        # THEN
        assert isinstance(scheduler._schedule_executions[sch_id], scheduler._ScheduleExecution)
        log_params = "Queued schedule '%s' for execution", 'purge'
        log_info.assert_called_with(*log_params)

    @pytest.mark.asyncio
    async def test_queue_task_schedule_not_found(self, mocker):
        # GIVEN
        scheduler = Scheduler()
        scheduler._storage = MockStorage(core_management_host=None, core_management_port=None)
        scheduler._storage_async = MockStorageAsync(core_management_host=None, core_management_port=None)
        mocker.patch.object(scheduler, '_schedule_first_task')
        mocker.patch.object(scheduler, '_ready', True)
        mocker.patch.object(scheduler, '_resume_check_schedules')

        # WHEN
        # THEN
        with pytest.raises(ScheduleNotFoundError) as excinfo:
            await scheduler.queue_task(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_delete_schedule(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        sch_id = uuid.UUID("d1631422-9ec6-11e7-abc4-cec278b6b50a")  # backup
        await scheduler._get_schedules()

        # Confirm no. of schedules
        assert len(scheduler._storage_async.schedules) == len(scheduler._schedules)

        mocker.patch.object(scheduler, '_ready', True)

        # WHEN
        # Now delete schedule
        await scheduler.delete_schedule(sch_id)

        # THEN
        # Now confirm there is one schedule less
        assert len(scheduler._storage_async.schedules) - 1 == len(scheduler._schedules)

    @pytest.mark.asyncio
    async def test_delete_schedule_enabled_schedule(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        sch_id = uuid.UUID("ada12840-68d3-11e7-907b-a6006ad3dba0")  #Coap
        await scheduler._get_schedules()
        mocker.patch.object(scheduler, '_ready', True)

        # Confirm there are 14 schedules
        assert len(scheduler._storage_async.schedules) == len(scheduler._schedules)

        # WHEN
        # Now delete schedule
        with pytest.raises(RuntimeWarning):
            await scheduler.delete_schedule(sch_id)

        # THEN
        # Now confirm no schedule is deleted
        assert len(scheduler._storage_async.schedules) == len(scheduler._schedules)
        assert 1 == log_exception.call_count
        log_params = 'Attempt to delete an enabled Schedule %s. Not deleted.', str(sch_id)
        log_exception.assert_called_with(*log_params)

    @pytest.mark.asyncio
    async def test_delete_schedule_exception(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        log_debug = mocker.patch.object(scheduler._logger, 'debug', side_effect=Exception())
        sch_id = uuid.UUID("d1631422-9ec6-11e7-abc4-cec278b6b50a")  # backup

        # WHEN
        # THEN
        with pytest.raises(ScheduleNotFoundError) as excinfo:
            await scheduler.delete_schedule(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_delete_schedule_not_found(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)

        # WHEN
        # THEN
        with pytest.raises(ScheduleNotFoundError) as excinfo:
            await scheduler.delete_schedule(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_running_tasks(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)

        # Assert that there is no task queued for schedule
        with pytest.raises(KeyError) as excinfo:
            assert scheduler._schedule_executions[schedule.id] is True

        # Now queue task and assert that the task has been queued
        await scheduler.queue_task(schedule.id)
        assert isinstance(scheduler._schedule_executions[schedule.id], scheduler._ScheduleExecution)

        # Confirm that no task has started yet
        assert 0 == len(scheduler._schedule_executions[schedule.id].task_processes)

        await scheduler._start_task(schedule)

        # Confirm that task has started
        assert 1 == len(scheduler._schedule_executions[schedule.id].task_processes)

        # WHEN
        tasks = await scheduler.get_running_tasks()

        # THEN
        assert 1 == len(tasks)
        assert schedule.process_name == tasks[0].process_name
        assert tasks[0].reason is None
        assert tasks[0].state == Task.State.RUNNING
        assert tasks[0].cancel_requested is None
        assert tasks[0].start_time is not None
        assert tasks[0].end_time is None
        assert tasks[0].exit_code is None

    @pytest.mark.asyncio
    async def test_get_task(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)

        # Assert that there is no North task queued for schedule
        with pytest.raises(KeyError) as excinfo:
            assert scheduler._schedule_executions[schedule.id] is True

        # Now queue task and assert that the North task has been queued
        await scheduler.queue_task(schedule.id)
        assert isinstance(scheduler._schedule_executions[schedule.id], scheduler._ScheduleExecution)

        # Confirm that no task has started yet
        assert 0 == len(scheduler._schedule_executions[schedule.id].task_processes)

        await scheduler._start_task(schedule)

        # Confirm that task has started
        assert 1 == len(scheduler._schedule_executions[schedule.id].task_processes)
        task_id = list(scheduler._schedule_executions[schedule.id].task_processes.keys())[0]

        # WHEN
        task = await scheduler.get_task(task_id)

        # THEN
        assert schedule.process_name == task.process_name
        assert task.reason is ''
        assert task.state is not None
        assert task.cancel_requested is None
        assert task.start_time is not None
        assert task.end_time is not None
        assert task.exit_code is '0'

    @pytest.mark.skip("Need a suitable fixture")
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)

        # WHEN
        # THEN
        with pytest.raises(TaskNotFoundError) as excinfo:
            tasks = await scheduler.get_task(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_task_exception(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        log_debug = mocker.patch.object(scheduler._logger, 'debug', side_effect=Exception())

        # WHEN
        # THEN
        task_id = uuid.uuid4()
        with pytest.raises(Exception) as excinfo:
            await scheduler.get_task(task_id)

        # THEN
        payload = {"return": ["id", "process_name", "state", {"alias": "start_time", "format": "YYYY-MM-DD HH24:MI:SS.MS", "column": "start_time"}, {"alias": "end_time", "format": "YYYY-MM-DD HH24:MI:SS.MS", "column": "end_time"}, "reason", "exit_code"], "where": {"column": "id", "condition": "=", "value": str(task_id)}}
        args, kwargs = log_exception.call_args
        assert 'Query failed: %s' == args[0]
        p = json.loads(args[1])
        assert payload == p

    @pytest.mark.asyncio
    async def test_get_tasks(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)

        # Assert that there is no North task queued for schedule
        with pytest.raises(KeyError) as excinfo:
            assert scheduler._schedule_executions[schedule.id] is True

        # Now queue task and assert that the North task has been queued
        await scheduler.queue_task(schedule.id)
        assert isinstance(scheduler._schedule_executions[schedule.id], scheduler._ScheduleExecution)

        # Confirm that no task has started yet
        assert 0 == len(scheduler._schedule_executions[schedule.id].task_processes)

        await scheduler._start_task(schedule)

        # Confirm that task has started
        assert 1 == len(scheduler._schedule_executions[schedule.id].task_processes)
        task_id = list(scheduler._schedule_executions[schedule.id].task_processes.keys())[0]

        # WHEN
        tasks = await scheduler.get_tasks()

        # THEN
        assert schedule.process_name == tasks[0].process_name
        assert tasks[0].reason is ''
        assert tasks[0].state is not None
        assert tasks[0].cancel_requested is None
        assert tasks[0].start_time is not None
        assert tasks[0].end_time is not None
        assert tasks[0].exit_code is '0'

    @pytest.mark.asyncio
    async def test_get_tasks_exception(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        log_debug = mocker.patch.object(scheduler._logger, 'debug', side_effect=Exception())

        # WHEN
        with pytest.raises(Exception) as excinfo:
            tasks = await scheduler.get_tasks()

        # THEN
        payload = {"return": ["id", "process_name", "state", {"alias": "start_time", "column": "start_time", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"alias": "end_time", "column": "end_time", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, "reason", "exit_code"], "limit": 100}
        args, kwargs = log_exception.call_args
        assert 'Query failed: %s' == args[0]
        p = json.loads(args[1])
        assert payload == p

    @pytest.mark.asyncio
    async def test_cancel_task_all_ok(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)

        # Assert that there is no task queued for schedule
        with pytest.raises(KeyError) as excinfo:
            assert scheduler._schedule_executions[schedule.id] is True

        # Now queue task and assert that the task has been queued
        await scheduler.queue_task(schedule.id)
        assert isinstance(scheduler._schedule_executions[schedule.id], scheduler._ScheduleExecution)

        # Confirm that no task has started yet
        assert 0 == len(scheduler._schedule_executions[schedule.id].task_processes)
        await scheduler._start_task(schedule)

        # Confirm that task has started
        assert 1 == len(scheduler._schedule_executions[schedule.id].task_processes)
        task_id = list(scheduler._schedule_executions[schedule.id].task_processes.keys())[0]

        # Confirm that cancel request has not been made
        assert scheduler._schedule_executions[schedule.id].task_processes[task_id].cancel_requested is None

        # WHEN
        await scheduler.cancel_task(task_id)

        # THEN
        assert scheduler._schedule_executions[schedule.id].task_processes[task_id].cancel_requested is not None
        assert 3 == log_info.call_count
        args, kwargs = log_info.call_args_list[0]
        assert ("Queued schedule '%s' for execution", 'OMF to PI north') == args
        args, kwargs = log_info.call_args_list[1]
        assert "Process started: Schedule '%s' process '%s' task %s pid %s, %s running tasks\n%s" in args
        assert 'OMF to PI north' in args
        assert 'North Readings to PI' in args
        args, kwargs = log_info.call_args_list[2]
        assert "Stopping process: Schedule '%s' process '%s' task %s pid %s\n%s" in args
        assert 'OMF to PI north' in args
        assert 'North Readings to PI' in args

    @pytest.mark.asyncio
    async def test_cancel_task_exception(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)

        # WHEN
        # THEN
        with pytest.raises(TaskNotRunningError) as excinfo:
            await scheduler.cancel_task(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_not_ready_and_paused(self, mocker):
        # GIVEN
        scheduler, schedule, log_info, log_exception, log_error, log_debug = await self.scheduler_fixture(mocker)
        mocker.patch.object(scheduler, '_ready', False)
        mocker.patch.object(scheduler, '_paused', True)

        # WHEN
        # THEN
        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.start()

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.get_scheduled_processes()

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.get_schedules()

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.get_schedule(uuid.uuid4())

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.save_schedule(Schedule(Schedule.Type.INTERVAL))

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.disable_schedule(uuid.uuid4())

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.enable_schedule(uuid.uuid4())

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.queue_task(uuid.uuid4())

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.delete_schedule(uuid.uuid4())

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.get_running_tasks()

        with pytest.raises(NotReadyError) as excinfo:
            await scheduler.cancel_task(uuid.uuid4())

    @pytest.mark.skip("_terminate_child_processes() not fit for unit test.")
    @pytest.mark.asyncio
    async def test__terminate_child_processes(self, mocker):
        pass

class MockStorage(StorageClientAsync):
    def __init__(self, core_management_host=None, core_management_port=None):
        super().__init__(core_management_host, core_management_port)

    def _get_storage_service(self, host, port):
        return {
                "id": uuid.uuid4(),
                "name": "FogLAMP Storage",
                "type": "Storage",
                "service_port": 9999,
                "management_port": 9999,
                "address": "0.0.0.0",
                "protocol": "http"
        }

class MockStorageAsync(StorageClientAsync):
    schedules = [
        {
            "id": "cea17db8-6ccc-11e7-907b-a6006ad3dba0",
            "process_name": "purge",
            "schedule_name": "purge",
            "schedule_type": 4,
            "schedule_interval": "01:00:00",
            "schedule_time": "",
            "schedule_day": 0,
            "exclusive": "t",
            "enabled": "t"
        },
        {
            "id": "2176eb68-7303-11e7-8cf7-a6006ad3dba0",
            "process_name": "stats collector",
            "schedule_name": "stats collection",
            "schedule_type": 2,
            "schedule_interval": "00:00:15",
            "schedule_time": "00:00:15",
            "schedule_day": 3,
            "exclusive": "f",
            "enabled": "t"
        },
        {
            "id": "d1631422-9ec6-11e7-abc4-cec278b6b50a",
            "process_name": "backup",
            "schedule_name": "backup hourly",
            "schedule_type": 3,
            "schedule_interval": "01:00:00",
            "schedule_time": "",
            "schedule_day": 0,
            "exclusive": "t",
            "enabled": "f"
        },
        {
            "id": "ada12840-68d3-11e7-907b-a6006ad3dba0",
            "process_name": "COAP",
            "schedule_name": "COAP listener south",
            "schedule_type": 1,
            "schedule_interval": "00:00:00",
            "schedule_time": "",
            "schedule_day": 0,
            "exclusive": "t",
            "enabled": "t"
        },
        {
            "id": "2b614d26-760f-11e7-b5a5-be2e44b06b34",
            "process_name": "North Readings to PI",
            "schedule_name": "OMF to PI north",
            "schedule_type": 3,
            "schedule_interval": "00:00:30",
            "schedule_time": "",
            "schedule_day": 0,
            "exclusive": "t",
            "enabled": "t"
        },
        {
            "id": "5d7fed92-fb9a-11e7-8c3f-9a214cf093ae",
            "process_name": "North Readings to OCS",
            "schedule_name": "OMF to OCS north",
            "schedule_type": 3,
            "schedule_interval": "1 day 00:00:40",
            "schedule_time": "",
            "schedule_day": 0,
            "exclusive": "t",
            "enabled": "f"
        },
    ]

    scheduled_processes = [
        {
            "name": "purge",
            "script": [
                "tasks/purge"
            ]
        },
        {
            "name": "stats collector",
            "script": [
                "tasks/statistics"
            ]
        },
        {
            "name": "backup",
            "script": [
                "tasks/backup_postgres"
            ]
        },
        {
            "name": "COAP",
            "script": [
                "services/south"
            ]
        },
        {
            "name": "North Readings to PI",
            "script": [
                "tasks/north",
                "--stream_id",
                "1",
                "--debug_level",
                "1"
            ]
        },
        {
            "name": "North Readings to OCS",
            "script": [
                "tasks/north",
                "--stream_id",
                "4",
                "--debug_level",
                "1"
            ]
        },
    ]

    tasks = [
        {
            "id": "259b8570-65c1-4b92-8c62-e9642631a600",
            "process_name": "North Readings to PI",
            "state": 1,
            "start_time": "2018-02-06 13:28:14.477868",
            "end_time": "2018-02-06 13:28:14.856375",
            "exit_code": "0",
            "reason": ""
        }
    ]

    def __init__(self, core_management_host=None, core_management_port=None):
        super().__init__(core_management_host, core_management_port)

    def _get_storage_service(self, host, port):
        return {
                "id": uuid.uuid4(),
                "name": "FogLAMP Storage",
                "type": "Storage",
                "service_port": 9999,
                "management_port": 9999,
                "address": "0.0.0.0",
                "protocol": "http"
        }

    @classmethod
    async def insert_into_tbl(cls, table_name, payload):
        pass

    @classmethod
    async def update_tbl(cls, table_name, payload):
        # Only valid for test_save_schedule_update
        if table_name == "schedules":
            return {"count": 1}

    @classmethod
    async def delete_from_tbl(cls, table_name, condition=None):
        pass

    @classmethod
    async def query_tbl_with_payload(cls, table_name, query_payload):
        if table_name == 'tasks':
            return {
                "count": len(MockStorageAsync.tasks),
                "rows": MockStorageAsync.tasks
            }

    @classmethod
    async def query_tbl(cls, table_name, query=None):
        if table_name == 'schedules':
            return {
                "count": len(MockStorageAsync.schedules),
                "rows": MockStorageAsync.schedules
            }

        if table_name == 'scheduled_processes':
            return {
                "count": len(MockStorageAsync.scheduled_processes),
                "rows": MockStorageAsync.scheduled_processes
            }
