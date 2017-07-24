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
"""Send log entries to /var/log/syslog"""
CONSOLE = 1
"""Send log entries to STDOUT"""


def setup(logger_name: str = None,
          destination: int = SYSLOG,
          level: int = logging.WARNING,
          propagate: bool = False) -> logging.Logger:
    """Configures a `logging.Logger`_ object

    Once configured, a logger can also be retrieved via
    `logging.getLogger`_().

    It is inefficient to call this function more than once for the same
    logger name.

    Args:
        logger_name (str):
            The name of the logger to configure. Use None (the default)
            to configure the root logger.

        level (int):
            The `logging level`_ to use when filtering log entries.
            Defaults to logging.WARNING.

        propagate (bool):
            Whether to send log entries to ancestor loggers. Defaults to False.

        destination (int):
            - SYSLOG: (the default) Send messages to syslog (view with tail -f /var/log/syslog)
            - CONSOLE: Send message to stdout

    Returns:
        A `logging.Logger`_ object

    .. _logging.Logger: https://docs.python.org/3/library/logging.html#logging.Logger

    .. _logging level: https://docs.python.org/3/library/logging.html#levels

    .. _logging.getLogger: https://docs.python.org/3/library/logging.html#logging.getLogger
    """

    logger = logging.getLogger(logger_name)

    if destination == SYSLOG:
        handler = handlers.SysLogHandler(address='/dev/log')
    elif destination == CONSOLE:
        handler = logging.StreamHandler(sys.stdout)
    else:
        raise ValueError("Invalid destination {}".format(destination))

    formatter = logging.Formatter(
        fmt='[FOGLAMP] %(asctime)s - %(levelname)s :: %(module)s: %(message)s',
        datefmt='%m-%d-%Y %H:%M:%S')

    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.propagate = propagate
    logger.addHandler(handler)

    return logger
