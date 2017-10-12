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
import signal
import sys
import time
import daemon
from daemon import pidfile

from foglamp.core.server import Server
from foglamp import logger

__author__ = "Amarendra K Sinha, Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_PID_PATH = os.path.expanduser('~/var/run/foglamp.pid')
_WORKING_DIR = os.path.expanduser('~/var/log')

_WAIT_STOP_SECONDS = 5
"""How many seconds to wait for the core server process to stop"""
_MAX_STOP_RETRY = 5
"""How many times to send TERM signal to core server process when stopping"""
_LOGGER = logger.setup(logger_name=__name__, level=20)


class Daemon(object):
    """FogLAMP Daemon"""

    @staticmethod
    def _safe_make_dirs(path):
        """Creates any missing parent directories

        :param path: The path of the directory to create
        """

        try:
            os.makedirs(path, 0o750)
        except OSError as exception:
            if not os.path.exists(path):
                raise exception

    @classmethod
    def _start_server(cls):
        """Starts the core server"""

        Server.start()

    @classmethod
    def start(cls):
        """Starts FogLAMP"""

        cls._safe_make_dirs(_WORKING_DIR)
        cls._safe_make_dirs(os.path.dirname(_PID_PATH))

        pid = cls.get_pid()

        if pid:
            print("FogLAMP is already running in PID {}".format(pid))
        else:
            # If it is desirable to output the pid to the console,
            # os.getpid() reports the wrong pid so it's not easy.
            print("Starting FogLAMP")
            _LOGGER.info("Starting FogLAMP")

            with daemon.DaemonContext(
                working_directory=_WORKING_DIR,
                umask=0o002,
                pidfile=pidfile.TimeoutPIDLockFile(_PID_PATH)
            ):
                cls._start_server()

    @classmethod
    def stop(cls, pid=None):
        """Stops FogLAMP if it is running

        Args:
            pid: Optional process id to stop. If not specified, the pidfile is read.

        Raises TimeoutError:
            Unable to stop FogLAMP. Wait and try again.
        """

        # TODO: FOGL-274 Stopping is hard.

        if not pid:
            pid = cls.get_pid()

        if not pid:
            print("FogLAMP is not running")
            return

        stopped = False

        try:
            for _ in range(_MAX_STOP_RETRY):
                os.kill(pid, signal.SIGTERM)

                for _ in range(_WAIT_STOP_SECONDS):  # Ignore the warning
                    os.kill(pid, 0)
                    time.sleep(1)
        except OSError:
            stopped = True

        if not stopped:
            raise TimeoutError("Unable to stop FogLAMP")

        print("FogLAMP stopped")
        _LOGGER.info("FogLAMP stopped")

    @classmethod
    def restart(cls):
        """Restarts FogLAMP"""

        pid = cls.get_pid()
        if pid:
            cls.stop(pid)

        cls.start()

    @staticmethod
    def get_pid():
        """Returns FogLAMP's process id or None if FogLAMP is not running"""

        try:
            with open(_PID_PATH, 'r') as pid_file:
                pid = int(pid_file.read().strip())
        except (IOError, ValueError):
            return None

        # Delete the pid file if the process isn't alive
        # there is an unavoidable race condition here if another
        # process is stopping or starting the daemon
        try:
            os.kill(pid, 0)
        except OSError:
            os.remove(_PID_PATH)
            pid = None

        return pid

    @classmethod
    def status(cls):
        """Outputs the status of the FogLAMP process"""
        pid = cls.get_pid()

        if pid:
            print("FogLAMP is running in PID {}".format(pid))
        else:
            print("FogLAMP is not running")
            sys.exit(2)

    @classmethod
    def main(cls):
        """Processes command-line arguments

        COMMAND LINE ARGUMENTS:
            - start
            - status
            - stop
            - restart

        EXIT STATUS:
            - 0: Normal
            - 1: An error occurred
            - 2: For the 'status' command: FogLAMP is not running

        :raises ValueError: Invalid or missing arguments provided
        """

        if len(sys.argv) == 1:
            raise ValueError("Usage: start|stop|restart|status")
        elif len(sys.argv) == 2:
            command = sys.argv[1]
            if command == 'start':
                cls.start()
            elif command == 'stop':
                cls.stop()
            elif command == 'restart':
                cls.restart()
            elif command == 'status':
                cls.status()
            else:
                raise ValueError("Unknown argument: {}".format(sys.argv[1]))


def main():
    """Processes command-line parameters

    See :meth:`Daemon.start`
    """

    try:
        Daemon.main()
    except Exception as ex:
        _LOGGER.exception(str(ex))

        # If the daemon package has been invoked, the following 'write' will
        # do nothing because stdout and stderr are routed to /dev/null
        sys.stderr.write(format(str(ex)) + "\n")

        sys.exit(1)
