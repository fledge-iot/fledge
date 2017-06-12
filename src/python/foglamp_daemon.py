"""Runs foglamp as a daemon"""

import os

import argparse
import logging
import daemon
from daemon import pidfile

from foglamp.controller import start


def do_something(logf):
    fh = logging.FileHandler(logf)
    fh.setLevel(logging.DEBUG)

    formatstr = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(formatstr)

    fh.setFormatter(formatter)

    logger = logging.getLogger('')
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)

    start()


def start_daemon(pidf, logf, wd):
    """Launches the daemon"""

    # XXX pidfile is a context
    with daemon.DaemonContext(
            working_directory=wd,
            umask=0o002,
            pidfile=pidfile.TimeoutPIDLockFile(pidf)
    ) as context:
        do_something(logf)


def safe_makedirs(dir):
    dir = os.path.expanduser(dir)
    try:
        os.makedirs(dir, 0o750)
    except Exception as e:
        if not os.path.exists(dir):
          raise e


def main():
    parser = argparse.ArgumentParser(description="FogLAMP daemon in Python")
    parser.add_argument('-p', '--pid-file', default='~/var/run/foglamp.pid')
    parser.add_argument('-l', '--log-file', default='~/var/log/foglamp.log')
    parser.add_argument('-w', '--working-dir', default='~/var/log')

    args = parser.parse_args()

    safe_makedirs(args.working_dir)
    safe_makedirs(os.path.dirname(args.pid_file))
    safe_makedirs(os.path.dirname(args.log_file))

    # TODO: ['start', 'stop', 'restart', 'status', 'info']
    start_daemon(pidf=os.path.expanduser(args.pid_file), logf=os.path.expanduser(args.log_file), wd=os.path.expanduser(args.working_dir))


if __name__ == "__main__":
    main()

