# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/services/core/scheduler/exceptions.py """

import uuid
import pytest
from foglamp.services.core.scheduler.exceptions import *

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "scheduler")
class TestSchedulerExceptions:
    def test_NotReadyError(self):
        with pytest.raises(NotReadyError) as excinfo:
            raise NotReadyError()
        assert excinfo.type is NotReadyError
        assert issubclass(excinfo.type, RuntimeError)

    def test_DuplicateRequestError(self):
        with pytest.raises(DuplicateRequestError) as excinfo:
            raise DuplicateRequestError()
        assert excinfo.type is DuplicateRequestError
        assert issubclass(excinfo.type, RuntimeError)

    def test_TaskNotRunningError(self):
        task_id = uuid.uuid4()
        with pytest.raises(TaskNotRunningError) as excinfo:
            raise TaskNotRunningError(task_id)
        assert excinfo.type is TaskNotRunningError
        assert issubclass(excinfo.type, RuntimeError)

        try:
            raise TaskNotRunningError(task_id)
        except Exception as ex:
            assert ex.__class__ is TaskNotRunningError
            assert issubclass(ex.__class__, TaskNotRunningError)
            assert "Task is not running: {}".format(task_id) == str(ex)

    def test_TaskNotFoundError(self):
        task_id = uuid.uuid4()
        with pytest.raises(TaskNotFoundError) as excinfo:
            raise TaskNotFoundError(task_id)
        assert excinfo.type is TaskNotFoundError
        assert issubclass(excinfo.type, ValueError)

        try:
            raise TaskNotFoundError(task_id)
        except Exception as ex:
            assert ex.__class__ is TaskNotFoundError
            assert issubclass(ex.__class__, TaskNotFoundError)
            assert "Task not found: {}".format(task_id) == str(ex)

    def test_ScheduleNotFoundError(self):
        schedule_id = uuid.uuid4()
        with pytest.raises(ScheduleNotFoundError) as excinfo:
            raise ScheduleNotFoundError(schedule_id)
        assert excinfo.type is ScheduleNotFoundError
        assert issubclass(excinfo.type, ValueError)

        try:
            raise ScheduleNotFoundError(schedule_id)
        except Exception as ex:
            assert ex.__class__ is ScheduleNotFoundError
            assert issubclass(ex.__class__, ScheduleNotFoundError)
            assert "Schedule not found: {}".format(schedule_id) == str(ex)

