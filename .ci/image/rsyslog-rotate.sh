#!/bin/sh

set -eu

LOG="${1:-/var/log/syslog}"

[ -f "${LOG}" ] || exit 0
mv -f "${LOG}" "${LOG}.1"
