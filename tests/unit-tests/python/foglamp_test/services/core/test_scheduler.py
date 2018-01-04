# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import datetime
import os
import time
import uuid
import aiopg
import aiopg.sa
import pytest
from foglamp.services.core.scheduler.scheduler import Scheduler, _FOGLAMP_ROOT
from foglamp.services.core.scheduler.entities import IntervalSchedule, Task, Schedule, TimedSchedule, ManualSchedule, \
    StartUpSchedule
from foglamp.services.core.scheduler.exceptions import ScheduleNotFoundError

__author__ = "Terris Linenbach, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_CONNECTION_STRING = "dbname='foglamp' user='foglamp'"
# TODO: To run this test,
#       1) Do 'scripts/foglamp start' and note the management_port from syslog
#       2) Change _m_port below with the management_port
#       3) Execute this command: FOGLAMP_ENV=TEST pytest -s -vv tests/unit-tests/python/foglamp_test/services/core/test_scheduler.py

# TODO: How to eliminate manual intervention as below when tests will run unattended at CI?
_address = '0.0.0.0'
_m_port = 46000


@pytest.allure.feature("unit")
@pytest.allure.story("scheduler")
class TestScheduler:
    _engine = None  # type: aiopg.sa.Engine

    # TODO: This test will not work if our storage engine is not Postgres. OK for today but long term we need to
    # approach this differently. We could simply use the storage layer to insert the test data.
    async def _get_connection_pool(self) -> aiopg.sa.Engine:
        """Returns a database connection pool object"""
        if self._engine is None:
            self._engine = await aiopg.sa.create_engine(_CONNECTION_STRING)
        return self._engine

    # TODO: Think of a better location for sleep.py + specify location with reference to FOGLAMP_ROOT in scheduled_processes table
    async def populate_test_data(self):
        """Delete all schedule-related tables and insert processes for testing"""
        async with (await self._get_connection_pool()).acquire() as conn:
            await conn.execute('delete from foglamp.tasks')
            await conn.execute('delete from foglamp.schedules')
            await conn.execute('delete from foglamp.scheduled_processes')
            await conn.execute(
                "insert into foglamp.scheduled_processes(name, script) values('sleep1', '[\"python3\", " + '"' +
                _FOGLAMP_ROOT + "/scripts/sleep.py\", \"1\"]')")
            await conn.execute(
                "insert into foglamp.scheduled_processes(name, script) values('sleep10', '[\"python3\",  " +  '"' +
                _FOGLAMP_ROOT + "/scripts/sleep.py\", \"10\"]')")
            await conn.execute(
                "insert into foglamp.scheduled_processes(name, script) values('sleep30', '[\"python3\", " +  '"' +
                _FOGLAMP_ROOT + "/scripts/sleep.py\", \"30\"]')")
            await conn.execute(
                "insert into foglamp.scheduled_processes(name, script) values('sleep5', '[\"python3\",  " +  '"' +
                _FOGLAMP_ROOT + "/scripts/sleep.py\", \"5\"]')")

    @staticmethod
    async def stop_scheduler(scheduler: Scheduler) -> None:
        """stop the schedule process - called at the end of each test"""
        while True:
            try:
                await scheduler.stop()  # Call the stop command
                break
            except TimeoutError:
                await asyncio.sleep(1)

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test that stop_scheduler actually works"""
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # Set schedule interval
        interval_schedule = IntervalSchedule()
        interval_schedule.exclusive = False
        interval_schedule.enabled = True
        interval_schedule.name = 'sleep1'
        interval_schedule.process_name = "sleep1"
        interval_schedule.repeat = datetime.timedelta(seconds=1)  # Set frequency of

        await scheduler.save_schedule(interval_schedule)  # Save schedule updates
        await asyncio.sleep(10)

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_interval_none_repeat(self):
        """Tests an interval schedule where repeat is None
        :assert:
            A task starts immediately and doesn't repeat
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # assert that the schedule type is interval
        interval_schedule = IntervalSchedule()
        assert interval_schedule.schedule_type == Schedule.Type.INTERVAL

        interval_schedule.name = 'sleep10'
        interval_schedule.process_name = "sleep10"
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(1)
        # Assert only 1 task is running
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        await asyncio.sleep(12)
        # Assert only 1 task is running
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_create_interval(self):
        """Test the creation of a new schedule interval
        :assert:
            The interval type of the schedule
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # assert that the schedule type is interval
        interval_schedule = IntervalSchedule()
        assert interval_schedule.schedule_type == Schedule.Type.INTERVAL

        interval_schedule.name = 'sleep10'
        interval_schedule.process_name = "sleep10"
        interval_schedule.repeat = datetime.timedelta(seconds=1)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_modify_schedule_type(self):
        """Test modifying the type of a schedule
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'sleep10'
        interval_schedule.process_name = 'sleep10'
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        manual_schedule = ManualSchedule()
        manual_schedule.schedule_id = interval_schedule.schedule_id
        manual_schedule.name = 'manual'
        manual_schedule.process_name = 'sleep10'
        manual_schedule.repeat = datetime.timedelta(seconds=0)
        manual_schedule.enabled = True

        await scheduler.save_schedule(manual_schedule)

        # Assert: only 1 task is running
        schedule = await scheduler.get_schedule(manual_schedule.schedule_id)

        assert isinstance(schedule, ManualSchedule)

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_update(self):
        """Test update of a running task
        :assert:
            the number of tasks running
            information regarding the process running
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'sleep10'
        interval_schedule.process_name = "sleep10"
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)  # Save update on _scheduler

        await asyncio.sleep(1)
        # Assert only 1 task is running
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        # Update 'updated' schedule interval
        interval_schedule.name = 'updated'
        interval_schedule.process_name = "sleep1"
        interval_schedule.repeat = datetime.timedelta(seconds=5)  # Set time interval to 5 sec
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)  # Save update on _scheduler
        await asyncio.sleep(6)

        # Assert: only 1 task is running
        tasks = await scheduler.get_running_tasks()  # list of current running tasks
        assert len(tasks) == 1

        interval_schedule.exclusive = False
        await scheduler.save_schedule(interval_schedule)

        # Check able to get same schedule after restart
        # Check fields have been modified
        await self.stop_scheduler(scheduler)
        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        schedule = await scheduler.get_schedule(interval_schedule.schedule_id)

        # Make sure that the values used by schedule are as expected
        assert schedule.process_name == 'sleep1'
        assert schedule.name == 'updated'
        assert schedule.repeat.seconds == 5
        assert not schedule.exclusive

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_startup_schedule(self):
        """Test startup of _scheduler
        :assert:
            the number of running tasks
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # Declare schedule startup, and execute
        startup_schedule = StartUpSchedule()  # A scheduled process of the _scheduler
        startup_schedule.name = 'startup schedule'
        startup_schedule.process_name = 'sleep30'
        startup_schedule.repeat = datetime.timedelta(seconds=0)  # set no repeat to startup
        startup_schedule.enabled = True

        await scheduler.save_schedule(startup_schedule)

        await asyncio.sleep(1)
        # Assert no tasks ar running
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 0

        await scheduler.get_schedule(startup_schedule.schedule_id)  # ID of the schedule startup

        await self.stop_scheduler(scheduler)

        scheduler = Scheduler()
        await scheduler.start()

        await asyncio.sleep(2)
        # Assert only 1 task is running
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        scheduler.max_running_tasks = 0  # set that no tasks would run
        await scheduler.cancel_task(tasks[0].task_id)

        await asyncio.sleep(2)

        # Assert no tasks are running
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 0

        scheduler.max_running_tasks = 1

        await asyncio.sleep(2)

        # Assert a single task is running
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_manual_schedule(self):
        """Test manually ran scheduled processes
        :assert:
            The number of running processes
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # Declare manual interval schedule
        manual_schedule = ManualSchedule()
        manual_schedule.name = 'manual task'
        manual_schedule.process_name = 'sleep10'
        manual_schedule.repeat = datetime.timedelta(seconds=0)
        manual_schedule.enabled = True

        await scheduler.save_schedule(manual_schedule)
        manual_schedule = await scheduler.get_schedule(manual_schedule.schedule_id)

        await scheduler.queue_task(manual_schedule.schedule_id)  # Added a task to the _scheduler queue
        await asyncio.sleep(5)

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_max_processes(self):
        """Test the maximum number of running processes
        :assert:
            the number of running processes
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # 2 maximum tasks

        # 1 runs at 1 second
        # 2 runs at 2 seconds
        # 3 runs at 11 seconds
        # 4 runs at 12 seconds
        # 5 runs at 21 seconds
        # 6 runs at 22 seconds
        # 7 runs at 31 seconds
        # 8 runs at 32 seconds
        # Total: 6

        scheduler.max_running_tasks = 2  # set the maximum number of running tasks in parallel

        # Set interval schedule configuration
        interval_schedule = IntervalSchedule()
        interval_schedule.repeat = datetime.timedelta(seconds=1)
        interval_schedule.name = 'max active'
        interval_schedule.exclusive = False
        interval_schedule.process_name = 'sleep10'
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(30.3)
        scheduler.max_running_tasks = 0  # set the maximum number of running tasks in parallel

        tasks = await scheduler.get_tasks(10)
        assert len(tasks) == 6

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 2

        # They end...
        await asyncio.sleep(20)

        scheduler.max_running_tasks = 10

        await asyncio.sleep(11)
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 10

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_timed_schedule(self):
        """Testing a timed schedule using a specific timestamp (in seconds)
        :assert:
            Number of running tasks
            The values declared at for timestamp
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        timed_schedule = TimedSchedule()

        # Set current timestamp to be: Tuesday August 8 2017 8:00:00 AM PDT
        now = 1502204400
        scheduler.current_time = now

        timed_schedule.name = 'timed'
        timed_schedule.process_name = 'sleep10'
        timed_schedule.day = 2
        timed_schedule.time = datetime.time(hour=8)
        timed_schedule.repeat = datetime.timedelta(seconds=0)
        timed_schedule.enabled = True

        # Set env timezone
        os.environ["TZ"] = "PST8PDT"
        time.tzset()

        await scheduler.save_schedule(timed_schedule)
        await asyncio.sleep(1)

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        timed_schedule = await scheduler.get_schedule(uuid.UUID(str(timed_schedule.schedule_id)))

        # Assert timed_schedule values
        assert timed_schedule.time.hour == 8
        assert timed_schedule.time.minute == 0
        assert timed_schedule.time.second == 0
        assert timed_schedule.day == 2

        # Reset timezone
        del os.environ["TZ"]
        time.tzset()

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test that a scheduled process gets removed
        :assert:
            scheduled task gets removed
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # Set schedule to be interval based
        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'deletetest'
        interval_schedule.process_name = "sleep1"
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(5)

        # Delete a scheduled task
        await scheduler.delete_schedule(interval_schedule.schedule_id)

        # Assert that process was deleted
        try:
            await scheduler.delete_schedule(interval_schedule.schedule_id)
            assert False
        except ScheduleNotFoundError:
            pass

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_cancel(self):
        """Cancel a running process"""
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'cancel_test'
        interval_schedule.process_name = 'sleep30'
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(5)
        tasks = await scheduler.get_running_tasks()

        await scheduler.cancel_task(tasks[0].task_id)  # Cancel a running task

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_get_schedule(self):
        """Schedule gets retrieved
        :assert:
            Schedule is retrieved by id """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # Declare schedule
        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_schedule_test'
        interval_schedule.process_name = "sleep30"
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        # Get schedule
        schedules = await scheduler.get_schedules()
        assert len(schedules) == 1  # Assert the number of schedules

        await scheduler.get_schedule(interval_schedule.schedule_id)  # Get the schedule by schedule process ID

        # Assert that schedule is retrieved by ID
        try:
            await scheduler.get_schedule(uuid.uuid4())
            assert False
        except ScheduleNotFoundError:
            pass

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_get_task(self):
        """Test tasks exists
        :assert:
            there exists a task
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_task'
        interval_schedule.process_name = "sleep30"
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)
        await asyncio.sleep(1)

        tasks = await scheduler.get_running_tasks()  # retrieve list running tasks
        assert len(tasks)

        task = await scheduler.get_task(str(tasks[0].task_id))
        assert task  # assert there exists a task

        await self.stop_scheduler(scheduler)

    @pytest.mark.skip(reason="This test needs total revamping and redesign in light of new get_tasks()")
    @pytest.mark.asyncio
    async def test_get_tasks(self):
        """Get list of tasks
        :assert:
            Number of running tasks
            The state of tasks
            the start time of a given task
        """
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # declare _scheduler task
        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_tasks'
        interval_schedule.process_name = "sleep5"
        interval_schedule.repeat = datetime.timedelta(seconds=1)
        interval_schedule.exclusive = False
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(15)

        # Assert running tasks
        tasks = await scheduler.get_tasks(
            where=["state", "=", int(Task.State.INTERRUPTED)])
        assert not tasks

        tasks = await scheduler.get_tasks(
            where=["end_time", "=", 'NULL'])
        assert tasks

        tasks = await scheduler.get_tasks(limit=50)
        states = [int(task.state) for task in tasks]

        assert len(tasks) > 1
        assert int(Task.State.RUNNING) in states
        assert int(Task.State.COMPLETE) in states

        tasks = await scheduler.get_tasks(1)
        assert len(tasks) == 1

        tasks = await scheduler.get_tasks(
            where=["state", "=", int(Task.State.RUNNING)],
            sort=[["state", "desc"]], offset=50)
        assert not tasks

        tasks = await scheduler.get_tasks(
            where=["state", "=", int(Task.State.RUNNING)],
            sort=[["state", "desc"], ["start_time", "asc"]])
        assert tasks

        tasks = await scheduler.get_tasks(
            or_where=[["state", "=", int(Task.State.RUNNING)], ["state", "=", int(Task.State.RUNNING)]])
        assert tasks

        tasks = await scheduler.get_tasks(
            and_where=[["state", "=", int(Task.State.RUNNING)], ["state", "=", int(Task.State.RUNNING)]])
        assert tasks

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_purge_tasks(self):
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'purge_task'
        interval_schedule.process_name = "sleep5"
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        # interval_schedule.repeat = datetime.timedelta(seconds=30)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(1)
        tasks = await scheduler.get_tasks(5)
        assert tasks

        scheduler.max_running_tasks = 0
        await asyncio.sleep(7)

        scheduler.max_completed_task_age = datetime.timedelta(seconds=1)
        await scheduler.purge_tasks()

        tasks = await scheduler.get_tasks(5)
        assert not tasks
        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_enable_schedule(self):
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # Declare schedule
        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'enable_schedule_test'
        interval_schedule.process_name = "sleep5"
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = False

        await scheduler.save_schedule(interval_schedule)

        # Get schedule
        schedules = await scheduler.get_schedules()
        assert len(schedules) == 1  # Assert the number of schedules
        assert schedules[0].enabled is False

        # Enable Schedule
        retval, reason = await scheduler.enable_schedule(interval_schedule.schedule_id)
        assert retval

        # Confirm enabled changed
        schedules = await scheduler.get_schedules()
        assert len(schedules) == 1  # Assert the number of schedules
        assert schedules[0].enabled is True

        await asyncio.sleep(5)

        # assert there exists a task
        tasks = await scheduler.get_running_tasks()  # retrieve list running tasks
        assert len(tasks)

        task = await scheduler.get_task(tasks[0].task_id)
        assert task

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_enable_schedule_wrong_schedule_id(self):
        with pytest.raises(ScheduleNotFoundError) as excinfo:
            scheduler = Scheduler(_address, _m_port)
            await scheduler.start()
            random_schedule_id = uuid.uuid4()
            await scheduler.enable_schedule(random_schedule_id)

    @pytest.mark.asyncio
    async def test_disable_schedule(self):
        await self.populate_test_data()  # Populate data in foglamp.scheduled_processes

        scheduler = Scheduler(_address, _m_port)
        await scheduler.start()

        # Declare schedule
        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'disable_schedule_test'
        interval_schedule.process_name = "sleep5"
        interval_schedule.repeat = datetime.timedelta(seconds=0)
        interval_schedule.enabled = True

        await scheduler.save_schedule(interval_schedule)

        # Get schedule
        schedules = await scheduler.get_schedules()
        assert len(schedules) == 1  # Assert the number of schedules
        assert schedules[0].enabled is True

        await asyncio.sleep(5)

        # assert there exists a task
        tasks = await scheduler.get_running_tasks()  # retrieve list running tasks
        assert len(tasks)

        task = await scheduler.get_task(tasks[0].task_id)
        assert task

        # Disable Schedule
        retval, reason = await scheduler.disable_schedule(interval_schedule.schedule_id)
        assert retval

        # Confirm enabled changed
        schedules = await scheduler.get_schedules()
        assert len(schedules) == 1  # Assert the number of schedules
        assert schedules[0].enabled is False

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_disable_schedule_wrong_schedule_id(self):
        with pytest.raises(ScheduleNotFoundError) as excinfo:
            scheduler = Scheduler(_address, _m_port)
            await scheduler.start()
            random_schedule_id = uuid.uuid4()
            await scheduler.disable_schedule(random_schedule_id)
