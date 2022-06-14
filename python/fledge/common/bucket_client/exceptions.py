# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Bucket layer python client exceptions

    If the data layer was unavailable then return “503 Service Unavailable”
    If any of the query parameters are missing or payload is malformed then return “400 Bad Request”
    If the data could not be deleted because of a conflict, then return error “409 Conflict”

    In other circumstances a “400 Bad Request” should be returned.
"""

__author__ = "Praveen Garg, Amandeep Singh Arora"
__copyright__ = "Copyright (c) 2022 Dianomic Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__all__ = ('BadRequest', 'BucketServiceUnavailable', 'InvalidServiceInstance', 'BucketServerError')


class BucketClientException(Exception):
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


class BadRequest(BucketClientException):
    """ 400 - Bad request: you sent some malformed data.
    """
    def __init__(self):
        self.code = 400
        self.message = "Bad request"


class BucketServiceUnavailable(BucketClientException):
    """ 503 - Service Unavailable
    """
    def __init__(self):
        self.code = 503
        self.message = "Bucket service is unavailable"


class InvalidServiceInstance(BucketClientException):
    """ 502 - Invalid Bucket Service
    """

    def __init__(self):
        self.code = 502
        self.message = "Bucket client needs a valid *Foglamp bucket* micro-service instance"


class BucketServerError(Exception):

    def __init__(self, code, reason, error):
        self.code = code
        self.reason = reason
        self.error = error

    def __str__(self):
        fmt_msg = "code: %d, reason:%s, error:%s" % (self.code, self.reason, self.error)
        return fmt_msg
