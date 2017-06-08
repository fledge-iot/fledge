"""Runs foglamp as a daemon"""

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
            pidfile=pidfile.TimeoutPIDLockFile(pidf),
    ) as context:
        do_something(logf)


def main():
    parser = argparse.ArgumentParser(description="FogLAMP daemon in Python")
    parser.add_argument('-p', '--pid-file', default='~/var/run/foglamp.pid')
    parser.add_argument('-l', '--log-file', default='~/var/log/foglamp.log')
    parser.add_argument('-w', '--working-dir', default='/var/log/foglamp')

    args = parser.parse_args()

    # TODO ['start', 'stop', 'restart', 'status', 'info']
    start_daemon(pidf=args.pid_file, logf=args.log_file, wd=args.working_dir)

if __name__ == "__main__":
    main()

