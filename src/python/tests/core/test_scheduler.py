# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import datetime

import pytest

from foglamp import logger
from foglamp.core.scheduler import Scheduler, IntervalSchedule


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestScheduler:
    @pytest.mark.asyncio
    async def test1(self):
        scheduler = Scheduler()

        await scheduler.reset_for_testing()
        await scheduler.start()

        try:
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

            await scheduler.queue_task(interval_schedule)
            await asyncio.sleep(10)

            # TODO: check for task exited (need API support)

        except Exception as e:
            logger.setup(__name__).exception(e)
        finally:
            while True:
                try:
                    await scheduler.stop()
                    break
                except TimeoutError:
                    await asyncio.sleep(1)
