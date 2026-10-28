#!/bin/bash
# Container entrypoint — starts rsyslog (so fledge's logger() calls have somewhere
# to land), starts fledge, then watches the fledge core process. If fledge dies,
# the script exits non-zero and the container exits with it. On SIGTERM, fledge
# is stopped cleanly first.
#
# Why not just `exec fledge start`? Because `fledge start` daemonizes — its own
# process exits as soon as the core service is forked, which would terminate the
# container immediately. The watchdog loop binds the container's lifecycle to the
# python core process instead. PID 1 isn't fledge but its lifetime mirrors it.
set -euo pipefail

if [[ $# -eq 0 ]]; then
    set -- start
elif [[ "$1" == "fledge" ]]; then
    shift
elif [[ "$1" == -* ]]; then
    set -- start "$@"
fi

if [[ "${1:-}" != "start" ]]; then
    exec "${FLEDGE_ROOT}/bin/fledge" "$@"
fi
shift

# Stale pid from a hard restart of a previously-running container prevents fledge
# from starting cleanly (see POLARIS-Fledge-Base scripts/fledge.sh for context).
rm -f "${FLEDGE_DATA:-/usr/local/fledge/data}/var/run/fledge.core.pid"

# rsyslog so fledge's logger() calls aren't dropped.
touch /var/log/syslog
chmod 640 /var/log/syslog
chown syslog:adm /var/log/syslog 2>/dev/null || chown root:root /var/log/syslog
rm -f /run/rsyslogd.pid
/usr/sbin/rsyslogd -f /etc/rsyslog.conf

# Background log streamer — surfaces fledge output to `docker logs`.
CORE_ERR="${FLEDGE_DATA:-/usr/local/fledge/data}/core.err"
tail -q -F -n0 /var/log/syslog "${CORE_ERR}" 2>/dev/null &
TAIL_PID=$!

shutdown() {
    local code="${1:-0}"
    echo "[entrypoint] stopping fledge (exit ${code})" >&2
    "${FLEDGE_ROOT}/bin/fledge" stop >/dev/null 2>&1 || true
    kill "${TAIL_PID}" 2>/dev/null || true
    exit "${code}"
}

trap 'shutdown 0' SIGTERM SIGINT

# Start fledge — `fledge start` forks the core service and returns.
"${FLEDGE_ROOT}/bin/fledge" start "$@"

# Wait a couple of seconds for the python core to actually come up before the
# watchdog starts looking for its PID. Otherwise we'd race the fork.
sleep 3
if ! pgrep -f fledge.services.core >/dev/null; then
    echo "[entrypoint] ERROR: fledge.services.core did not start" >&2
    shutdown 1
fi

STORAGE_GRACE="${FLEDGE_STORAGE_GRACE:-90}"
storage_seen=0
storage_missing_since=0

interruptible_sleep() {
    sleep "$1" &
    wait $! 2>/dev/null || true
}

while pgrep -f fledge.services.core >/dev/null; do
    if [[ "${STORAGE_GRACE}" != "0" ]]; then
        if pgrep -f fledge.services.storage >/dev/null; then
            storage_seen=1
            if (( storage_missing_since != 0 )); then
                echo "[entrypoint] fledge.services.storage recovered" >&2
                storage_missing_since=0
            fi
        elif (( storage_seen == 1 )); then
            now=$(date +%s)
            if (( storage_missing_since == 0 )); then
                storage_missing_since=${now}
                echo "[entrypoint] WARNING: fledge.services.storage is gone, allowing ${STORAGE_GRACE}s for core to respawn it" >&2
            elif (( now - storage_missing_since >= STORAGE_GRACE )); then
                echo "[entrypoint] ERROR: fledge.services.storage absent for ${STORAGE_GRACE}s; exiting so the restart policy can recover the container" >&2
                shutdown 1
            fi
        fi
    fi
    interruptible_sleep 5
done

echo "[entrypoint] ERROR: fledge.services.core exited unexpectedly" >&2
shutdown 1
