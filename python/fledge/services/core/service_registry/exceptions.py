# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Services Registry Exceptions module"""

__author__ = "Praveen Garg, Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class DoesNotExist(Exception):
    pass


class AlreadyExistsWithTheSameName(Exception):
    pass


class AlreadyExistsWithTheSameAddressAndPort(Exception):
    pass


class AlreadyExistsWithTheSameAddressAndManagementPort(Exception):
    pass


class NonNumericPortError(TypeError):
    pass
