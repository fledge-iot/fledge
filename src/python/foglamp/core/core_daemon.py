#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""
This module can not be called 'daemon' because it conflicts
with the third-party daemon module
"""

import os
import logging
import signal
import sys
import time
import daemon
from daemon import pidfile


import foglamp.core.server

__author__    = "Amarendra K Sinha, Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__   = "Apache 2.0"
__version__   = "${VERSION}"

# Location of daemon files
PIDFILE = '~/var/run/foglamp.pid'
LOGFILE = '~/var/log/foglamp.log'
WORKING_DIR = '~/var/log'

# Full path location of daemon files
# TODO Make these more human friendly and give them docstrings or make them private (start with _)
pidf = os.path.expanduser(PIDFILE)
logf = os.path.expanduser(LOGFILE)
wdir = os.path.expanduser(WORKING_DIR)

_logger_configured = False


def _start_server():
    """
    Starts the core REST server
    """

    # TODO Move log initializer to a module in the foglamp package. The files
    # should rotate etc.
    file_handler = logging.FileHandler(logf)
    file_handler.setLevel(logging.WARNING)

    formatstr = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(formatstr)

    file_handler.setFormatter(formatter)
 
    logger = logging.getLogger('')
    logger.addHandler(file_handler)
    logger.setLevel(logging.WARNING)

    global _logger_configured
    _logger_configured = True

    # The main daemon process
    foglamp.core.server.start()


def start():
    """
    Launches the daemon
    """

    # Get the pid from the pidfile
    pid = get_pid()

    if pid is not None:
        message = "Daemon already running under PID {}\n"
        sys.stderr.write(message.format(pid))
        return is_running()

    print ("Logging to {}".format(logf));

    with daemon.DaemonContext(
        working_directory=wdir,
        umask=0o002,
        pidfile=daemon.pidfile.TimeoutPIDLockFile(pidf)
    ) as context:
        _start_server()


def stop():
    """
    Stops the daemon if it is running
    """

    # TODO Document the return code

    # Get the pid from the pidfile
    pid = get_pid()

    if pid is None:
        message = "pidfile {} does not exist. Daemon not running.\n"
        sys.stderr.write(message.format(pidf))
        return is_running()

    # Try killing the daemon process
    try:
        while True:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
    except OSError as err:
        err = str(err)
        # TODO This is not ideal. It is english only.
        if err.find("No such process") > 0:
            if os.path.exists(pidf):
                os.remove(pidf)
        else:
            # TODO Throw an exception instead
            sys.stdout.write(str(err))
            sys.exit(1)

    return is_running()


def restart():
    """
    Relaunches the daemon
    """

    if is_running():
        stop()
    start()

    return is_running()


def is_running():
    """
    Check if the daemon is running.

    :return boolean status as True|False
    """

    return get_pid() is not None


def get_pid():
    """
    Returns the PID from pidf
    """

    try:
        pf = open(pidf,'r')
        pid = int(pf.read().strip())
        pf.close()
    except (IOError, TypeError):
        pid = None

    return pid


def _safe_makedirs(directory):
    """
    :param directory: working directory
    """

    try:
        os.makedirs(directory, 0o750)
    except Exception as e:
        if not os.path.exists(directory):
            raise e


def _do_main():
    _safe_makedirs(wdir)
    _safe_makedirs(os.path.dirname(pidf))
    _safe_makedirs(os.path.dirname(logf))

    if len(sys.argv) == 1:
        print("Usage: start|stop|restart|status|info")
        # TODO throw an exception instead
        sys.exit(2)
    elif len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            start()
        elif 'stop' == sys.argv[1]:
            stop()
        elif 'restart' == sys.argv[1]:
            restart()
        elif 'status' == sys.argv[1]:
            if is_running():
                print("FogLAMP is running")
            else:
                print("FogLAMP is not running")
        elif 'info' == sys.argv[1]:
            print("Pid: {}".format(get_pid()))
        else:
            # TODO throw an exception instead
            print("Unknown argument: {}".format(sys.argv[1]))
            sys.exit(2)

def main():
    """
    Processes command-line arguments
    """
    try:
        _do_main()
    except Exception as e:
        global _logger_configured
        if _logger_configured:
            logging.getLogger(__name__).exception("Failed")
        else:
            # If the daemon package has been invoked, the following 'write' will
            # do nothing
            sys.stderr.write("Failed: {}\n".format(str(e)));
      
        sys.exit(2)


if __name__ == "__main__":
    main()

