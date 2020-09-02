#!/bin/bash

# Include logging
. $FLEDGE_ROOT/scripts/common/write_log.sh

# Logger wrapper
schema_update_log() {
    write_log "Upgrade" "scripts.plugins.storage.${PLUGIN_NAME}.schema_update" "$1" "$2" "$3" "$4"
}



#
#
#
calculate_dbid() {

    _n_readings_allocate=$1

    schema_update_log "debug" "upgrade: calculate_dbid: SQLITE_SQL :$SQLITE_SQL: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "all" "pretty"

    #// FIXME_I:
    # Call the DB script
    #// FIXME_I:
    SQL_COMMAND="${SQLITE_SQL} \"${DEFAULT_SQLITE_DB_FILE}\" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';

UPDATE readings_1.asset_reading_catalogue SET db_id=(((table_id - 1) / '${_n_readings_allocate}') +1);
.quit
EOF"


    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';

UPDATE readings_1.asset_reading_catalogue SET db_id=(((table_id - 1) / '${_n_readings_allocate}') +1);

.quit
EOF`

    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then
        schema_update_log "err" "Failure in upgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
        exit 1
    fi
}

#

#
#
#
execute_sql_file() {

    schema_update_log "debug" "upgrade: execute_sql_file: SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "all" "pretty"

    #// FIXME_I:
    # Call the DB script
    #// FIXME_I:
    SQL_COMMAND="TODO"
    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

.read '${sql_file}'
.quit
EOF`

    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then
        schema_update_log "err" "Failure in upgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
        exit 1
    fi
}

#
create_database_file() {

    readings_file=$1

    file_path=$(dirname ${DEFAULT_SQLITE_DB_FILE_READINGS})
    file_name_path="${file_path}/${readings_file}.db"

    schema_update_log "debug" "upgrade: create_database_file - file path :$file_name_path:" "all" "pretty"

    # Created datafile
    COMMAND_OUTPUT=`${SQLITE_SQL} ${file_name_path} .databases 2>&1`

    ret_code=$?
    if [ "${ret_code}" -ne 0 ]; then
        sqlite_log "err" "Error creating SQLite3 database ${readings_file}: ${COMMAND_OUTPUT}" "all" "pretty"
        exit 1
    fi

}

create_all_database_files() {

    cat "$tmp_file"  | while read table_id db_id asset_code; do

        schema_update_log "debug" "upgrade: create_all_database_file - :$table_id: :$db_id: :$asset_code: " "all" "pretty"

        # The first database is created by the upgrade process
        if [ "$db_id" != "1" ]; then

            create_database_file "readings_$db_id"
        fi

    done
}



create_readings() {

    READINGS_DB="$1"
    READINGS_TABLE="$2"

    file_path=$(dirname ${DEFAULT_SQLITE_DB_FILE_READINGS})
    readings_file="${file_path}/${READINGS_DB}.db"

    schema_update_log "debug" "upgrade: create_readings - db :$READINGS_DB: table :$READINGS_TABLE: asset code :$ASSET_CODE:" "all" "pretty"

    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF
    ATTACH DATABASE '${readings_file}'                          AS '${READINGS_DB}';

    -- Readings table
    -- This tables contains the readings for assets.
    -- An asset can be a south with multiple sensor, a single sensor,
    -- a software or anything that generates data that is sent to Fledge
    --
    CREATE TABLE  '${READINGS_DB}'.'${READINGS_TABLE}' (
        id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
        reading    JSON                        NOT NULL DEFAULT '{}',            -- The json object received
        user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),      -- UTC time
        ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))       -- UTC time
    );

    .quit
