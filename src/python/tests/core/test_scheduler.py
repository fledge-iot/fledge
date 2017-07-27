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

        start_task = StartUpSchedule()
        start_task.schedule_id = uuid.uuid4()
        start_task.name = 'test1'

        start_task.process_name = "sleep10"

        await scheduler.save_schedule(start_task)
        await asyncio.sleep(10)
        await scheduler.stop()


