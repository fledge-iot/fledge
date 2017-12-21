# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Interests Registry Exceptions module"""

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class DoesNotExist(Exception):
    pass

class ErrorInterestRegistrationAlreadyExists(Exception):
    pass

