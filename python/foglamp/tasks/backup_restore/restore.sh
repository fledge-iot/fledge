#!/usr/bin/env bash
# Restore wrapper to avoid its termination at the execution of FogLAMP stop

command="python3 -m foglamp.backup_restore.restore $@"

nohup $command </dev/null >/dev/null 2>&1 &
