# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Microservice Management Client Exceptions module"""

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class MicroserviceManagementClientError(Exception):

        def __init__(self, status=None, reason=None):
                self.status = status
                self.reason = reason

