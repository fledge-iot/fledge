#!/bin/bash

##--------------------------------------------------------------------
## Copyright (c) 2017-2018 OSIsoft, LLC
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##--------------------------------------------------------------------

# Script input parameters
# $1 is action (start|stop|status|init|reset|purge|help)
# $2 is db schema (i.e 35)

__author__="Massimiliano Pinto"
__version__="1.0"

set -e

PLUGIN="sqlite"

# Set default DB file
if [ ! "${DEFAULT_SQLITE_DB_FILE}" ]; then
    export DEFAULT_SQLITE_DB_FILE="${FLEDGE_DATA}/fledge.db"
fi

# if the script changes the value it forces the overwrite of the value every times
# it is needed when the storage plugin is changed
if [ ! "${DEFAULT_SQLITE_DB_FILE_READINGS_FLAG}" ]; then

    if [ ! "${DEFAULT_SQLITE_DB_FILE_READINGS}" ]; then

        export DEFAULT_SQLITE_DB_FILE_READINGS_FLAG=1
    fi
fi

if [ "${DEFAULT_SQLITE_DB_FILE_READINGS_FLAG}" ]; then

    export DEFAULT_SQLITE_DB_FILE_READINGS_BASE="${FLEDGE_DATA}/readings"
    export DEFAULT_SQLITE_DB_FILE_READINGS="${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}_1.db"
    export DEFAULT_SQLITE_DB_FILE_READINGS_SINGLE="${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}.db"
fi

USAGE="Usage: `basename ${0}` {start|stop|status|init|reset|purge|help}"

# Check FLEDGE_ROOT
if [ -z ${FLEDGE_ROOT+x} ]; then
    # Set FLEDGE_ROOT as the default directory
    FLEDGE_ROOT="/usr/local/fledge"
fi

# Check if the default directory exists
if [[ ! -d "${FLEDGE_ROOT}" ]]; then

    # Here we cannot use the logger because we cannot find the write_log script.
    # But it is ok, because the script is called with source and if it is called
    # as standalone script the echo will be captured.
    echo "Fledge cannot be executed: ${FLEDGE_ROOT} is not a valid directory."
    echo "Create the enviroment variable FLEDGE_ROOT before using Fledge."
    echo "Specify the base directory for Fledge and set the variable with:"
    echo "export FLEDGE_ROOT=<basedir>"
    exit 1

fi

##########
## INCLUDE SECTION
##########
. $FLEDGE_ROOT/scripts/common/get_engine_management.sh
. $FLEDGE_ROOT/scripts/common/write_log.sh


# Logger wrapper
sqlite_log() {
    write_log "Storage" "script.plugin.storage.sqlite" "$1" "$2" "$3" "$4"
}

# Check first SQLite 3 with static library command line is available
SQLITE_SQL="$FLEDGE_ROOT/plugins/storage/sqlite/sqlite3"
if ! [[ -x "${SQLITE_SQL}" ]]; then
# Check system default SQLite 3 command line is available
    if ! [[ -x "$(command -v sqlite3)" ]]; then
        sqlite_log "info" "The sqlite3 command cannot be found. Is SQLite3 installed?" "outonly" "pretty"
        sqlite_log "info" "If SQLite3 is installed, check if the bin dir is in the PATH." "outonly" "pretty"
        exit 1
    else
        SQLITE_SQL="$(command -v sqlite3)"
    fi
fi

