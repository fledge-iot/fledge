# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Storage layer python client exceptions

    If the data layer was unavailable then return “503 Service Unavailable”
    If any of the query parameters are missing or payload is malformed then return “400 Bad Request”
    If the data could not be deleted because of a conflict, then return error “409 Conflict”

    In other circumstances a “400 Bad Request” should be returned.
"""

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__all__ = ('BadRequest', 'StorageServiceUnavailable', 'InvalidServiceInstance', 'InvalidReadingsPurgeFlagParameters', 'PurgeOneOfAgeAndSize', 'PurgeOnlyOneOfAgeAndSize')


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


class InvalidReadingsPurgeFlagParameters(BadRequest):
    """ 400 - Invalid params for Purge request
    """

    def __init__(self):
        self.code = 400
        self.message = "Purge flag valid options are retain or purge only"


class PurgeOnlyOneOfAgeAndSize(BadRequest):
    """ 400 - Invalid params for Purge request
    """

    def __init__(self):
        self.code = 400
        self.message = "Purge must specify only one of age or size"


class PurgeOneOfAgeAndSize(BadRequest):
    """ 400 - Invalid params for Purge request
    """

    def __init__(self):
        self.code = 400
        self.message = "Purge must specify one of age or size"

# TODO: add more specific exceptions

