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

__author__="Massimiliano Pinto"
__version__="1.0"

set -e

PLUGIN="sqlite"

# Set default DB file
if [ ! "${DEFAULT_SQLITE_DB_FILE}" ]; then
    export DEFAULT_SQLITE_DB_FILE="${FOGLAMP_DATA}/foglamp.db"
fi

USAGE="Usage: `basename ${0}` {start|stop|status|init|reset|help}"

# Check FOGLAMP_ROOT
if [ -z ${FOGLAMP_ROOT+x} ]; then
    # Set FOGLAMP_ROOT as the default directory
    FOGLAMP_ROOT="/usr/local/foglamp"
fi

# Check if the default directory exists
if [[ ! -d "${FOGLAMP_ROOT}" ]]; then

    # Here we cannot use the logger because we cannot find the write_log script.
    # But it is ok, because the script is called with source and if it is called
    # as standalone script the echo will be captured.
    echo "FogLAMP cannot be executed: ${FOGLAMP_ROOT} is not a valid directory."
    echo "Create the enviroment variable FOGLAMP_ROOT before using FogLAMP."
    echo "Specify the base directory for FogLAMP and set the variable with:"
    echo "export FOGLAMP_ROOT=<basedir>"
    exit 1

fi

##########
## INCLUDE SECTION
##########
. $FOGLAMP_ROOT/scripts/common/get_engine_management.sh
. $FOGLAMP_ROOT/scripts/common/write_log.sh


# Logger wrapper
sqlite_log() {
    write_log "Storage" "script.plugin.storage.sqlite" "$1" "$2" "$3" "$4"
}


# Check SQLite 3 command line is available
if ! [[ -x "$(command -v sqlite3)" ]]; then
    sqlite_log "info" "The sqlite3 command cannot be found. Is SQLite3 installed?" "outonly" "pretty"
    sqlite_log "info" "If SQLite3 is installed, check if the bin dir is in the PATH." "outonly" "pretty"
    exit 1
else
    SQLITE_SQL="$(command -v sqlite3)"
fi

## SQLite3 Start
sqlite_start() {

    # Check the status of the server
    result=`sqlite_status "silent"`
    case "$result" in
        "0")
            # SQLilte3 DB found already running.
            if [[ "$1" == "noisy" ]]; then
                sqlite_log "info" "SQLite3 database is ready." "all" "pretty"
            else
                sqlite_log "info" "SQLite3 database is ready." "logonly" "pretty"
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

    # Check if the foglamp database has been created
    FOUND_SCHEMAS=`${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} "ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'foglamp'; SELECT name FROM sqlite_master WHERE type='table'"`

    if [ ! "${FOUND_SCHEMAS}" ]; then
        # Create the FogLAMP database
         sqlite_reset "$1" "immediate" 
    fi

    # FogLAMP DB schema update: FogLAMP version is $2
    sqlite_schema_update $2
}


## SQLite  Stop
sqlite_stop() {

    # Since the script may be called with "source", this condition must be set
    # and the else must be maintained because exit can't be used

    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "FogLAMP database is SQLite3. No stop/start actions available" "all" "pretty"
    else
        sqlite_log "info" "FogLAMP database is SQLite3. No stop/start actions available" "logonly" "pretty"
    fi

    return 0
}


