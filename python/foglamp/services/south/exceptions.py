# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" South Microservice exceptions module """

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class InvalidCommandLineParametersError(Exception):
    """ Command line parameters are invalid """
    pass


class InvalidMicroserviceNameError(Exception):
    """ Invalid microservice name"""
    pass


class InvalidPortError(Exception):
    """ Invalid port """
    pass


class InvalidAddressError(Exception):
    """ Invalid address """
    pass


class InvalidPluginTypeError(Exception):
    """ Invalid plugin type, only the type -south- is allowed """
    pass


class DataRetrievalError(Exception):
    """ Unable to retrieve data from the South plugin """
    pass
