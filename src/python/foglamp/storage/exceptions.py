# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Storage layer python client exceptions
"""

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__all__ = ('BadRequest', 'StorageServiceUnavailable', 'InvalidServiceInstance')


class StorageClientException(Exception):
    """ The base exception class for all exceptions this module raises.
    """
    def __init__(self, code, message=None):
        self.code = code
        # NOTE: Use getattr on self.__class__.message since
        # BaseException.message was dropped in python 3, see PEP 0352.
        self.message = message or getattr(self.__class__, 'message', None)

    def __str__(self):
        fmt_msg = "%s" % self.message
        return fmt_msg


class BadRequest(StorageClientException):
    """ 400 - Bad request: you sent some malformed data.
    """
    def __init__(self):
        self.code = 400
        self.message = "Bad request"


class StorageServiceUnavailable(StorageClientException):
    """ 503 - Service Unavailable
    """
    def __init__(self):
        self.code = 503
        self.message = "Storage service is unavailable"


class InvalidServiceInstance(StorageClientException):
    """ 502 - Invalid Storage Service
    """

    def __init__(self):
        self.code = 502
        self.message = "Storage client needs a valid *FogLAMP storage* micro-service instance"

# TODO: add more specific exceptions
