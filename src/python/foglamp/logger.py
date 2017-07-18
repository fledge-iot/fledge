# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Syslog logger """


import logging
from logging import handlers

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def setup(name):
    """ Configures the log mechanism """

    try:
        handler = handlers.SysLogHandler(address='/dev/log')
        formatter = logging.Formatter(
            fmt='[FOGLAMP] %(asctime)s - %(levelname)s :: %(module)s: %(message)s',
            datefmt='%m-%d-%Y %H:%M:%S')
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

    except:
        raise

    return logger