## SQLite3 Reset
sqlite_reset() {
    if [[ $2 != "immediate" ]]; then
        echo "This script will remove all data stored in the SQLite3 datafile '${DEFAULT_SQLITE_DB_FILE}'"
        echo -n "Enter YES if you want to continue: "
        read continue_reset

        if [ "$continue_reset" != 'YES' ]; then
            echo "Goodbye."
            # This is ok because it means that the script is called from command line
            exit 0
        fi
    fi

    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "Building the metadata for the FogLAMP Plugin '${PLUGIN}' ..." "all" "pretty"
    else
        sqlite_log "info" "Building the metadata for the FogLAMP Plugin '${PLUGIN}' ..." "logonly" "pretty"
    fi

    # 1- Drop all databases in DEFAULT_SQLITE_DB_FILE
    if [ -f "${DEFAULT_SQLITE_DB_FILE}" ]; then
        rm ${DEFAULT_SQLITE_DB_FILE} ||
        sqlite_log "err" "Cannot drop database '${DEFAULT_SQLITE_DB_FILE}' for the FogLAMP Plugin '${PLUGIN}'" "all" "pretty"
    fi
    # 2- Create new datafile an apply init file
    INIT_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'foglamp';
.read '${INIT_SQL}'
.quit
EOF`

    RET_CODE=$?
    # Exit on failure
    if [ "${RET_CODE}" -ne 0 ]; then
        sqlite_log "err" "Cannot initialize '${DEFAULT_SQLITE_DB_FILE}' for the FogLAMP Plugin '${PLUGIN}': ${INIT_OUTPUT}. Exiting" "all" "pretty"
        exit 2
    fi

    # Log success
    if [[ "$1" == "noisy" ]]; then
        sqlite_log "info" "Build complete for FogLAMP Plugin '${PLUGIN} in database '${DEFAULT_SQLITE_DB_FILE}'." "all" "pretty"
    else
        sqlite_log "info" "Build complete for FogLAMP Plugin '${PLUGIN} in database '${DEFAULT_SQLITE_DB_FILE}'." "logonly" "pretty"
    fi
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
            sqlite_log "info" "SQLite 3 database '${DEFAULT_SQLITE_DB_FILE}' ready." "logonly" "pretty"
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

## SQLite schema update entry point
#
sqlite_schema_update() {

    # Current starting FogLAMP version
    NEW_VERSION=$1
    # DB table
    VERSION_TABLE="version"
    # Check first if the version table exists
    VERSION_QUERY="SELECT name FROM sqlite_master WHERE type='table' and name = '${VERSION_TABLE}'"
    COMMAND_VERSION="${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} \"${VERSION_QUERY}\""
    CURR_VER=`eval ${COMMAND_VERSION}`
    ret_code=$?
    if [ ! "${CURR_VER}" ] || [ "${ret_code}" -ne 0 ]; then
        sqlite_log "error" "Error checking FogLAMP DB schema version: "\
"the table '${VERSION_TABLE}' doesn't exist. Exiting" "all" "pretty"
        return 1
    fi

    # Fetch FogLAMP DB version
    CURR_VER=`${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} "ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'foglamp'; SELECT id FROM foglamp.${VERSION_TABLE}" | tr -d ' '`
    if [ ! "${CURR_VER}" ]; then
        # No version found set DB version now
        INSERT_QUERY="ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'foglamp'; BEGIN; INSERT INTO foglamp.${VERSION_TABLE} (id) VALUES('${NEW_VERSION}'); COMMIT;"
        COMMAND_INSERT="${SQLITE_SQL} ${DEFAULT_SQLITE_DB_FILE} \"${INSERT_QUERY}\""
        CURR_VER=`eval "${COMMAND_INSERT}"`
        ret_code=$?

        SET_VERSION_MSG="FogLAMP DB version not found in foglamp.'${VERSION_TABLE}', setting version [${NEW_VERSION}]"
        if [[ "$1" == "noisy" ]]; then
            sqlite_log "info" "${SET_VERSION_MSG}" "all" "pretty"
        else 
            sqlite_log "info" "${SET_VERSION_MSG}" "logonly" "pretty"
        fi
    else
        # Only if DB version is not equal to starting FogLAMP version we try schema update
        if [ "${CURR_VER}" != "${NEW_VERSION}" ]; then
            sqlite_log "info" "Detected '${PLUGIN}' FogLAMP DB schema change from version [${CURR_VER}]"\
" to [${NEW_VERSION}], applying Upgrade/Downgrade ..." "all" "pretty"
            SCHEMA_UPDATE_SCRIPT="$FOGLAMP_ROOT/scripts/plugins/storage/${PLUGIN}/schema_update.sh"
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
            sqlite_log "info" "FogLAMP DB schema is up to date to version [${CURR_VER}]" "logonly" "pretty"
            return 0
        fi
    fi
}

## SQLite Help
sqlite_help() {

    echo "${USAGE}
SQLite3 Storage Layer plugin init script. 
The script is used to control the SQLite3 plugin as database for FogLAMP
Arguments:
 start   - Start the database server (when managed)
           If the server has not been initialized, it also initialize it
 stop    - Stop the database server (when managed)
 status  - Check the status of the database server
 reset   - Bring the database server to the original installation.
           This is a synonym of init.
           WARNING: all the data stored in the server will be lost!
 help    - This text

 managed   - The database server is embedded in FogLAMP
 unmanaged - The database server is not embedded in FogLAMP"

}


##################
### Main Logic ###
##################

# Set FOGLAMP_DATA if it does not exist
if [ -z ${FOGLAMP_DATA+x} ]; then
    FOGLAMP_DATA="${FOGLAMP_ROOT}/data"
fi

# Check if $FOGLAMP_DATA exists
if [[ ! -d ${FOGLAMP_DATA} ]]; then
    sqlite_log "err" "FogLAMP cannot be executed: ${FOGLAMP_DATA} is not a valid directory." "all" "pretty"
    exit 1
fi

# Check if the Configuration file exists
if [[ ! -e ${FOGLAMP_DATA}/etc/foglamp.json ]]; then
    sqlite_log "err" "Missing FogLAMP configuration file ${FOGLAMP_DATA}/etc/foglamp.json" "all" "pretty"
    exit 1
fi

# Extract plugin
engine_management=`get_engine_management $PLUGIN`
# Settings if the database is managed by FogLAMP
case "$engine_management" in
    "true")

        MANAGED=true

        # Check if sqlitei3 is present in the expected path
        # We don't need to manage SQLite3 db
        # This will be removed in next commits
        SQLITE_SQL="$FOGLAMP_ROOT/plugins/storage/sqlite/bin/psql"
        if ! [[ -x "${SQLITE_SQL}" ]]; then
            sqlite_log "err" "SQLite program not found: the database server cannot be managed." "all" "pretty"
            exit 1
        fi

        print_output="noisy"
        ;;
    
    "false")

        # This is an explicit input, which means that we do not want to send
        # messages when we start or stop the server
        print_output="silent"
        MANAGED=false
        ;;

    *)

        # Unexpected value from the configuration file
        sqlite_log "err" "FogLAMP cannot start." "all" "pretty"
        sqlite_log "err" "Missing plugin information in FogLAMP configuration file foglamp.json" "all" "pretty"
        exit 1
        ;;

esac

# Check if the init.sql file exists
# Attempt 1: deployment path
if [[ -e "$FOGLAMP_ROOT/plugins/storage/sqlite/init.sql" ]]; then
    INIT_SQL="$FOGLAMP_ROOT/plugins/storage/sqlite/init.sql"
else
    # Attempt 2: development path
    if [[ -e "$FOGLAMP_ROOT/scripts/plugins/storage/sqlite/init.sql" ]]; then
        INIT_SQL="$FOGLAMP_ROOT/scripts/plugins/storage/sqlite/init.sql"
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
    stop)
        sqlite_stop "$print_output"
        ;;
    reset)
        sqlite_reset "$print_output" "$2"
        ;;
    status)
        sqlite_status "$print_output"
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
