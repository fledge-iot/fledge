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
# $3 (optional) is the engine management flag (true or false)
# if $3 is empty a call to get_engine_management will be done

set -e
#set -x

PLUGIN="postgres"
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
postgres_log() {
    write_log "Storage" "script.plugin.storage.postgres" "$1" "$2" "$3" "$4"
}


## PostgreSQL Start
pg_start() {

    # Check the status of the server
    result=`pg_status "silent"`
    case "$result" in
        "0")
            # PostgreSQL already running.
            if [[ "$1" == "noisy" ]]; then
                postgres_log "info" "PostgreSQL is already running." "all" "pretty"
            else
		if [[ "$1" != "skip" ]]; then
                    postgres_log "info" "PostgreSQL is already running." "logonly" "pretty"
		fi
            fi
            ;;

        "2")
            if [[ "$MANAGED" = false ]]; then
                if [[ "$1" == "noisy" ]]; then
                    postgres_log "info" "Unable to start PostgreSQL. The server is not managed by Fledge." "all" "pretty"
                else
                    postgres_log "info" "Unable to start PostgreSQL. The server is not managed by Fledge." "logonly" "pretty"
                fi
                exit 2
            fi

            # PostgreSQL not running - starting
            if [[ "$1" == "noisy" ]]; then
                postgres_log "info" "Starting PostgreSQL..." "all" "pretty"
            else
                postgres_log "info" "Starting PostgreSQL..." "logonly" "pretty"
            fi
            eval $PG_CTL_COMMAND start > /dev/null 2>&1

            check_again=`pg_status "silent"`
            if [[ "$check_again" -eq "0" ]]; then
                if [[ "$1" == "noisy" ]]; then
                    postgres_log "info" "PostgreSQL started." "all" "pretty"
                else
                    postgres_log "info" "PostgreSQL started." "logonly" "pretty"
                fi
            else
                postgres_log "err" "Unable to start PostgreSQL." "all"
                exit 1
            fi
            ;;

        *)
            postgres_log "err" "Unknown database return status." "all"
            exit 1
            ;;
    esac

    # Check if the fledge database has been created
    if [[ `$PG_SQL -l | grep -c '^ fledge'` -ne 1 ]]; then
        # Create the Fledge database
        pg_reset "$1" "immediate" 
    fi

    # Fledge DB schema update: Fledge version is $2, $1 is log verbosity
    pg_schema_update $2 $1
}


## PostgreSQL Stop
pg_stop() {

    # Since the script may be called with "source", this condition must be set
    # and the else must be maintained because exit can't be used
    if [[ "$MANAGED" = false ]]; then

        # UNMANAGED part

        if [[ "$1" == "noisy" ]]; then
            postgres_log "info" "Unable to stop PostgreSQL. The server is not managed by Fledge." "all" "pretty"
        else
            postgres_log "info" "Unable to stop PostgreSQL. The server is not managed by Fledge." "logonly" "pretty"
        fi

    else

        # MANAGED part

        # Check the status of the server
        result=`pg_status "silent"`
        case "$result" in
            "0")
                if [[ "$1" == "noisy" ]]; then
                    postgres_log "info" "Stopping PostgreSQL..." "all" "pretty"
                else
                    postgres_log "info" "Stopping PostgreSQL..." "logonly" "pretty"
                fi
                eval $PG_CTL_COMMAND stop > /dev/null 2>&1

                check_again=`pg_status "silent"`
                if [[ "$check_again" -eq "2" ]]; then
                    if [[ "$1" == "noisy" ]]; then
                        postgres_log "info" "PostgreSQL stopped." "all" "pretty"
                    else
                        postgres_log "info" "PostgreSQL stopped." "logonly" "pretty"
                    fi
                else
                    postgres_log "err" "Unable to stop PostgreSQL." "all"
                    exit 1
                fi
                ;;

            "2")
                if [[ "$1" == "noisy" ]]; then
                    postgres_log "info" "PostgreSQL is not running." "all" "pretty"
                else
                    postgres_log "info" "PostgreSQL is not running." "logonly" "pretty"
                fi
                ;;

            *)
                postgres_log "err" "Unknown database return status." "all"
                exit 1
                ;;
        esac

    fi  # MANAGED true/false

}


