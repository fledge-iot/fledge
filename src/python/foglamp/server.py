#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
import logging
import signal
import sys
import time
import daemon
from daemon import pidfile

from foglamp.controller import start as start_controller

__author__    = "Terris Linenbach, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__   = "Apache 2.0"
__version__   = "${VERSION}"

# Location of daemon files
PIDFILE = '~/var/run/foglamp.pid'
LOGFILE = '~/var/log/foglamp.log'
WORKING_DIR = '~/var/log'

# Full path location of daemon files
pidf = os.path.expanduser(PIDFILE)
logf = os.path.expanduser(LOGFILE)
wdir = os.path.expanduser(WORKING_DIR)


def do_something(logf):
    """
    The main daemon method call

    :param logf: log file
    """

    file_handler = logging.FileHandler(logf)
    file_handler.setLevel(logging.WARNING)

    formatstr = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(formatstr)

    file_handler.setFormatter(formatter)

    logger = logging.getLogger('')
    logger.addHandler(file_handler)
    logger.setLevel(logging.WARNING)

    # The main daemon process
    start_controller()


def run():
    """
    Run foglamp server in foreground
    """

    if is_running():
        message = "Daemon already running. Check PID %s.\n"
        sys.stderr.write(message % get_pid())
        return is_running()

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("foglamp").setLevel(logging.WARNING)

    start_controller()


def start():
    """
    Launches the daemon
    """

    # Get the pid from the pidfile
    pid = get_pid()

    if pid is not None:
        message = "Daemon already running under PID %s.\n"
        sys.stderr.write(message % pid)
        return is_running()

    with daemon.DaemonContext(
        working_directory=wdir,
        umask=0o002,
        pidfile=pidfile.TimeoutPIDLockFile(pidf)
    ) as context:
        do_something(logf)

def stop():
    """
    Stop the daemon
    """

    # Get the pid from the pidfile
    pid = get_pid()

    if pid is None:
        message = "pidfile %s does not exist. Daemon not running.\n"
        sys.stderr.write(message % pidf)
        return is_running()

    # Try killing the daemon process
    try:
        while True:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
    except OSError as err:
        err = str(err)
        if err.find("No such process") > 0:
            if os.path.exists(os.path.expanduser(pidf)):
                os.remove(os.path.expanduser(pidf))
        else:
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


def safe_makedirs(directory):
    """
    :param directory: working directory
    """

    directory = os.path.expanduser(directory)
    try:
        os.makedirs(directory, 0o750)
    except Exception as e:
        if not os.path.exists(directory):
            raise e


def main():
    safe_makedirs(WORKING_DIR)
    safe_makedirs(os.path.dirname(PIDFILE))
    safe_makedirs(os.path.dirname(LOGFILE))

    if len(sys.argv) == 1:
        start()
    elif len(sys.argv) == 2:
            if 'start' == sys.argv[1]:
                start()
            elif 'stop' == sys.argv[1]:
                stop()
            elif 'restart' == sys.argv[1]:
                restart()
            elif 'status' == sys.argv[1]:
                print(is_running())
            elif 'info' == sys.argv[1]:
                print(get_pid())
            else:
                print("Unknown argument")
                sys.exit(2)
            sys.exit(0)
    else:
        print("usage: foglampd start|stop|restart|status|info")
        sys.exit(2)

if __name__ == "__main__":
    run()