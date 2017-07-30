# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import datetime
import uuid

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
            interval_schedule.schedule_id = uuid.uuid4()
            interval_schedule.name = 'test1'
            interval_schedule.repeat = datetime.timedelta(seconds=15)

            interval_schedule.process_name = "sleep1"
            await scheduler.save_schedule(interval_schedule)

            # TODO: Re-read the task and check the type (need API support)

            await asyncio.sleep(1)

            # TODO: check for task created (need API support)

            await asyncio.sleep(10000)

            # TODO: check for task exited (need API support)

            interval_schedule.name = 'test1 updated'
            await scheduler.save_schedule(interval_schedule)

            # TODO: check for update (need API support)
        except Exception as e:
            logger.setup(__name__).exception(e)
        finally:
            while True:
                try:
                    await scheduler.stop()
                    break
                except TimeoutError:
                    await asyncio.sleep(1)