## PostgreSQL Reset
pg_reset() {

    if [[ `pg_status silent` -eq 2 ]]; then
       pg_start "$1" "$2"
    fi

    if [[ $2 != "immediate" ]]; then
        echo "This script will remove all data stored in the server."
        echo -n "Enter YES if you want to continue: "
        read continue_reset

        if [ "$continue_reset" != 'YES' ]; then
	    echo "The system will NOT be reset and current content remains"
            echo "Goodbye."
            # This is ok because it means that the script is called from command line
            exit 0
        fi
    fi

    if [[ "$1" == "noisy" ]]; then
        postgres_log "info" "Building the metadata for the Fledge Plugin 'postgres'" "all" "pretty"
    else
        postgres_log "info" "Building the metadata for the Fledge Plugin 'postgres'" "logonly" "pretty"
    fi

    output=$(eval $PG_SQL -d postgres -q -f $INIT_SQL 2>&1)
    outputUC=${output^^}

    if [[ "$outputUC" =~ "ERROR" || "$outputUC" =~ "WARNING" || "$outputUC" =~ "FATAL" ]]; then

        postgres_log "err" "${output}" "all"
        exit 1
    else
        if [[ "$1" == "noisy" ]]; then
            postgres_log "info" "Build complete." "all" "pretty"
        else
            postgres_log "info" "Build complete." "logonly" "pretty"
        fi
    fi

}


## PostgreSQL Status
#
# NOTE: You can call this script with $1 = silent to avoid non output errors
#
# Returns:
#   0 - Server running
#   1 - Error
#   2 - Server not running
pg_status() {

    # Check if the database server is managed by Fledge
    if [[ "$MANAGED" = true ]]; then

        # Check if the PostgreSQL directory in $FLEDGE_DATA exists and create it
        # This is necessary to avoid an error in the PG_CTL command,
        # when the log is set
        if ! [[ -d "$PG_DIR" ]]; then
            mkdir -p "$PG_DIR"
        fi

        # Check if the Data directory exists and create it
        if ! [[ -d "$PG_DATA" ]]; then
            mkdir -p "$PG_DATA"
        fi

        # Check if the cluster files exist and create them
        if ! [[ -d "$PG_DATA/base" ]]; then

            if [[ "$1" == "noisy" ]]; then
                postgres_log "info" "Initializing PostgreSQL." "all" "pretty"
            else
                postgres_log "info" "Initializing PostgreSQL." "logonly" "pretty"
            fi
            eval $PG_CTL_COMMAND init > /dev/null 2>&1

        fi

        # Check the status command
        cmd_to_exec="$PG_CTL_COMMAND status"
        case "$($cmd_to_exec)" in
            "pg_ctl: no server running")
                if [[ "$1" == "noisy" ]]; then
                    postgres_log "info" "PostgreSQL not running." "outonly" "pretty"
                else
                    echo "2"
                fi    
                ;;
            "pg_ctl: server is running"*)
                if [[ "$1" == "noisy" ]]; then
                    postgres_log "info" "PostgreSQL running." "outonly" "pretty"
                else
                    echo "0"
                fi
                ;;
            *)
                postgres_log "err" "Unrecognized PostgreSQL status." "all"
                exit 1
                ;;
        esac
    
    else

        # The unmanaged part
        if ! [[ -x "$(command -v pg_isready)" ]]; then
            postgres_log "info" "Status check cannot be found. Is PostgreSQL installed?" "outonly" "pretty"
            postgres_log "info" "If PostgreSQL is installed, check if the bin dir is in the PATH." "outonly" "pretty"
            exit 1
        fi

        ret_message=`pg_isready`
        case "${ret_message}" in
            *"no response")
                if [[ "$1" == "noisy" ]]; then
                    postgres_log "info" "PostgreSQL not running." "outonly" "pretty"
                else
                    echo "2"
                fi
                ;;
            *"accepting connections")
                if [[ "$1" == "noisy" ]]; then
                    postgres_log "info" "PostgreSQL running." "outonly" "pretty"
                else
                    echo "0"
                fi
                ;;
            *)
                postgres_log "err" "Unknow status return by the PostgreSQL database server." "all"
                exit 1
        esac

    fi

}

