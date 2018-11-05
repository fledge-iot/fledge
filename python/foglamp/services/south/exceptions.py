# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" South Microservice exceptions module """

import sys

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


class QuietError(Exception):
    # All who inherit me shall not traceback, but be spoken of cleanly
    pass


def quiet_hook(kind, message, traceback):
    if QuietError in kind.__bases__:
        print('{0}: {1}'.format(kind.__name__, message))  # Only print Error Type and Message
    else:
        sys.__excepthook__(kind, message, traceback)  # Print Error Type, Message and Traceback

sys.excepthook = quiet_hook
