# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Interests Registry Exceptions module"""

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class DoesNotExist(Exception):
    pass

class ErrorInterestRegistrationAlreadyExists(Exception):
    pass