## SQLite3 Start
sqlite_start() {

    # Check the status of the server
    if [[ "$1" != "skip" ]]; then
        result=`sqlite_status "silent"`
    else
        result=`sqlite_status "skip"`
    fi
    case "$result" in
        "0")
            # SQLilte3 DB found already running.
            if [[ "$1" == "noisy" ]]; then
                sqlite_log "info" "SQLite3 database is ready." "all" "pretty"
            else
                if [[ "$1" != "skip" ]]; then
                            sqlite_log "info" "SQLite3 database is ready." "logonly" "pretty"
                fi
            fi
            ;;

        "1")
            # Database not found, created datafile
            COMMAND_OUTPUT=`${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} .databases 2>&1`
            RET_CODE=$?
            if [ "${RET_CODE}" -ne 0 ]; then
                sqlite_log "err" "Error creating SQLite3 database ${DEFAULT_SQLITE_DB_FILE}: ${COMMAND_OUTPUT}" "all" "pretty"
                exit 1
            fi

            # File created
            if [[ "$1" == "noisy" ]]; then
                sqlite_log "info" "SQLite3 database ${DEFAULT_SQLITE_DB_FILE} has been created." "all" "pretty"
            else
                sqlite_log "info" "SQLite3 database ${DEFAULT_SQLITE_DB_FILE} has been created." "logonly" "pretty"
            fi
           ;;

        *)
            sqlite_log "err" "Unknown SQLite database return status." "all"
            exit 1
            ;;
    esac

    # Check the presence of the readingds.db datafile
    if [[ "$1" != "skip" ]]; then
        result=`sqlite_status_readings "silent"`
    else
        result=`sqlite_status_readings "skip"`
    fi

    case "$result" in
        "0")
            # SQLilte3 DB found already running.
            if [[ "$1" == "noisy" ]]; then
                sqlite_log "info" "SQLite3 readings database is ready." "all" "pretty"
            else
                if [[ "$1" != "skip" ]]; then
                            sqlite_log "info" "SQLite3 readings database is ready." "logonly" "pretty"
                fi
            fi
            ;;

        "1")
            # Database not found, created datafile
            COMMAND_OUTPUT=`${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE_READINGS} .databases 2>&1`
            RET_CODE=$?
            if [ "${RET_CODE}" -ne 0 ]; then
                sqlite_log "err" "Error creating SQLite3 database ${DEFAULT_SQLITE_DB_FILE_READINGS}: ${COMMAND_OUTPUT}" "all" "pretty"
                exit 1
            fi

            # File created
            if [[ "$1" == "noisy" ]]; then
                sqlite_log "info" "SQLite3 database ${DEFAULT_SQLITE_DB_FILE_READINGS} has been created." "all" "pretty"
            else
                sqlite_log "info" "SQLite3 database ${DEFAULT_SQLITE_DB_FILE_READINGS} has been created." "logonly" "pretty"
            fi
           ;;

        *)
            sqlite_log "err" "Unknown SQLite database return status." "all"
            exit 1
            ;;
    esac

    # Check if the fledge database has been created
    FOUND_SCHEMAS=`${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} "ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge'; SELECT name FROM sqlite_master WHERE type='table'"`

    if [ ! "${FOUND_SCHEMAS}" ]; then
        # Create the Fledge database
         sqlite_reset "$1" "immediate"
    else
        # Check if the readings database has been created
        FOUND_SCHEMAS=`${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE_READINGS} "ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}' AS 'readings'; SELECT name FROM sqlite_master WHERE type='table'"`

        if [ ! "${FOUND_SCHEMAS}" ]; then
            # Create the readings database
            sqlite_reset_db_readings "$1" "immediate"
        fi
    fi

    # Fledge DB schema update: Fledge version is $2, $1 is log verbosity
    sqlite_schema_update $2 $1
}


## SQLite  Stop
sqlite_stop() {

    # Since the script may be called with "source", this condition must be set
    # and the else must be maintained because exit can't be used

    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "Fledge database is SQLite3. No stop/start actions available" "all" "pretty"
    else
        sqlite_log "info" "Fledge database is SQLite3. No stop/start actions available" "logonly" "pretty"
    fi

    return 0
}


## SQLite3 Reset
sqlite_reset() {

    if [[ $2 != "immediate" ]]; then
        echo "This script will remove all data stored in the SQLite3 datafiles:"
        echo "'${DEFAULT_SQLITE_DB_FILE}'"
        echo "'${DEFAULT_SQLITE_DB_FILE_READINGS}'"
        echo -n "Enter YES if you want to continue: "
        read continue_reset

        if [ "$continue_reset" != 'YES' ]; then
            echo "Goodbye."
            # This is ok because it means that the script is called from command line
            exit 0
        fi
    fi

    sqlite_reset_db_fledge   "$1" "$2"
    sqlite_reset_db_readings "$1" "$2"
}

