# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""The fogbench exceptions module contains Exception subclasses

"""

# nothing to import yet

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class FogbenchError(Exception):
    """
    All errors specific to fogbench will be
    subclassed from FogbenchError which is subclassed from Exception.
    """
    pass


class InvalidTemplateFormat(FogbenchError):
    pass


class InvalidSensorValueObjectTemplateFormat(InvalidTemplateFormat):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "{!s}".format(self.msg)
