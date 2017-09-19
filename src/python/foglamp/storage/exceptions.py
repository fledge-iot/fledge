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


class FogLAMPError(Exception):
    """ all error specific to foglamp storage microservice python client will be subclassed
    from this """
    pass


class StorageClientError(FogLAMPError):
    pass


class StorageServiceUnavailableException(FogLAMPError):
    pass

# TODO: add more specific exceptions
