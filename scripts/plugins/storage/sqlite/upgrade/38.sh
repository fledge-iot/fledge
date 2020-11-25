#!/bin/bash

# Include logging
. $FLEDGE_ROOT/scripts/common/write_log.sh

# Logger wrapper
schema_update_log() {
    write_log "Upgrade" "scripts.plugins.storage.${PLUGIN_NAME}schema_update" "$1" "$2" "$3" "$4"
}

calculate_table_id() {

    declare _n_readings_allocate=$1

    schema_update_log "debug" "calculate_db_id: SQLITE_SQL :$SQLITE_SQL: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

    SQL_COMMAND="${SQLITE_SQL} \"${DEFAULT_SQLITE_DB_FILE}\" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';

INSERT INTO readings_1.asset_reading_catalogue
SELECT
    (tb.table_id - ((db_id - 1) * 15))

    table_id,
    db_id,
    asset_code
FROM readings_1.asset_reading_catalogue_tmp tb;

.quit
EOF"


    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';

INSERT INTO readings_1.asset_reading_catalogue
SELECT
    (tb.table_id - ((db_id - 1) * 15))

    table_id,
    db_id,
    asset_code
FROM readings_1.asset_reading_catalogue_tmp tb;

.quit
EOF`

    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then
        schema_update_log "err" "calculate_db_id - Failure in upgrade command [${SQL_COMMAND}] result [${COMMAND_OUTPUT}]. Exiting" "all" "pretty"
        exit 1
    fi
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

UPDATE readings_1.asset_reading_catalogue_tmp SET db_id=(((table_id - 1) / '${_n_readings_allocate}') +1);

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
# Updates the db with the max used database id
#
update_max_db_id() {

    declare _db_id_max=$1

    schema_update_log "debug" "calculate_db_id: SQLITE_SQL :$SQLITE_SQL: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

    SQL_COMMAND="${SQLITE_SQL} \"${DEFAULT_SQLITE_DB_FILE}\" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';

UPDATE readings_1.configuration_readings SET db_id_Last=${_db_id_max};

.quit
EOF"


    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'     AS 'readings_1';

UPDATE readings_1.configuration_readings SET db_id_Last=${_db_id_max};

.quit
EOF`

    ret_code=$?

    if [ "${ret_code}" -ne 0 ]; then
        schema_update_log "err" "calculate_db_id - Failure in upgrade command [${SQL_COMMAND}] result [${COMMAND_OUTPUT}]. Exiting" "all" "pretty"
        exit 1
    fi
}

#
# Creates all the required database file in relation to the asset_reading_catalogue content
#
create_all_database_files() {

    declare _n_db_allocate=$1
    declare db_name
    declare db_id_start

    while read -r table_id db_id asset_code; do

        # The first database is created by the upgrade process
        if [ "$db_id" != "1" ]; then

            if [[ $db_id > $db_id_max ]]
            then
                db_id_max=${db_id}
            fi
            db_name="readings_$db_id"

            schema_update_log "debug" "create_all_database_file - db name :$db_name: db id :$db_id: " "logonly" "pretty"
            schema_update_log "debug" "create_all_database_file - db name :$db_name: db id :$db_id: table id :$table_id: asset code :$asset_code: " "logonly" "pretty"
            create_database_file "$db_name"
        fi
    done < "$tmp_file"

    # Creates all the required databases if not already created
    if [[ $db_id_max < $_n_db_allocate ]]
    then
        db_id_start=$((${db_id_max} +1))

        # The first database is created by the upgrade process
        for ((db_id=${db_id_start}; db_id<=${_n_db_allocate}; db_id++)); do

            db_name="readings_$db_id"

            schema_update_log "debug" "create_all_database_file - db name :$db_name: db id :$db_id: " "logonly" "pretty"
            create_database_file "$db_name"
        done
        db_id_max=$_n_db_allocate
    fi
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

    CREATE INDEX  '${READINGS_DB}'.'${READINGS_TABLE}_ix3' ON '${READINGS_TABLE}' (user_ts desc);

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

    CREATE INDEX  '${READINGS_DB}'.'${READINGS_TABLE}_ix3' ON '${READINGS_TABLE}' (user_ts desc);

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

    declare _n_db_allocate=$1
    declare _n_readings_allocate=$2

    for ((db_id=1; db_id<=${_n_db_allocate}; db_id++)); do

        for ((table_id=1; table_id<=${_n_readings_allocate}; table_id++)); do

            schema_update_log "debug" "create_all_readings - dbid :$db_id: table id :${db_id}_${table_id}: " "logonly" "pretty"

            # The first reading table is created by the sql script
            if [[  "$db_id" != "1" || "$table_id" != "1" ]]
            then

                create_readings "readings_$db_id" "readings_${db_id}_${table_id}"
            fi
        done
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

        populate_readings "readings_$db_id" "readings_${db_id}_${table_id}" "$asset_code"
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
        FROM readings_1.asset_reading_catalogue
        ORDER BY db_id, table_id;

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
DROP TABLE readings_1.asset_reading_catalogue_tmp;

.quit
EOF"

    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF

ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'                 AS 'fledge';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}'        AS 'readings_1';
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE}' AS 'readings';

DROP TABLE readings.readings;
DROP TABLE readings_1.asset_reading_catalogue_tmp;

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

#// FIXME_I: ro remove
e_syscls

export FLEDGE_DEV=/home/foglamp/Development/fledge;export FLEDGE_DEP=/usr/local/fledge;export FLEDGE_ROOT=${FLEDGE_DEV};export FLEDGE_SCRIPT=${FLEDGE_ROOT}/scripts/fledge;export FLEDGE_DATA=${FLEDGE_ROOT}/data;export PYTHONPATH=${FLEDGE_ROOT}/python;export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:$FLEDGE_ROOT/cmake_build/C/lib;export PATH=${PATH}:/home/foglamp/wrk/scripts
export sql_file="/home/foglamp/Development/fledge/scripts/plugins/storage/sqlite/upgrade/38.sql"
export SQLITE_SQL="$(command -v sqlite3)"
export DEFAULT_SQLITE_DB_FILE="${FLEDGE_DATA}/fledge.db"
export DEFAULT_SQLITE_DB_FILE_READINGS_BASE="${FLEDGE_DATA}/readings"
export DEFAULT_SQLITE_DB_FILE_READINGS="${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}_1.db"
export DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE="${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}.db"

echo "DBG `id`"
ls -l  ${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}_*.*
rm -f ${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}_*.*
COMMAND_OUTPUT=`${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE_READINGS} .databases 2>&1`
RET_CODE=$?


# END


#
# Main
#
export n_db_allocate=3
export n_readings_allocate=15
export tmp_file=/tmp/$$
export IFS="|"

schema_update_log "debug" "$0 - SQLITE_SQL :$SQLITE_SQL: sql_file :$sql_file: DEFAULT_SQLITE_DB_FILE :$DEFAULT_SQLITE_DB_FILE: DEFAULT_SQLITE_DB_FILE_READINGS :$DEFAULT_SQLITE_DB_FILE_READINGS:" "logonly" "pretty"

execute_sql_file

calculate_db_id ${n_readings_allocate}

calculate_table_id ${n_readings_allocate}

export_readings_list

db_id_max=0
create_all_database_files ${n_db_allocate}   # updates db_id_max
update_max_db_id          ${db_id_max}   # updates db_id_max
create_all_readings       ${db_id_max} ${n_readings_allocate}

populate_all_readings

cleanup_db

unset IFS

exit 0
