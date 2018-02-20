# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/services/core/scheduler/entities.py """

import pytest
from foglamp.services.core.scheduler.entities import *

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "scheduler")
class TestSchedulerEntities:
    def test_ScheduledProcess(self):
        scheduled_process = ScheduledProcess()
        assert scheduled_process.name is None
        assert scheduled_process.script is None

    def test_Schedule(self):
        assert isinstance(Schedule.Type(2), IntEnum)
        schedule = Schedule(Schedule.Type.STARTUP)
        assert schedule.schedule_id is None
        assert schedule.name is None
        assert schedule.exclusive is True
        assert schedule.enabled is False
        assert schedule.repeat is None
        assert schedule.process_name is None
        assert schedule.schedule_type == 1

    def test_StartUpSchedule(self):
        startup_schedule = StartUpSchedule()
        assert startup_schedule.schedule_id is None
        assert startup_schedule.name is None
        assert startup_schedule.exclusive is True
        assert startup_schedule.enabled is False
        assert startup_schedule.repeat is None
        assert startup_schedule.process_name is None
        assert startup_schedule.schedule_type == 1
        with pytest.raises(AttributeError):
            assert startup_schedule.day is None
            assert startup_schedule.time is None

    def test_TimedSchedule(self):
        timed_schedule = TimedSchedule()
        assert timed_schedule.schedule_id is None
        assert timed_schedule.name is None
        assert timed_schedule.exclusive is True
        assert timed_schedule.enabled is False
        assert timed_schedule.repeat is None
        assert timed_schedule.process_name is None
        assert timed_schedule.schedule_type == 2
        assert timed_schedule.day is None
        assert timed_schedule.time is None

    def test_IntervalSchedule(self):
        interval_schedule = IntervalSchedule()
        assert interval_schedule.schedule_id is None
        assert interval_schedule.name is None
        assert interval_schedule.exclusive is True
        assert interval_schedule.enabled is False
        assert interval_schedule.repeat is None
        assert interval_schedule.process_name is None
        assert interval_schedule.schedule_type == 3
        with pytest.raises(AttributeError):
            assert interval_schedule.day is None
            assert interval_schedule.time is None

    def test_ManualSchedule(self):
        manual_schedule = ManualSchedule()
        assert manual_schedule.schedule_id is None
        assert manual_schedule.name is None
        assert manual_schedule.exclusive is True
        assert manual_schedule.enabled is False
        assert manual_schedule.repeat is None
        assert manual_schedule.process_name is None
        assert manual_schedule.schedule_type == 4
        with pytest.raises(AttributeError):
            assert manual_schedule.day is None
            assert manual_schedule.time is None

    def test_Task(self):
        assert isinstance(Task.State(2), IntEnum)
        task = Task()
        assert task.task_id is None
        assert task.process_name is None
        assert task.reason is None
        assert task.state is None
        assert task.cancel_requested is None
        assert task.start_time is None
        assert task.end_time is None
        assert task.exit_code is None
