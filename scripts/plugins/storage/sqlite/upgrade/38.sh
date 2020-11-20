#!/bin/bash

# Include logging
. $FLEDGE_ROOT/scripts/common/write_log.sh

# Logger wrapper
schema_update_log() {
    write_log "Upgrade" "scripts.plugins.storage.${PLUGIN_NAME}schema_update" "$1" "$2" "$3" "$4"
}

#
# Updates asset_reading_catalogue setting the proper db id in relation to how many tables per db
# should be managed
#
calculate_db_id() {

    declare _n_readings_allocate=$1

    schema_update_log "debug" "calculate_db_id: SQLITE_SQL :$SQLITE_SQL: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

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
        schema_update_log "err" "calculate_db_id - Failure in upgrade command [${SQL_COMMAND}] result [${COMMAND_OUTPUT}]. Exiting" "all" "pretty"
        exit 1
    fi
}

#
# Executes the .sql file associated to this shell script
#
execute_sql_file() {

    schema_update_log "debug" "execute_sql_file: SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

    SQL_COMMAND="${SQLITE_SQL} \"${DEFAULT_SQLITE_DB_FILE}\" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

.read '${sql_file}'

.quit
EOF"

    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

.read '${sql_file}'
.quit
EOF`

    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then
        schema_update_log "err" "execute_sql_file - Failure in upgrade command [${SQL_COMMAND}] result [${COMMAND_OUTPUT}]. Exiting" "all" "pretty"
        exit 1
    fi
}

#
# Creates a database file given the file name
#
create_database_file() {

    readings_file=$1

    file_path=$(dirname "${DEFAULT_SQLITE_DB_FILE_READINGS}")
    file_name_path="${file_path}/${readings_file}.db"

    # Creates the file if it was not already created
    if [ ! -f "${file_name_path}" ]; then

        schema_update_log "debug" "create_database_file - file path :$file_name_path:" "logonly" "pretty"

        # Created datafile
        COMMAND_OUTPUT=$(${SQLITE_SQL} ${file_name_path} .databases 2>&1)

        ret_code=$?
        if [ "${ret_code}" -ne 0 ]; then
            schema_update_log "err" "create_database_file - Failure in upgrade command [${SQL_COMMAND}] result [${COMMAND_OUTPUT}]. Exiting" "all" "pretty"
            exit 1
        fi
    fi
}

#
# Creates all the required database file in relation to the asset_reading_catalogue content
#
create_all_database_files() {

    declare db_name

    cat "$tmp_file"  | while read -r table_id db_id asset_code; do

        # The first database is created by the upgrade process
        if [ "$db_id" != "1" ]; then

            db_name="readings_$db_id"

            schema_update_log "debug" "create_all_database_file - db name :$db_name: db id :$db_id: table id :$table_id: asset code :$asset_code: " "logonly" "pretty"
            create_database_file "$db_name"
        fi
    done
}

#
# Creates a reading table given the database and the table name that should be used
#
create_readings() {

    READINGS_DB="$1"
    READINGS_TABLE="$2"

    file_path=$(dirname ${DEFAULT_SQLITE_DB_FILE_READINGS})
    readings_file="${file_path}/${READINGS_DB}.db"

    schema_update_log "debug" "create_readings - db :$READINGS_DB: table :$READINGS_TABLE: asset code :$ASSET_CODE:" "logonly" "pretty"

    SQL_COMMAND="${SQLITE_SQL} \"${DEFAULT_SQLITE_DB_FILE}\" 2>&1 <<EOF

    ATTACH DATABASE '${readings_file}'                          AS '${READINGS_DB}';

    CREATE TABLE  '${READINGS_DB}'.'${READINGS_TABLE}' (
        id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
        reading    JSON                        NOT NULL DEFAULT '{}',            -- The json object received
        user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),      -- UTC time
        ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))       -- UTC time
    );

.quit
EOF"

    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

    ATTACH DATABASE '${readings_file}'                          AS '${READINGS_DB}';

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

        schema_update_log "err" "create_readings - Failure in upgrade command [${SQL_COMMAND}] result [${COMMAND_OUTPUT}]. Exiting" "all" "pretty"
        exit 1
    fi


}

#
# Creates all the required reading tables in relation to the asset_reading_catalogue content
#
create_all_readings() {

    cat "$tmp_file"  | while read table_id db_id asset_code; do

        schema_update_log "debug" "create_all_readings - dbid :$db_id: table id :$table_id: " "logonly" "pretty"

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

    READINGS_DB="$1"
    READINGS_TABLE="$2"
    ASSET_CODE="$3"

    file_path=$(dirname ${DEFAULT_SQLITE_DB_FILE_READINGS})
    readings_file="${file_path}/${READINGS_DB}.db"

    schema_update_log "debug" "populate_readings - file :$readings_file: db :$READINGS_DB: table :$READINGS_TABLE: asset code :$ASSET_CODE:" "logonly" "pretty"

    SQL_COMMAND="${SQLITE_SQL} \"${DEFAULT_SQLITE_DB_FILE}\" 2>&1 <<EOF

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
EOF"

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

        schema_update_log "err" "populate_readings - Failure in upgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
        exit 1
    fi

}

#
# Populates all the required reading tables in relation to the asset_reading_catalogue content
#
populate_all_readings() {

    cat "$tmp_file"  | while read table_id db_id asset_code; do

        schema_update_log "debug" "populate_all_readings - db id :$db_id: table id :$table_id: asset code :$asset_code: " "logonly" "pretty"

        populate_readings "readings_$db_id" "readings_$table_id" "$asset_code"
    done
}

#
# Export the asset_reading_catalogue content into a temporary file
#
export_readings_list() {

    schema_update_log "debug" "export_readings_list - tmp_file :$tmp_file: SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

    SQL_COMMAND="${SQLITE_SQL} \"${DEFAULT_SQLITE_DB_FILE}\" 2>&1 <<EOF

        ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';

        SELECT
            table_id,
            db_id,
            asset_code
        FROM readings_1.asset_reading_catalogue;

.quit
EOF"
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

        schema_update_log "err" "export_readings_list - Failure in upgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
        exit 1
    fi

}

#
# Cleanups database and file system
#
cleanup_db() {

    schema_update_log "debug" "cleanup - SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

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
        schema_update_log "err" "cleanup_db - Failure in upgrade command [${SQL_COMMAND}]: result [${COMMAND_OUTPUT}]. Proceeding" "all" "pretty"
    fi

    #
    # Clean up - file system
    #
    file_path=$(dirname ${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE})
    file_name_path="${file_path}/readings.db*"

    schema_update_log "debug" "cleanup - deleting ${file_name_path}" "logonly" "pretty"

    rm ${file_name_path}
    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then
        schema_update_log "notice" "cleanup_db - Failure in upgrade, files [${file_name_path}] can't be deleted. Proceeding" "logonly" "pretty"
    fi
}


#
# Main
#
export n_readings_allocate=15
export tmp_file=/tmp/$$
export IFS="|"

schema_update_log "debug" "$0 - SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

execute_sql_file

calculate_db_id ${n_readings_allocate}

export_readings_list

create_all_database_files

create_all_readings

populate_all_readings

cleanup_db

unset IFS

exit 0
