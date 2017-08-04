# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import datetime

import pytest
import uuid

from foglamp.core.scheduler import Scheduler, IntervalSchedule, ScheduleNotFoundError, Task


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
    async def test_save(self):
        scheduler = Scheduler()

        await scheduler.populate_test_data()
        await scheduler.start()

        interval_schedule = IntervalSchedule()
        interval_schedule.name = 'sleep1'
        interval_schedule.process_name = "sleep1"
        interval_schedule.repeat = datetime.timedelta(seconds=1)

        await scheduler.save_schedule(interval_schedule)

        # TODO: Re-read the task and check the type (need API support)

        await asyncio.sleep(10)

        # TODO: check for task created (need API support)

        # TODO: check for task exited (need API support)

        interval_schedule.name = 'sleep10 max active'
        interval_schedule.exclusive = False
        interval_schedule.process_name = 'sleep10'
        scheduler.max_active_tasks = 2

        await scheduler.save_schedule(interval_schedule)
        await asyncio.sleep(30)

        # TODO: Verify exactly 3 tasks ran

        scheduler.max_active_tasks = Scheduler.DEFAULT_MAX_ACTIVE_TASKS
        interval_schedule.repeat = datetime.timedelta(seconds=30)
        interval_schedule.process_name = 'sleep1'
        interval_schedule.name = 'manual runner'
        await scheduler.save_schedule(interval_schedule)

        await asyncio.sleep(10)

        # TODO: check for update (need API support)

        await scheduler.queue_task(interval_schedule.schedule_id)
        await asyncio.sleep(10)

        # TODO: check for task exited (need API support)

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
        interval_schedule.process_name = "sleep30"
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