## PostgreSQL schema update entry point
#
pg_schema_update() {
    # Current starting Fledge version
    NEW_VERSION=$1
    # DB table
    VERSION_TABLE="fledge.version"
    # Check first if the version table exists
    CURR_VERR=`${PG_SQL} -d fledge -q -A -t -c "SELECT to_regclass('${VERSION_TABLE}')"`
    ret_code=$?
    if [ ! "${CURR_VERR}" ] || [ "${ret_code}" -ne 0 ]; then
        postgres_log "error" "Error checking Fledge DB schema version: "\
"the table '${VERSION_TABLE}' doesn't exist. Exiting" "all" "pretty"
        return 1
    fi

    # Fetch Fledge DB version
    CURR_VERR=`${PG_SQL} -d fledge -q -A -t -c "SELECT id FROM ${VERSION_TABLE}" | tr -d ' '`
    if [ ! "${CURR_VERR}" ]; then
        # No version found set DB version now
        CURR_VERR=`${PG_SQL} -d fledge -q -A -t -c "INSERT INTO ${VERSION_TABLE} (id) VALUES('${NEW_VERSION}')"`
        SET_VERSION_MSG="Fledge DB version not found in '${VERSION_TABLE}', setting version [${NEW_VERSION}]"
        if [[ "$2" == "noisy" ]]; then
            postgres_log "info" "${SET_VERSION_MSG}" "all" "pretty"
        else 
            postgres_log "info" "${SET_VERSION_MSG}" "logonly" "pretty"
        fi
    else
        # Only if DB version is not equal to starting Fledge version we try schema update
        if [ "${CURR_VERR}" != "${NEW_VERSION}" ]; then
            postgres_log "info" "Detected '${PLUGIN}' Fledge DB schema change from version [${CURR_VERR}]"\
" to [${NEW_VERSION}], applying Upgrade/Downgrade ..." "all" "pretty"
            # Call the schema update script
            $FLEDGE_ROOT/scripts/plugins/storage/postgres/schema_update.sh "${CURR_VERR}" "${NEW_VERSION}" "${PG_SQL}"
            update_code=$?
            return ${update_code}
        else
            # Just log up-to-date
	    if [[ "$2" != "skip" ]]; then
                postgres_log "info" "Fledge DB schema is up to date to version [${CURR_VERR}]" "logonly" "pretty"
            fi
            return 0
        fi
    fi
}

## PostgreSQL Help
pg_help() {
    echo "${USAGE}
PostgreSQL Storage Layer plugin init script. 
The script is used to control the PostgreSQL plugin as database for Fledge
Arguments:
 start   - Start the database server (when managed)
           If the server has not been initialized, it also initialize it
 stop    - Stop the database server (when managed)
 status  - Check the status of the database server
 reset   - Bring the database server to the original installation.
           This is a synonym of init.
           WARNING: all the data stored in the server will be lost!
 init    - Database check: if Fledge database does not exist
           it will be created.
 purge   - Purge all readings data and non-configuration data stored in the database.
           WARNING: all the data stored in the affected tables will be lost!
 help    - This text

 managed   - The database server is embedded in Fledge
 unmanaged - The database server is not embedded in Fledge"

}

