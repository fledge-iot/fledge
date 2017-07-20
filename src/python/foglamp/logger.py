# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" FogLAMP Logger """

import sys
import logging
from logging import handlers

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

SYSLOG = 0
CONSOLE= 1

def setup(logger_name: str = None,
          level: int = logging.WARNING,
          destination: int = SYSLOG) -> logging.Logger:
    """Configures a logging.Logger object

    Once configured, a logger can also be retrieved via logger.getLogger().

    It is inefficient to call this function more than once for the same
    logger name.

    Args:
        logger_name (str):
            The name of the logger to configure. Use None (the default)
            to configure the root logger

        level (int): The logging level filter. Defaults to logging.WARNING.

        destination (int):
            - SYSLOG: (the default) Send messages to syslog (view with tail -f /var/log/syslog)
            - CONSOLE: Send message to stdout

    Returns:
        A logging.Logger object
    """

    #logger = logging.getLogger()#  if logger is None ?: logging.getLogger() : logging.getLogger(logger_name)
    logger = logging.getLogger(logger_name)

    if destination == SYSLOG:
        handler = handlers.SysLogHandler(address='/dev/log')
    elif destination == CONSOLE:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
    else:
        raise ValueError("Invalid destination {}".format(destination))

    formatter = logging.Formatter(
        fmt='[FOGLAMP] %(asctime)s - %(levelname)s :: %(module)s: %(message)s',
        datefmt='%m-%d-%Y %H:%M:%S')

    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
