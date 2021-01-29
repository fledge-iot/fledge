#!/bin/bash

declare SQL_COMMAND
declare COMMAND_OUTPUT

# Include logging
. $FLEDGE_ROOT/scripts/common/write_log.sh

# Logger wrapper
schema_update_log() {
    write_log "Downgrade" "scripts.plugins.storage.${PLUGIN_NAME}.schema_update" "$1" "$2" "$3" "$4"
}

schema_update_log "debug" "$0 - SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

SQL_COMMAND="${SQLITE_SQL} \"${DEFAULT_SQLITE_DB_FILE}\" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'                 AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

.read '${sql_file}'
.quit
EOF"


COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'                 AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

.read '${sql_file}'
.quit
EOF`

ret_code=$?

if [ "${ret_code}" -ne 0 ]; then
    schema_update_log "err" "Failure in downgrade command [${SQL_COMMAND}] result [${COMMAND_OUTPUT}]. Exiting" "all" "pretty"
    exit 1
fi

#
# Clean up - file system
#
file_path=$(dirname ${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE})
file_name_path="${file_path}/readings*"

schema_update_log "debug" "cleanup - deleting ${file_name_path}" "logonly" "pretty"

rm ${file_name_path}
ret_code=$?

if [ "${ret_code}" -ne 0 ]; then
    schema_update_log "notice" "cleanup_db - Failure in downgrade, files [${file_name_path}] can't be deleted. Proceeding" "logonly" "pretty"
fi
