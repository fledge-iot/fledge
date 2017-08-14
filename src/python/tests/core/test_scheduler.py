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
                                    Schedule, TimedSchedule, ManualSchedule, StartUpSchedule)


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestScheduler:
    @staticmethod
    async def stop_scheduler(scheduler: Scheduler)->None:
        while True:
            try:
                await scheduler.stop()
                break
            except TimeoutError:
                await asyncio.sleep(1)

    @pytest.mark.asyncio
    async def test_stop(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.exclusive = False
        interval_schedule.name = 'sleep1'
        interval_schedule.process_name = "sleep1"
        interval_schedule.repeat = datetime.timedelta(seconds=1)

        await scheduler.save_schedule(interval_schedule)
        await asyncio.sleep(10)

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_create_interval(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        assert interval_schedule.schedule_type == Schedule.Type.INTERVAL

        interval_schedule.name = 'sleep10'
        interval_schedule.process_name = "sleep10"
        interval_schedule.repeat = datetime.timedelta(seconds=1)

        await scheduler.save_schedule(interval_schedule)

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_update(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'sleep10'
        interval_schedule.process_name = "sleep10"

        await scheduler.save_schedule(interval_schedule)

        tasks = await scheduler.get_running_tasks()
        await asyncio.sleep(1)
        assert len(tasks) == 0

        interval_schedule.name = 'updated'
        interval_schedule.process_name = "sleep1"
        interval_schedule.repeat = datetime.timedelta(seconds=5)

        await scheduler.save_schedule(interval_schedule)
        await asyncio.sleep(6)

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        interval_schedule.exclusive = False
        await scheduler.save_schedule(interval_schedule)

        # Check able to get same schedule after restart
        # Check fields have been modified
        await self.stop_scheduler(scheduler)
        scheduler = Scheduler()
        await scheduler.start()

        schedule = await scheduler.get_schedule(interval_schedule.schedule_id)
        assert schedule.process_name == 'sleep1'
        assert schedule.name == 'updated'
        assert schedule.repeat.seconds == 5
        assert not schedule.exclusive

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_startup_schedule(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        startup_schedule = StartUpSchedule()
        startup_schedule.name = 'startup schedule'
        startup_schedule.process_name = 'sleep30'
        startup_schedule.repeat = datetime.timedelta(seconds=0)

        await scheduler.save_schedule(startup_schedule)

        await asyncio.sleep(1)
        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 0

        await scheduler.get_schedule(startup_schedule.schedule_id)

        await self.stop_scheduler(scheduler)

        scheduler = Scheduler()
        await scheduler.start()

        await asyncio.sleep(2)

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        scheduler.max_running_tasks = 0
        await scheduler.cancel_task(tasks[0].task_id)

        await asyncio.sleep(2)

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 0

        scheduler.max_running_tasks = 1

        await asyncio.sleep(2)

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_manual_schedule(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        manual_schedule = ManualSchedule()
        manual_schedule.name = 'manual task'
        manual_schedule.process_name = 'sleep10'

        await scheduler.save_schedule(manual_schedule)
        manual_schedule = await scheduler.get_schedule(manual_schedule.schedule_id)

        await scheduler.queue_task(manual_schedule.schedule_id)
        await asyncio.sleep(5)

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_max_processes(self):
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

        scheduler.max_running_tasks = 2

        interval_schedule = IntervalSchedule()
        interval_schedule.repeat = datetime.timedelta(seconds=1)
        interval_schedule.name = 'max active'
        interval_schedule.exclusive = False
        interval_schedule.process_name = 'sleep10'

        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(30.3)
        scheduler.max_running_tasks = 0

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
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        timed_schedule = TimedSchedule()

        # Tuesday August 8 2017 8:00:00 AM PDT
        now = 1502204400
        scheduler.current_time = now

        timed_schedule.name = 'timed'
        timed_schedule.process_name = 'sleep10'
        timed_schedule.day = 2
        timed_schedule.time = datetime.time(hour=8)

        os.environ["TZ"] = "PST8PDT"
        time.tzset()

        await scheduler.save_schedule(timed_schedule)
        await asyncio.sleep(1)

        tasks = await scheduler.get_running_tasks()
        assert len(tasks) == 1

        timed_schedule = await scheduler.get_schedule(
                            uuid.UUID(str(timed_schedule.schedule_id)))

        assert timed_schedule.time.hour == 8
        assert timed_schedule.time.minute == 0
        assert timed_schedule.time.second == 0
        assert timed_schedule.day == 2

        del os.environ["TZ"]
        time.tzset()

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_delete(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'deletetest'
        interval_schedule.process_name = "sleep1"
        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(5)

        await scheduler.delete_schedule(interval_schedule.schedule_id)

        try:
            await scheduler.delete_schedule(interval_schedule.schedule_id)
            assert False
        except ScheduleNotFoundError:
            pass

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_cancel(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'cancel_test'
        interval_schedule.process_name = 'sleep30'
        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(5)
        tasks = await scheduler.get_running_tasks()
        await scheduler.cancel_task(tasks[0].task_id)

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_get_schedule(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_schedule_test'
        interval_schedule.process_name = "sleep30"
        await scheduler.save_schedule(interval_schedule)

        schedules = await scheduler.get_schedules()
        assert len(schedules) == 1

        await scheduler.get_schedule(interval_schedule.schedule_id)

        try:
            await scheduler.get_schedule(uuid.uuid4())
            assert False
        except ScheduleNotFoundError:
            pass

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_get_task(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_task'
        interval_schedule.process_name = "sleep30"
        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(5)
        tasks = await scheduler.get_running_tasks()

        task = await scheduler.get_task(tasks[0].task_id)
        assert task

        await self.stop_scheduler(scheduler)

    @pytest.mark.asyncio
    async def test_get_tasks(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'get_tasks'
        interval_schedule.process_name = "sleep5"
        interval_schedule.repeat = datetime.timedelta(seconds=1)
        interval_schedule.exclusive = False
        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(15)

        tasks = await scheduler.get_tasks(50)
        assert len(tasks) > 1
        assert tasks[0].state == Task.State.RUNNING
        assert tasks[-1].state == Task.State.COMPLETE

        assert len(tasks)
        tasks2 = await scheduler.get_tasks(1)
        assert len(tasks2) == 1
        assert tasks[0].start_time == tasks2[0].start_time

        await self.stop_scheduler(scheduler)