EOF`

    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then

        schema_update_log "err" "xxx Failure in upgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
        exit 1
    fi


}

create_all_readings() {

    cat "$tmp_file"  | while read table_id db_id asset_code; do

        schema_update_log "debug" "upgrade: create_all_readings - dbid :$db_id: table id :$table_id: " "all" "pretty"

        # The first readings iss created by the sql script
        if [ "$table_id" != "1" ]; then

            create_readings "readings_$db_id" "readings_$table_id"
        fi
    done
}

#
#
# Populate the proper readings table
#
# $1 = READINGS_DB
# $2 = Readings table
# $3 = Asset code
#
populate_readings() {

    #// FIXME_I:
    SQL_COMMAND="TODO"

    READINGS_DB="$1"
    READINGS_TABLE="$2"
    ASSET_CODE="$3"

    file_path=$(dirname ${DEFAULT_SQLITE_DB_FILE_READINGS})
    readings_file="${file_path}/${READINGS_DB}.db"

    schema_update_log "debug" "upgrade: populate_readings - file :$readings_file: db :$READINGS_DB: table :$READINGS_TABLE: asset code :$ASSET_CODE:" "all" "pretty"

    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF
    ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'                 AS 'fledge';
    ATTACH DATABASE '${readings_file}'                          AS '${READINGS_DB}';
    ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

    INSERT INTO '${READINGS_DB}'.'${READINGS_TABLE}'
        SELECT
            id,
            reading,
            user_ts,
            ts
        FROM readings.readings
        WHERE asset_code = '${ASSET_CODE}';

    .quit
EOF`

    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then

        schema_update_log "err" "xxx Failure in upgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
        exit 1
    fi

}

populate_all_readings() {

    cat "$tmp_file"  | while read table_id db_id asset_code; do

        schema_update_log "debug" "upgrade: populate_all_readings - db id :$db_id: table id :$table_id: asset code :$asset_code: " "all" "pretty"

        populate_readings "readings_$db_id" "readings_$table_id" "$asset_code"
    done
}

export_readings_list() {

    SQL_COMMAND="TODO"

    schema_update_log "debug" "upgrade: export_readings_list - tmp_file :$tmp_file: SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "all" "pretty"

    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" > $tmp_file <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';

SELECT
    table_id,
    db_id,
    asset_code
FROM readings_1.asset_reading_catalogue;

.quit
EOF`


    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then

        schema_update_log "err" "xxx export_readings_list - Failure in upgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
        exit 1
    fi

}




#
cleanup_db() {

    schema_update_log "debug" "upgrade: cleanup - SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "all" "pretty"

    #
    # Clean up - database
    #
    SQL_COMMAND="${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'                 AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'        AS 'readings_1';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

DROP TABLE readings.readings;

.quit
EOF"

    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'                 AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'        AS 'readings_1';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

DROP TABLE readings.readings;

.quit
EOF`

    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then
        schema_update_log "err" "Failure in upgrade command [${SQL_COMMAND}]: result [${COMMAND_OUTPUT}]. Exiting" "all" "pretty"
        exit 1
    fi

    #
    # Clean up - file system
    #
    file_path=$(dirname ${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE})
    file_name_path="${file_path}/readings.db*"

    schema_update_log "debug" "upgrade: cleanup - deleting ${file_name_path}" "all" "pretty"

    rm ${file_name_path}
    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then
        schema_update_log "notice" "Failure in upgrade, files [${file_name_path}] can't be deleted. Proceeding" "all" "pretty"
    fi


    #// FIXME_I:
#    echo "--- s0 -----------------------------------------------------------------------------------------:"
#    lsof  /home/foglamp/Development/fledge/data/readings.db
#    echo "--- s1 -----------------------------------------------------------------------------------------:"
#    ls -l ${FLEDGE_ROOT}/data
#    echo "--- s2 -----------------------------------------------------------------------------------------:"
#    ls -l /home/foglamp/Development/fledge/data
}


#
# Main
#
export n_readings_allocate=15
export tmp_file=/tmp/$$
export IFS="|"

schema_update_log "debug" "upgrade: SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "all" "pretty"

execute_sql_file

calculate_dbid ${n_readings_allocate}

export_readings_list

create_all_database_files

create_all_readings

populate_all_readings

cleanup_db

unset IFS

#// FIXME_I:
#3exit 1

exit 0
