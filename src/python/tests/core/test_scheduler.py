# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import datetime
import os
import time
import uuid

import pytest

from foglamp.core.scheduler import (Scheduler, IntervalSchedule, ScheduleNotFoundError, Task,
                                    Schedule, TimedSchedule, ManualSchedule, StartUpSchedule, Where)


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestScheduler:
    @staticmethod
    async def stop_scheduler(scheduler: Scheduler)->None:
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
        scheduler = Scheduler()  # Declare schedule

        await scheduler.populate_test_data()  # Populate data in foglamp.scheduled_processes
        await scheduler.start()  # Start scheduler

        # Set schedule interval
        interval_schedule = IntervalSchedule()
        interval_schedule.exclusive = False
        interval_schedule.name = 'sleep1'
        interval_schedule.process_name = "sleep1"
        interval_schedule.repeat = datetime.timedelta(seconds=1)  # Set frequency of

        await scheduler.save_schedule(interval_schedule)  # Save schedule updates
        await asyncio.sleep(10)

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_create_interval(self):
        """Test the creation of a new schedule interval
        :assert:
            The interval type of the schedule
        """
        scheduler = Scheduler()

        await scheduler.populate_test_data()  # Populate data in foglamp.scheduled_processes
        await scheduler.start()

        # assert that the schedule type is interval
        interval_schedule = IntervalSchedule()
        assert interval_schedule.schedule_type == Schedule.Type.INTERVAL

        interval_schedule.name = 'sleep10'
        interval_schedule.process_name = "sleep10"
        interval_schedule.repeat = datetime.timedelta(seconds=1)

        await scheduler.save_schedule(interval_schedule)

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_update(self):
        """Test update of a running task
        :assert:
            the number of tasks running
            information regarding the process running
        """
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'sleep10'
        interval_schedule.process_name = "sleep10"

        await scheduler.save_schedule(interval_schedule)  # Save update on scheduler

        await asyncio.sleep(1)
        # Assert only 1 task is running
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1  

        # Update 'updated' schedule interval
        interval_schedule.name = 'updated'
        interval_schedule.process_name = "sleep1"
        interval_schedule.repeat = datetime.timedelta(seconds=5)  # Set time interval to 5 sec

        await scheduler.save_schedule(interval_schedule)  # Save update on scheduler
        await asyncio.sleep(6)
        
        # Assert: only 1 task is running
        tasks = await scheduler.get_running_tasks()  # list of current running tasks
        assert len(tasks) == 1 

        interval_schedule.exclusive = False
        await scheduler.save_schedule(interval_schedule)

        # Check able to get same schedule after restart
        # Check fields have been modified
        await self.stop_scheduler(scheduler)
        scheduler = Scheduler()
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
        """Test startup of scheduler
        :assert:
            the number of running tasks
        """
        scheduler = Scheduler()

        await scheduler.populate_test_data()  # Populate data in foglamp.scheduled_processes
        await scheduler.start()  # Start scheduler

        # Declare schedule startup, and execute
        startup_schedule = StartUpSchedule()  # A scheduled process of the scheduler
        startup_schedule.name = 'startup schedule'
        startup_schedule.process_name = 'sleep30'
        startup_schedule.repeat = datetime.timedelta(seconds=0)  # set no repeat to startup

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
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        # Declare manual interval schedule
        manual_schedule = ManualSchedule()
        manual_schedule.name = 'manual task'
        manual_schedule.process_name = 'sleep10'

        await scheduler.save_schedule(manual_schedule)
        manual_schedule = await scheduler.get_schedule(manual_schedule.schedule_id)

        await scheduler.queue_task(manual_schedule.schedule_id)  # Added a task to the scheduler queue
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
        scheduler = Scheduler()

        await scheduler.populate_test_data()
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
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        timed_schedule = TimedSchedule()

        # Set current timestamp to be: Tuesday August 8 2017 8:00:00 AM PDT
        now = 1502204400
        scheduler.current_time = now

        timed_schedule.name = 'timed'
        timed_schedule.process_name = 'sleep10'
        timed_schedule.day = 2
        timed_schedule.time = datetime.time(hour=8)

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
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        # Set schedule to be interval based
        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'deletetest'
        interval_schedule.process_name = "sleep1"
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
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'cancel_test'
        interval_schedule.process_name = 'sleep30'
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
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        # Declare schedule
        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_schedule_test'
        interval_schedule.process_name = "sleep30"
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
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_task'
        interval_schedule.process_name = "sleep30"
        await scheduler.save_schedule(interval_schedule)
        await asyncio.sleep(1)

        tasks = await scheduler.get_running_tasks()  # retrieve list running tasks
        assert len(tasks)

        task = await scheduler.get_task(tasks[0].task_id)
        assert task  # assert there exists a task

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_get_tasks(self):
        """Get list of tasks
        :assert:
            Number of running tasks
            The state of tasks
            the start time of a given task
        """
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        # declare scheduler task
        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_tasks'
        interval_schedule.process_name = "sleep5"
        interval_schedule.repeat = datetime.timedelta(seconds=1)
        interval_schedule.exclusive = False
        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(15)

        # Assert running tasks
        tasks = await scheduler.get_tasks(
            where=Task.attr.state == int(Task.State.INTERRUPTED))
        assert not tasks

        tasks = await scheduler.get_tasks(
            where=(Task.attr.end_time == None))
        assert tasks

        tasks = await scheduler.get_tasks(50)
        assert len(tasks) > 1
        assert tasks[0].state == Task.State.RUNNING
        assert tasks[-1].state == Task.State.COMPLETE

        tasks = await scheduler.get_tasks(1)
        assert len(tasks) == 1

        tasks = await scheduler.get_tasks(
            where=Task.attr.state.in_(int(Task.State.RUNNING)),
            sort=[Task.attr.state.desc], offset=50)
        assert not tasks

        tasks = await scheduler.get_tasks(
            where=(Task.attr.state == int(Task.State.RUNNING)).or_(
                Task.attr.state == int(Task.State.RUNNING),
                Task.attr.state == int(Task.State.RUNNING)).and_(
                Task.attr.state.in_(int(Task.State.RUNNING)),
                Task.attr.state.in_(int(Task.State.RUNNING)).or_(
                    Task.attr.state.in_(int(Task.State.RUNNING)))),
            sort=(Task.attr.state.desc, Task.attr.start_time))
        assert tasks

        tasks = await scheduler.get_tasks(
            where=Where.or_(Task.attr.state == int(Task.State.RUNNING),
                            Task.attr.state == int(Task.State.RUNNING)))
        assert tasks

        tasks = await scheduler.get_tasks(
            where=(Task.attr.state == int(Task.State.RUNNING)) | (
                Task.attr.state.in_(int(Task.State.RUNNING))))
        assert tasks

        tasks = await scheduler.get_tasks(
            where=(Task.attr.state == int(Task.State.RUNNING)) & (
                Task.attr.state.in_(int(Task.State.RUNNING))))
        assert tasks

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_purge_tasks(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'purge_task'
        interval_schedule.process_name = "sleep5"
        # interval_schedule.repeat = datetime.timedelta(seconds=30)
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