sqlite_reset_db_fledge() {
    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "Building the metadata for the Fledge Plugin '${PLUGIN}' ..." "all" "pretty"
    else
        sqlite_log "info" "Building the metadata for the Fledge Plugin '${PLUGIN}' ..." "logonly" "pretty"
    fi

    # 1- Drop all databases in DEFAULT_SQLITE_DB_FILE
    if [ -f "${DEFAULT_SQLITE_DB_FILE}" ]; then
        rm ${DEFAULT_SQLITE_DB_FILE} ||
        sqlite_log "err" "Cannot drop database '${DEFAULT_SQLITE_DB_FILE}' for the Fledge Plugin '${PLUGIN}'" "all" "pretty"
    fi
    rm -f ${DEFAULT_SQLITE_DB_FILE}-journal ${DEFAULT_SQLITE_DB_FILE}-wal ${DEFAULT_SQLITE_DB_FILE}-shm
    # 2- Create new datafile an apply init file
    INIT_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF
PRAGMA page_size = 4096;
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge';
.read '${INIT_SQL}'
.quit
EOF`

    RET_CODE=$?
    # Exit on failure
    if [ "${RET_CODE}" -ne 0 ]; then
        sqlite_log "err" "Cannot initialize '${DEFAULT_SQLITE_DB_FILE}' for the Fledge Plugin '${PLUGIN}': ${INIT_OUTPUT}. Exiting" "all" "pretty"
        exit 2
    fi

    # Log success
    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "Build complete for Fledge Plugin '${PLUGIN} in database '${DEFAULT_SQLITE_DB_FILE}'." "all" "pretty"
    else
        sqlite_log "info" "Build complete for Fledge Plugin '${PLUGIN} in database '${DEFAULT_SQLITE_DB_FILE}'." "logonly" "pretty"
    fi

}

sqlite_create_db_readings() {

    # 2- Create new datafile an apply init file
    INIT_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE_READINGS}" 2>&1 <<EOF
PRAGMA page_size = 4096;
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE_READINGS}' AS 'readings_1';
.read '${INIT_READINGS_SQL}'
.quit
EOF`

    RET_CODE=$?
    # Exit on failure
    if [ "${RET_CODE}" -ne 0 ]; then
        sqlite_log "err" "Cannot initialize '${DEFAULT_SQLITE_DB_FILE_READINGS}' for the Fledge Plugin '${PLUGIN}': ${INIT_OUTPUT}. Exiting" "all" "pretty"
        exit 2
    fi

    # Log success
    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "Build complete for Fledge Plugin '${PLUGIN} in database '${DEFAULT_SQLITE_DB_FILE_READINGS}'." "all" "pretty"
    else
        sqlite_log "info" "Build complete for Fledge Plugin '${PLUGIN} in database '${DEFAULT_SQLITE_DB_FILE_READINGS}'." "logonly" "pretty"
    fi
}

sqlite_reset_db_readings() {

    # 1- Drop all databases in DEFAULT_SQLITE_DB_FILE_READINGS
    if [ -f "${DEFAULT_SQLITE_DB_FILE_READINGS}" ]; then
        rm ${DEFAULT_SQLITE_DB_FILE_READINGS} ||
        sqlite_log "err" "Cannot drop database '${DEFAULT_SQLITE_DB_FILE_READINGS}' for the Fledge Plugin '${PLUGIN}'" "all" "pretty"
    fi
    rm -f ${DEFAULT_SQLITE_DB_FILE_READINGS}-journal ${DEFAULT_SQLITE_DB_FILE_READINGS}-wal ${DEFAULT_SQLITE_DB_FILE_READINGS}-shm
    # Delete all the readings databases if any
    rm -f ${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}*.db
    rm -f ${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}*.db-journal
    rm -f ${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}*.db-wal
    rm -f ${DEFAULT_SQLITE_DB_FILE_READINGS_BASE}*.db-shm

    sqlite_create_db_readings
}



## SQLite 3 Database Status
#
# NOTE: You can call this script with $1 = silent to avoid non output errors
#
# Returns:
#   0 - SQLite3 datafile found
#   1 - SQLite3 datafile NOT found
sqlite_status() {
    if [ -f "${DEFAULT_SQLITE_DB_FILE}" ]; then
        if [[ "$1" == "noisy" ]]; then
            sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE}' ready." "all" "pretty"
        else
            if [[ "$1" != "skip" ]]; then
                sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE}' ready." "logonly" "pretty"
            fi
        fi
        echo "0"
    else
        if [[ "$1" == "noisy" ]]; then
            sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE}' not found." "all" "pretty"
        else
            sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE}' not found." "logonly" "pretty"
        fi
        echo "1"
    fi
}

## SQLite 3 Database Status - checks the presence of the readingds.db datafile
#
# NOTE: You can call this script with $1 = silent to avoid non output errors
#
# Returns:
#   0 - SQLite3 readingds datafile found
#   1 - SQLite3 readingds datafile NOT found
sqlite_status_readings() {
    if [ -f "${DEFAULT_SQLITE_DB_FILE_READINGS}" ]; then
        if [[ "$1" == "noisy" ]]; then
            sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE_READINGS}' ready." "all" "pretty"
        else
            if [[ "$1" != "skip" ]]; then
                sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE_READINGS}' ready." "logonly" "pretty"
            fi
        fi
        echo "0"
    else
        if [[ "$1" == "noisy" ]]; then
            sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE_READINGS}' not found." "all" "pretty"
        else
            sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE_READINGS}' not found." "logonly" "pretty"
        fi
        echo "1"
    fi
}


