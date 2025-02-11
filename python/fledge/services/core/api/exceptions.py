# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from aiohttp import web

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2021, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__all__ = ('AuthenticationIsOptional', 'VerificationFailed', 'ConflictException')


class AuthenticationIsOptional(web.HTTPPreconditionFailed):
    pass

class VerificationFailed(web.HTTPUnauthorized):
    pass

class ConflictException(web.HTTPConflict):
    def __init__(self, message):
        super().__init__(reason=message)
        self.message = message

