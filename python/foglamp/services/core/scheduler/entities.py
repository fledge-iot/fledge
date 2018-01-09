# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler module"""

import collections
import datetime
import uuid
from enum import IntEnum
from typing import Iterable, List, Tuple, Union

__author__ = "Terris Linenbach, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class ScheduledProcess(object):
    """Represents a program that a Task can run"""

    __slots__ = ['name', 'script']

    def __init__(self):
        self.name = None  # type: str
        """Unique identifier"""
        self.script = None  # type: List[ str ]


class Schedule(object):
    class Type(IntEnum):
        """Enumeration for schedules.schedule_type"""
        STARTUP = 1
        TIMED = 2
        INTERVAL = 3
        MANUAL = 4

    """Schedule base class"""
    __slots__ = ['schedule_id', 'name', 'process_name', 'exclusive', 'enabled', 'repeat', 'schedule_type']

    def __init__(self, schedule_type: Type):
        self.schedule_id = None  # type: uuid.UUID
        self.name = None  # type: str
        self.exclusive = True
        self.enabled = False
        self.repeat = None  # type: datetime.timedelta
        self.process_name = None  # type: str
        self.schedule_type = schedule_type  # type: Schedule.Type


class IntervalSchedule(Schedule):
    """Interval schedule"""

    def __init__(self):
        super().__init__(self.Type.INTERVAL)


class TimedSchedule(Schedule):
    """Timed schedule"""
    __slots__ = ['time', 'day']

    def __init__(self):
        super().__init__(self.Type.TIMED)
        self.time = None  # type: datetime.time
        self.day = None  # type: int
        """1 (Monday) to 7 (Sunday)"""


class ManualSchedule(Schedule):
    """A schedule that is run manually"""

    def __init__(self):
        super().__init__(self.Type.MANUAL)


class StartUpSchedule(Schedule):
    """A schedule that is run when the _scheduler starts"""

    def __init__(self):
        super().__init__(self.Type.STARTUP)

class Task(object):
    """A task represents an operating system process"""

    class State(IntEnum):
        """Enumeration for tasks.task_state"""
        RUNNING = 1
        COMPLETE = 2
        CANCELED = 3
        INTERRUPTED = 4

    # Class attributes
    attr = collections.namedtuple('TaskAttributes', ['state', 'process_name', 'start_time',
                                                     'end_time', 'exit_code'])

    __slots__ = ['task_id', 'process_name', 'state', 'cancel_requested', 'start_time',
                 'end_time', 'state', 'exit_code', 'reason']

    def __init__(self):
        # Instance attributes
        self.task_id = None  # type: uuid.UUID
        """Unique identifier"""
        self.process_name = None  # type: str
        self.reason = None  # type: str
        self.state = None  # type: Task.State
        self.cancel_requested = None  # type: datetime.datetime
        self.start_time = None  # type: datetime.datetime
        self.end_time = None  # type: datetime.datetime
        self.exit_code = None  # type: int