## SQLite schema update entry point
#
sqlite_schema_update() {

    # Current starting Fledge version
    NEW_VERSION=$1
    # DB table
    VERSION_TABLE="version"
    # Check first if the version table exists
    VERSION_QUERY="SELECT name FROM sqlite_master WHERE type='table' and name = '${VERSION_TABLE}'"
    COMMAND_VERSION="${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} \"${VERSION_QUERY}\""
    CURR_VER=`eval ${COMMAND_VERSION}`
    ret_code=$?
    if [ ! "${CURR_VER}" ] || [ "${ret_code}" -ne 0 ]; then
        sqlite_log "error" "Error checking Fledge DB schema version: "\
"the table '${VERSION_TABLE}' doesn't exist. Exiting" "all" "pretty"
        return 1
    fi

    # Fetch Fledge DB version
    CURR_VER=`${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} "ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge'; SELECT id FROM fledge.${VERSION_TABLE}" | tr -d ' '`
    if [ ! "${CURR_VER}" ]; then
        # No version found set DB version now
        INSERT_QUERY="ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge'; BEGIN; INSERT INTO fledge.${VERSION_TABLE} (id) VALUES('${NEW_VERSION}'); COMMIT;"
        COMMAND_INSERT="${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} \"${INSERT_QUERY}\""
        CURR_VER=`eval "${COMMAND_INSERT}"`
        ret_code=$?

        SET_VERSION_MSG="Fledge DB version not found in fledge.'${VERSION_TABLE}', setting version [${NEW_VERSION}]"
        if [[ "$2" == "noisy" ]]; then
            sqlite_log "info" "${SET_VERSION_MSG}" "all" "pretty"
        else 
            sqlite_log "info" "${SET_VERSION_MSG}" "logonly" "pretty"
        fi
    else
        # Only if DB version is not equal to starting Fledge version we try schema update
        if [ "${CURR_VER}" != "${NEW_VERSION}" ]; then
            sqlite_log "info" "Detected '${PLUGIN}' Fledge DB schema change from version [${CURR_VER}]"\
" to [${NEW_VERSION}], applying Upgrade/Downgrade ..." "all" "pretty"
            SCHEMA_UPDATE_SCRIPT="$FLEDGE_ROOT/scripts/plugins/storage/${PLUGIN}/schema_update.sh"
            if [ -s "${SCHEMA_UPDATE_SCRIPT}" ] && [ -x "${SCHEMA_UPDATE_SCRIPT}" ]; then
                # Call the schema update script
                ${SCHEMA_UPDATE_SCRIPT} "${CURR_VER}" "${NEW_VERSION}" "${SQLITE_SQL}"
                update_code=$?
                return ${update_code}
            else
                sqlite_log "err" "Cannot find schema update script '${SCHEMA_UPDATE_SCRIPT}'. Exiting" "all" "pretty"
                exit 2
            fi
        else
            # Just log up-to-date
            if [[ "$2" != "skip" ]]; then
                sqlite_log "info" "Fledge DB schema is up to date to version [${CURR_VER}]" "logonly" "pretty"
            fi
            return 0
        fi
    fi
}


## SQLite Help
sqlite_help() {

    echo "${USAGE}
SQLite3 Storage Layer plugin init script. 
The script is used to control the SQLite3 plugin as database for Fledge
Arguments:
 start   - Start the database server (when managed)
           If the server has not been initialized, it also initialize it
 stop    - Stop the database server (when managed)
 status  - Check the status of the database server
 reset   - Bring the database server to the original installation.
           WARNING: all the data stored in the server will be lost!
 init    - Database check: if Fledge database does not exist
           it will be created.
 purge   - Purge all readings data and non-configuration data stored in the database.
           WARNING: all the data stored in the affected tables will be lost!
 help    - This text

 managed   - The database server is embedded in Fledge
 unmanaged - The database server is not embedded in Fledge"

}

