# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import uuid
import asyncio

import pytest

from foglamp.core.scheduler import Scheduler, StartUpSchedule

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
            startup_schedule = StartUpSchedule()
            startup_schedule.schedule_id = uuid.uuid4()
            startup_schedule.name = 'test1'

            startup_schedule.process_name = "sleep10"
            await scheduler.save_schedule(startup_schedule)

            # TODO: Re-read the task and check the type (need API support)

            await asyncio.sleep(1)

            # TODO: check for task created (need API support)

            await asyncio.sleep(12)

            # TODO: check for task exited (need API support)

            startup_schedule.name = 'test1 updated'
            await scheduler.save_schedule(startup_schedule)

            # TODO: check for update (need API support)

        finally:
            await scheduler.stop()


