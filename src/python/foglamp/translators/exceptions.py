# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" North Plugin exceptions

"""

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__all__ = ('NorthPluginException', 'HttpTranslatorException', 'ConfigurationError')



class NorthPluginException(Exception):
    def __init__(self, reason):
        self.reason = reason


class HttpTranslatorException(NorthPluginException):
    def __init__(self, reason):
        super(HttpTranslatorException, self).__init__(reason)
        self.reason = reason


class ConfigurationError(HttpTranslatorException):
    def __init__(self, reason):
        super(ConfigurationError, self).__init__(reason)
        self.reason = reason