## SQLite3 purge all readings and non-configuration data
sqlite_purge() {
    echo "This script will remove all readings data and non-configuration data stored in the SQLite3 datafiles:"
    echo "'${DEFAULT_SQLITE_DB_FILE}'"
    echo "'${DEFAULT_SQLITE_DB_FILE_READINGS}'"
    echo -n "Enter YES if you want to continue: "
    read continue_purge

    if [ "$continue_purge" != 'YES' ]; then
        echo "Goodbye."
        # This is ok because it means that the script is called from command line
        exit 0
    fi

    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "Purging data for the Fledge Plugin '${PLUGIN}' ..." "all" "pretty"
    else
        sqlite_log "info" "Purging data for the Fledge Plugin '${PLUGIN}' ..." "logonly" "pretty"
    fi

    # Purge database content
    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge';
UPDATE fledge.statistics SET value = 0, previous_value = 0, ts = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime');
DELETE FROM fledge.asset_tracker; 
DELETE FROM fledge.sqlite_sequence WHERE name='asset_tracker';
DELETE FROM fledge.tasks;
DELETE FROM fledge.statistics_history;
DELETE FROM sqlite_sequence WHERE name='statistics_history';
DELETE FROM fledge.log;
DELETE FROM sqlite_sequence WHERE name='log';
DELETE FROM fledge.plugin_data;
DELETE FROM fledge.omf_created_objects;
DELETE FROM fledge.user_logins;
UPDATE fledge.streams SET last_object = 0, ts = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime');
VACUUM;
.quit
EOF`

    RET_CODE=$?
    if [ "${RET_CODE}" -ne 0 ]; then
        sqlite_log "err" "Failure in purge command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
        return 1
    fi

    # Log success
    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "Purge complete for Fledge Plugin '${PLUGIN} in database '${DEFAULT_SQLITE_DB_FILE}'." "all" "pretty"
    else
        sqlite_log "info" "Purge complete for Fledge Plugin '${PLUGIN} in database '${DEFAULT_SQLITE_DB_FILE}'." "logonly" "pretty"
    fi

    # Remove all readings
    sqlite_reset_db_readings
}

##################
### Main Logic ###
##################

# Set FLEDGE_DATA if it does not exist
if [ -z ${FLEDGE_DATA+x} ]; then
    FLEDGE_DATA="${FLEDGE_ROOT}/data"
fi

# Check if $FLEDGE_DATA exists
if [[ ! -d ${FLEDGE_DATA} ]]; then
    sqlite_log "err" "Fledge cannot be executed: ${FLEDGE_DATA} is not a valid directory." "all" "pretty"
    exit 1
fi

engine_management="false"

# Settings if the database is managed by Fledge
case "$engine_management" in
    "true")

	# SQLite does not support managed storage. Ignore this option
        print_output="silent"
        MANAGED=false
        ;;
    
    "false")

        # This is an explicit input, which means that we do not want to send
        # messages when we start or stop the server
        print_output="silent"
        MANAGED=false
        ;;

    *)

        # Unexpected value from the configuration file
        sqlite_log "err" "Fledge cannot start." "all" "pretty"
        sqlite_log "err" "Missing plugin information from the storage microservice" "all" "pretty"
        exit 1
        ;;

esac

# Check if the init.sql file exists
# Attempt 1: deployment path
if [[ -e "$FLEDGE_ROOT/plugins/storage/sqlite/init.sql" ]]; then
    INIT_SQL="$FLEDGE_ROOT/plugins/storage/sqlite/init.sql"
    INIT_READINGS_SQL="$FLEDGE_ROOT/plugins/storage/sqlite/init_readings.sql"
else
    # Attempt 2: development path
    if [[ -e "$FLEDGE_ROOT/scripts/plugins/storage/sqlite/init.sql" ]]; then
        INIT_SQL="$FLEDGE_ROOT/scripts/plugins/storage/sqlite/init.sql"
        INIT_READINGS_SQL="$FLEDGE_ROOT/scripts/plugins/storage/sqlite/init_readings.sql"
    else
        sqlite_log "err" "Missing plugin '${PLUGIN}' initialization file init.sql." "all" "pretty"
        exit 1
    fi
fi

# Main case
case "$1" in
    start)
        sqlite_start "$print_output" "$2"
        ;;
    init)
        sqlite_start "skip" "$2"
        ;;
    stop)
        sqlite_stop "$print_output"
        ;;
    reset)
        sqlite_reset "$print_output" "$2"
        ;;
    status)
        sqlite_status "$print_output"
        ;;
    purge)
        sqlite_purge "$print_output"
        ;;
    help)
        sqlite_help
        ;;
    *)
        echo "${USAGE}"
        exit 1
esac

# Exit cannot be used because the script may be "sourced"
#exit $?
