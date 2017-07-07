#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Starts the FogLAMP core service as a daemon

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

from foglamp.core import server

__author__ = "Amarendra K Sinha, Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Location of daemon files
PID_PATH = os.path.expanduser('~/var/run/foglamp.pid')
LOG_PATH = os.path.expanduser('~/var/log/foglamp.log')
WORKING_DIR = os.path.expanduser('~/var/log')

_logger_configured = False


def _start_server():
    # TODO Move log initializer to a module in the foglamp package. The files
    # should rotate etc.
    file_handler = logging.FileHandler(LOG_PATH)
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
    server.start()


def start():
    """Launches FogLAMP"""

    pid = get_pid()

    if pid:
        print("FogLAMP is already running in PID: {}".format(pid))
    else:
        # TODO Output the pid. os.getpid() reports the wrong pid so it's not easy.
        print("Starting FogLAMP\nLogging to {}".format(LOG_PATH))

        with daemon.DaemonContext(
            working_directory=WORKING_DIR,
            umask=0o002,
            pidfile=daemon.pidfile.TimeoutPIDLockFile(PID_PATH)
        ):
            _start_server()


def stop():
    """Stops the FogLAMP process if it is running"""

    pid = get_pid()

    if pid is None:
        print("FogLAMP is not running")
        return 

    # Kill the daemon process
    # TODO This should time out and throw an exception
    try:
        while True:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
    except OSError:
        pass

    print("FogLAMP stopped")


def restart():
    """Relaunches FogLAMP"""

    if get_pid():
        stop()

    start()


def get_pid():
    """Returns FogLAMP's PID or None if not running"""

    try:
        with open(PID_PATH, 'r') as pf:
            pid = int(pf.read().strip())
    except Exception:
        return None

    # Delete the pid file if the process isn't alive
    # there is an unavoidable race condition here if another
    # process is stopping or starting the daemon
    try:
        os.kill(pid, 0)
    except Exception:
        os.remove(PID_PATH)
        pid = None

    return pid


def _safe_makedirs(path):
    """
    Creates any missing parent directories

    :param path: The path of the directory to create
    """

    try:
        os.makedirs(path, 0o750)
    except Exception as e:
        if not os.path.exists(path):
            raise e


def _do_main():
    _safe_makedirs(WORKING_DIR)
    _safe_makedirs(os.path.dirname(PID_PATH))
    _safe_makedirs(os.path.dirname(LOG_PATH))

    if len(sys.argv) == 1:
        raise Exception("Usage: start|stop|restart|status")
    elif len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            start()
        elif 'stop' == sys.argv[1]:
            stop()
        elif 'restart' == sys.argv[1]:
            restart()
        elif 'status' == sys.argv[1]:
            pid = get_pid()
            if pid:
                print("FogLAMP is running in PID: {}".format(pid))
            else:
                print("FogLAMP is not running")
                sys.exit(2)
        else:
            raise Exception("Unknown argument: {}".format(sys.argv[1]))


def main():
    """
    Processes command-line arguments

    COMMAND LINE ARGUMENTS:
        start
        status
        stop
        restart

    EXIT STATUS:
        1: An error occurred
        2: For the 'status' command: FogLAMP is not running (otherwise, 0)
    """
    try:
        _do_main()
    except Exception as e:
        if _logger_configured:
            logging.getLogger(__name__).exception("Failed")
        else:
            # If the daemon package has been invoked, the following 'write' will
            # do nothing
            sys.stderr.write(format(str(e)) + "\n");
      
        sys.exit(1)

