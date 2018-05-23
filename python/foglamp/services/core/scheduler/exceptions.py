# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler module"""

import uuid

__author__ = "Terris Linenbach, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__all__ = ('NotReadyError', 'DuplicateRequestError', 'TaskNotRunningError', 'TaskNotFoundError', 'ScheduleNotFoundError',
           'ScheduleProcessNameNotFoundError')

class NotReadyError(RuntimeError):
    pass


class DuplicateRequestError(RuntimeError):
    pass


class TaskNotRunningError(RuntimeError):
    """Raised when canceling a task and the task isn't running"""

    def __init__(self, task_id: uuid.UUID, *args):
        self.task_id = task_id
        super(RuntimeError, self).__init__(
            "Task is not running: {}".format(task_id), *args)


class TaskNotFoundError(ValueError):
    def __init__(self, task_id: uuid.UUID, *args):
        self.task_id = task_id
        super(ValueError, self).__init__(
            "Task not found: {}".format(task_id), *args)


class ScheduleNotFoundError(ValueError):
    def __init__(self, schedule_id: uuid.UUID, *args):
        self.schedule_id = schedule_id
        super(ValueError, self).__init__(
            "Schedule not found: {}".format(schedule_id), *args)


class ScheduleProcessNameNotFoundError(ValueError):
    pass