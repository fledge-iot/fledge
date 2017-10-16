#!/usr/bin/env bash

### BEGIN INIT INFO
# Provides:          foglamp
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: foglamp script
# Description:       starts foglamp core, storage and scheduler

# `make install` will put foglamp as python code entry_point in /home/foglamp/.local/bin


# Copy this script into /etc/init.d using
# e.g. sudo cp foglamp-service.sh /etc/init.d.
# Make sure the script is executable (chmod again)
# sudo chmod 755 foglamp-service.sh
# and make sure that it has UNIX line-endings (dos2unix).


# running the command `sudo update-rc.d foglamp-service.sh defaults`.
# This command adds in symbolic links to the `/etc/rc?.d` directories
# so that the init script is run at the default times.
# you can see these links if you do `ls -l /etc/rc?.d/*foglamp-service.sh`


# At this point you should be able to start foglamp using the command:

# sudo /etc/init.d/foglamp-service.sh start,
# check its status with the /etc/init.d/foglamp-service.sh status argument
# and stop it with sudo /etc/init.d/foglamp-service.sh stop.
### END INIT INFO

DIR=/home/foglamp/.local/bin
DAEMON=$DIR/foglamp
DAEMON_NAME=foglamp

# Add any command line options for your daemon here
DAEMON_OPTS="start"

# This next line determines what user the script runs as.
# Root generally not recommended but seems necessary
DAEMON_USER=foglamp

# The process ID of the script when it runs is stored here:
PIDFILE=/var/run/$DAEMON_NAME.pid

. /lib/lsb/init-functions

do_start () {
    log_daemon_msg "Starting system $DAEMON_NAME daemon"
    start-stop-daemon --start --background --pidfile $PIDFILE --make-pidfile --user $DAEMON_USER --chuid $DAEMON_USER --startas $DAEMON -- $DAEMON_OPTS
    log_end_msg $?
}
do_stop () {
    log_daemon_msg "Stopping system $DAEMON_NAME daemon"
    start-stop-daemon --stop --pidfile $PIDFILE --retry 10
    log_end_msg $?
}

case "$1" in

    start|stop)
        do_${1}
        ;;

    restart|reload)
        do_stop
        do_start
        ;;

    status)
        status_of_proc "$DAEMON_NAME" "$DAEMON" && exit 0 || exit $?
        ;;

    *)
        echo "Usage: /etc/init.d/$DAEMON_NAME {start|stop|status|restart|reload}"
        exit 1
        ;;

esac
exit 0