## PostgreSQL purge all readings and non-configuration data
#
pg_purge() {
    echo "This script will remove all readings data and non-configuration stored in the server."
    echo -n "Enter YES if you want to continue: "
    read continue_purge

    if [ "$continue_purge" != 'YES' ]; then
	echo "The system will NOT be purged of data and current content remains"
        echo "Goodbye."
        # This is ok because it means that the script is called from command line
        exit 0
    fi

    if [[ "$1" == "noisy" ]]; then
        postgres_log "info" "Purging data for the Fledge Plugin '${PLUGIN}' ..." "all" "pretty"
    else
        postgres_log "info" "Purging data for the Fledge Plugin '${PLUGIN}' ..." "logonly" "pretty"
    fi

   SQL_COMMAND=`${PG_SQL} -d fledge -b -q <<EOF
UPDATE fledge.statistics SET value = 0, previous_value = 0, ts = now();
TRUNCATE TABLE fledge.asset_tracker;
TRUNCATE TABLE fledge.tasks;
TRUNCATE TABLE fledge.statistics_history;
TRUNCATE TABLE fledge.log;
TRUNCATE TABLE fledge.readings;
UPDATE fledge.streams SET last_object = 0, ts = now();
TRUNCATE TABLE fledge.plugin_data;
TRUNCATE TABLE fledge.omf_created_objects;
TRUNCATE TABLE fledge.user_logins;
DO \\$alter_seq\\$
DECLARE i TEXT;
BEGIN
 FOR i IN (SELECT UNNEST(REGEXP_MATCHES(column_default, 'nextval\(''(.*)''::regclass\)')) AS seq_name
           FROM information_schema.columns
           WHERE column_default LIKE 'nextval%'
           AND table_schema = 'fledge'
           AND table_name IN ('asset_tracker', 'log'))
  LOOP
      EXECUTE 'ALTER SEQUENCE' || ' ' || i || ' '||' RESTART 1;';
  END LOOP;
END\\$alter_seq\\$;
EOF`

    RET_CODE=$?
    if [ "${RET_CODE}" -ne 0 ]; then
        postgres_log "err" "Failure in purge command. Exiting" "all" "pretty"
        return 1
    fi

    # Log success
    if [[ "$1" == "noisy" ]]; then
        postgres_log "info" "Purge complete for Fledge Plugin '${PLUGIN}" "all" "pretty"
    else
        postgres_log "info" "Purge complete for Fledge Plugin '${PLUGIN}" "logonly" "pretty"
    fi
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
    postgres_log "err" "Fledge cannot be executed: ${FLEDGE_DATA} is not a valid directory." "all" "pretty"
    exit 1
fi

# Extract plugin engine management status id $3 paramter is not set
if [ ! "${3}" ]; then
	engine_management=`get_engine_management $PLUGIN`
else
	engine_management=$3
fi

# Settings if the database is managed by Fledge
case "$engine_management" in
    "true")

        MANAGED=true

        # Set PGHOST if it does not exist
        if [ -z ${PGHOST+x} ]; then
            PGHOST="/tmp"
            export PGHOST
        fi

        PG_DIR="${FLEDGE_DATA}/storage/postgres/pgsql"
        PG_DATA="${PG_DIR}/data"
        PG_LOG="${PG_DIR}/logger"

        # Check if pg_ctl is present in the expected path
        PG_CTL="$FLEDGE_ROOT/plugins/storage/postgres/pgsql/bin/pg_ctl"
        PG_CTL_COMMAND="$PG_CTL -w -D $PG_DATA -l $PG_LOG"
        if ! [[ -x "${PG_CTL}" ]]; then
            postgres_log "err" "PostgreSQL program pg_ctl not found: the database server cannot be managed." "all" "pretty"
            exit 1
        fi

        # Check if psql is present in the expected path
        PG_SQL="$FLEDGE_ROOT/plugins/storage/postgres/pgsql/bin/psql"
        if ! [[ -x "${PG_SQL}" ]]; then
            postgres_log "err" "PostgreSQL program psql not found: the database server cannot be managed." "all" "pretty"
            exit 1
        fi

        print_output="noisy"
        ;;
    
    "false")

        # This case includes UNMANAGED

        if ! [[ -x "$(command -v psql)" ]]; then
            postgres_log "info" "The psql command cannot be found. Is PostgreSQL installed?" "outonly" "pretty"
            postgres_log "info" "If PostgreSQL is installed, check if the bin dir is in the PATH." "outonly" "pretty"
            exit 1
        else
            PG_SQL="$(command -v psql)"
        fi

        # This is an explicit imput, which means that we do not want to send
        # messages when we start or stop the server
        print_output="silent"
        MANAGED=false
        ;;

    *)

        # Unexpected value from the configuration file
        postgres_log "err" "Fledge cannot start." "all" "pretty"
        postgres_log "err" "Missing plugin information from the storage microservice" "all" "pretty"
        exit 1
        ;;

esac

# Check if the init.sql file exists
# Attempt 1: deployment path
if [[ -e "$FLEDGE_ROOT/plugins/storage/postgres/init.sql" ]]; then
    INIT_SQL="$FLEDGE_ROOT/plugins/storage/postgres/init.sql"
else
    # Attempt 2: development path
    if [[ -e "$FLEDGE_ROOT/scripts/plugins/storage/postgres/init.sql" ]]; then
        INIT_SQL="$FLEDGE_ROOT/scripts/plugins/storage/postgres/init.sql"
    else
        postgres_log "err" "Missing initialization file init.sql." "all" "pretty"
        exit 1
    fi
fi

# Main case
case "$1" in
    start)
        pg_start "$print_output" "$2"
        ;;
    init)
        pg_start "skip" "$2"
        ;;
    stop)
        pg_stop "$print_output"
        ;;
    reset)
        pg_reset "$print_output" "$2"
        ;;
    status)
        pg_status "$print_output"
        ;;
    purge)
	pg_purge
        ;;
    help)
        pg_help
        ;;
    *)
        echo "${USAGE}"
        exit 1
esac

# Exit cannot be used because the script may be "sourced"
#exit $?
