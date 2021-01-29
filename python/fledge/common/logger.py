# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Fledge Logger """
import os
import subprocess
import sys
import logging
from logging.handlers import SysLogHandler

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

SYSLOG = 0
r"""Send log entries to /var/log/syslog

- View with: ``tail -f /var/log/syslog | sed 's/#012/\n\t/g'``

"""
CONSOLE = 1
"""Send log entries to STDERR"""


FLEDGE_LOGS_DESTINATION='FLEDGE_LOGS_DESTINATION'  # env variable
default_destination = SYSLOG    # default for fledge

def set_default_destination(destination: int):
    """ set_default_destination - allow a global default to be set, once, for all fledge modules
        also, set env variable FLEDGE_LOGS_DESTINATION for communication with related, spawned
        processes. (makes logging consistent for interactive stderr vs server syslog applications """
    global default_destination
    default_destination = destination
    os.environ[FLEDGE_LOGS_DESTINATION] = str(destination)


if (FLEDGE_LOGS_DESTINATION in os.environ) and \
   os.environ[FLEDGE_LOGS_DESTINATION] in [str(CONSOLE), str(SYSLOG)]:
    # inherit (valid) default from the environment
    set_default_destination(int(os.environ[FLEDGE_LOGS_DESTINATION]))
    


def setup(logger_name: str = None,
          destination: int = None,
          level: int = None,
          propagate: bool = False) -> logging.Logger:
    """Configures a `logging.Logger`_ object

    Once configured, a logger can also be retrieved via
    `logging.getLogger`_

    It is inefficient to call this function more than once for the same
    logger name.

    Args:
        logger_name:
            The name of the logger to configure. Use None (the default)
            to configure the root logger.

        level:
            The `logging level`_ to use when filtering log entries.
            Use None to maintain the default level

        propagate:
            Whether to send log entries to ancestor loggers. Defaults to False.

        destination:
            - SYSLOG: (the default) Send messages to syslog.
                - View with: ``tail -f /var/log/syslog | sed 's/#012/\n\t/g'``
            - CONSOLE: Send message to stderr

    Returns:
        A `logging.Logger`_ object

    .. _logging.Logger: https://docs.python.org/3/library/logging.html#logging.Logger

    .. _logging level: https://docs.python.org/3/library/logging.html#levels

    .. _logging.getLogger: https://docs.python.org/3/library/logging.html#logging.getLogger
    """

    def _get_process_name():
        # Example: ps -eaf | grep 5175 | grep -v grep | awk -F '--name=' '{print $2}'
        pid = os.getpid()
        cmd = "ps -eaf | grep {} | grep -v grep | awk -F '--name=' '{{print $2}}'| tr -d '\n'".format(pid)
        read_process_name = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()
        binary_to_string = [b.decode() for b in read_process_name]
        pname = 'Fledge ' + binary_to_string[0] if binary_to_string else 'Fledge'
        return pname

    logger = logging.getLogger(logger_name)

    # if no destination is set, use the fledge default
    if destination is None:
        destination = default_destination

    if destination == SYSLOG:
        handler = SysLogHandler(address='/dev/log')
    elif destination == CONSOLE:
        handler = logging.StreamHandler()  # stderr
    else:
        raise ValueError("Invalid destination {}".format(destination))

    process_name = _get_process_name()
    # TODO: Consider using %r with message when using syslog .. \n looks better than #
    fmt = '{}[%(process)d] %(levelname)s: %(module)s: %(name)s: %(message)s'.format(process_name)
    formatter = logging.Formatter(fmt=fmt)

    handler.setFormatter(formatter)
    if level is not None:
        logger.setLevel(level)
        
    logger.addHandler(handler)

    logger.propagate = propagate
    return logger
