# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Fledge Logger """
import os
import subprocess
import logging
import traceback
from logging.handlers import SysLogHandler
from functools import wraps


__author__ = "Praveen Garg, Ashish Jabble"
__copyright__ = "Copyright (c) 2017-2023 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

SYSLOG = 0
r"""Send log entries to /var/log/syslog

- View with: ``tail -f /var/log/syslog | sed 's/#012/\n\t/g'``

"""
CONSOLE = 1
"""Send log entries to STDERR"""
FLEDGE_LOGS_DESTINATION = 'FLEDGE_LOGS_DESTINATION'
"""Log destination environment variable"""
default_destination = SYSLOG
"""Default destination of logger"""


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


def get_process_name() -> str:
    # Example: ps -eaf | grep 5175 | grep -v grep | awk -F '--name=' '{print $2}'
    pid = os.getpid()
    cmd = "ps -eaf | grep {} | grep -v grep | awk -F '--name=' '{{print $2}}'| tr -d '\n'".format(pid)
    read_process_name = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()
    binary_to_string = [b.decode() for b in read_process_name]
    pname = 'Fledge ' + binary_to_string[0] if binary_to_string else 'Fledge'
    return pname


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

    # save the old logging.error function
    __logging_error = logger.error

    # TODO: Consider using %r with message when using syslog .. \n looks better than #
    fmt = '{}[%(process)d] %(levelname)s: %(module)s: %(name)s: %(message)s'.format(get_process_name())
    formatter = logging.Formatter(fmt=fmt)
    handler.setFormatter(formatter)
    if level is not None:
        logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = propagate

    @wraps(logger.error)
    def error(msg, *args, **kwargs):
        if isinstance(msg, Exception):
            trace_msg = traceback.format_exception(msg.__class__, msg, msg.__traceback__)
            if args:
                trace_msg[:0] = ["{}\n".format(args[0])]
            [__logging_error(line.strip('\n')) for line in trace_msg]
        else:
            if isinstance(msg, str):
                if args:
                    msg = msg % args
                [__logging_error(m) for m in msg.splitlines()]
            else:
                # Default logging error
                __logging_error(msg)

    # overwrite the default logging.error
    logger.error = error

    return logger


class FLCoreLogger:
    """
    Singleton FLCoreLogger class. This class is only instantiated ONCE. It is to keep a consistent
    criteria for the logger throughout the application if need to be called upon.
    It serves as the criteria for initiating logger for modules. It creates child loggers.
    It's important to note these are child loggers as any changes made to the root logger
    can be done.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            process_name = get_process_name()
            fmt = '{}[%(process)d] %(levelname)s: %(module)s: %(name)s: %(message)s'.format(process_name)
            cls.formatter = logging.Formatter(fmt=fmt)
        return cls._instance

    def get_syslog_handler(self):
        """Defines a syslog handler

        Returns:
             logging handler object : the syslog handler
        """
        syslog_handler = SysLogHandler(address='/dev/log')
        syslog_handler.setFormatter(self.formatter)
        syslog_handler.name = "syslogHandler"
        return syslog_handler

    def get_console_handler(self):
        """Defines a console handler to come out on the console

        Returns:
            logging handler object : the console handler
        """
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)
        console_handler.name = "consoleHandler"
        return console_handler

    def add_handlers(self, logger, handler_list: list):
        """Adds handlers to the logger, checks first if handlers exist to avoid
        duplication

        Args:
            logger: Logger to check handlers
            handler_list: list of handlers to add
        """
        existing_handler_names = []
        for existing_handler in logger.handlers:
            existing_handler_names.append(existing_handler.name)

        for new_handler in handler_list:
            if new_handler.name not in existing_handler_names:
                logger.addHandler(new_handler)

    def get_logger(self, logger_name: str):
        """Generates logger for use in the modules.
        Args:
            logger_name: name of the logger

        Returns:
            logger: returns logger for module
        """
        _logger = logging.getLogger(logger_name)

        # save the old logging.error function
        __logging_error = _logger.error

        console_handler = self.get_console_handler()
        syslog_handler = self.get_syslog_handler()
        self.add_handlers(_logger, [syslog_handler, console_handler])
        _logger.propagate = False

        @wraps(_logger.error)
        def error(msg, *args, **kwargs):
            """Override error logger to print multi-line traceback and error string with newline"""
            if isinstance(msg, Exception):
                """For example:
                    a) _logger.error(ex)
                    b) _logger.error(ex, "Failed to add data.")
                """
                trace_msg = traceback.format_exception(msg.__class__, msg, msg.__traceback__)
                if args:
                    trace_msg[:0] = ["{}\n".format(args[0])]
                [__logging_error(line.strip('\n')) for line in trace_msg]
            else:
                if isinstance(msg, str):
                    """For example:
                        a) _logger.error(str(ex))
                        b) _logger.error("Failed to log audit trail entry")
                        c) _logger.error('Failed to log audit trail entry for code: %s', "CONCH")
                        d) _logger.error('Failed to log audit trail entry for code: {log_code}'.format(log_code="CONAD"))
                        e) _logger.error('Failed to log audit trail entry for code: {0}'.format("CONAD"))
                        f) _logger.error("Failed to log audit trail entry for code '{}' \n{}".format("CONCH", "Next line"))
                    """
                    if args:
                        msg = msg % args
                    [__logging_error(m) for m in msg.splitlines()]
                else:
                    # Default logging error
                    __logging_error(msg)

        # overwrite the default logging.error
        _logger.error = error
        return _logger

    def set_level(self, level_name: str):
        """Sets the root logger level. That means all child loggers will inherit this feature from it.
        Args:
            level_name: logging level
        """
        if level_name == 'debug':
            log_level = logging.DEBUG
        elif level_name == 'info':
            log_level = logging.INFO
        elif level_name == 'error':
            log_level = logging.ERROR
        elif level_name == 'critical':
            log_level = logging.CRITICAL
        else:
            log_level = logging.WARNING
        logging.root.setLevel(log_level)
