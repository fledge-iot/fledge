#!/bin/bash

##--------------------------------------------------------------------
## Copyright (c) 2018 OSIsoft, LLC
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

FLEDGE_DB_VERSION=$1
NEW_VERSION=$2
export SQLITE_SQL=$3
export sql_file=""

PLUGIN_NAME="sqlite"

echo "$@" | grep -q -- --verbose && VERBOSE="Y"

# Include logging
. $FLEDGE_ROOT/scripts/common/write_log.sh

# Logger wrapper
schema_update_log() {
    write_log "Storage" "scripts.plugins.storage.${PLUGIN_NAME}.schema_update" "$1" "$2" "$3" "$4"
}

# Parameters passed by the caller
if [ ! "$1" ]; then
   schema_update_log "err" "Error: missing required parameters for upgrade/downgrade. Fledge cannot start." "all" "pretty"
   exit 1
fi

# Same version check: do nothing
if [ "${FLEDGE_DB_VERSION}" == "${NEW_VERSION}" ]; then
    schema_update_log "info" "Fledge DB schema is up to date to version ${FLEDGE_DB_VERSION}" "logonly" "pretty"
    return  0
fi

# Perform DB Upgrade
db_upgrade()
{
    UPDATE_SCRIPTS_DIR="$FLEDGE_ROOT/scripts/plugins/storage/${PLUGIN_NAME}/upgrade"
    # Start from next schema revision
    CHECK_VER=`expr ${FLEDGE_DB_VERSION} + 1`
    while [ "${CHECK_VER}" -le ${NEW_VERSION} ]
    do
        UPGRADE_SCRIPT="${UPDATE_SCRIPTS_DIR}/${CHECK_VER}.sql"
        if [ ! -e "${UPGRADE_SCRIPT}" ]; then
            schema_update_log "err" "Error in schema Upgrade: cannot find file ${UPGRADE_SCRIPT} "\
"required for [${FLEDGE_DB_VERSION}] to [${NEW_VERSION}] upgrade. Exiting" "all" "pretty"
            return 1
        fi
        CHECK_VER=`expr $CHECK_VER + 1`
    done

    START_UPGRADE=""
    CHECK_VER=`expr ${FLEDGE_DB_VERSION} + 1`
    # sort in ascending order
    for sql_file in `ls -1 ${UPDATE_SCRIPTS_DIR}/*.sql | sort -V`
        do
            # Get start_ver from filename START_VER-to-END_VER.sql
            START_VER=`echo $(basename -s '.sql' $sql_file)`

            # Skip current file ?
            # Logic is: if sql_file name has START_VER != FLEDGE_DB_VERSION skip it
            # else mark the START_UPGRADE
            if [ ! "${START_UPGRADE}" ] && [ "${START_VER}" != "${CHECK_VER}" ]; then
                if [ "${VERBOSE}" ]; then
                    schema_update_log "info" "Skipping upgrade $(basename ${sql_file}) "\
"for Fledge upgrade from ${FLEDGE_DB_VERSION} to ${NEW_VERSION}" "logonly" "pretty"
                fi

                # Get next file in the list
                continue
            else
                START_UPGRADE="Y"
            fi

            # Perform Upgrade
            if [ "${START_UPGRADE}" ]; then

                # Evaluates if a shell script is available, in case it is executed instead of the .sql file
                file_name=$(basename ${sql_file})
                file_name_shell=${file_name%.*}.sh
                file_name_path="${UPDATE_SCRIPTS_DIR}/${file_name_shell}"

                if [ -f "${file_name_path}" ]; then

                    schema_update_log "debug" "upgrade shell calling [${file_name_path}]" "logonly" "pretty"
                    ${file_name_path}

                    RET_CODE=$?
                    if [ "${RET_CODE}" -ne 0 ]; then
                        schema_update_log "err" "Failure in upgrade, executing ${file_name_path}. Exiting" "all" "pretty"
                        return 1
                    fi
                else
                    schema_update_log "debug" "upgrade sql calling [${sql_file}]" "logonly" "pretty"

                    # Prepare command string for error reporting
                    SQL_COMMAND="${SQLITE_SQL} '${DEFAULT_SQLITE_DB_FILE}' \"ATTACH DATABASE "\
"'${DEFAULT_SQLITE_DB_FILE}' AS 'fledge'; .read '${sql_file}' .quit\""

                    if [ "${VERBOSE}" ]; then
                        schema_update_log "info" "Applying upgrade $(basename ${sql_file}) ..." "logonly" "pretty"
                        schema_update_log "info" "Calling [${SQL_COMMAND}]" "logonly" "pretty"
                    fi

                    # Call the DB script
                    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}'              AS 'fledge';
.read '${sql_file}'
.quit
EOF`
                    RET_CODE=$?

                    if [ "${RET_CODE}" -ne 0 ]; then
                        schema_update_log "err" "Failure in upgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
                        return 1
                    fi

                fi

                # Update the DB version
                UPDATE_VER=`basename -s .sql ${sql_file}`
                UPDATE_COMMAND="${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" \"ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge'; UPDATE fledge.version SET id = '${UPDATE_VER}';\" 2>&1"
                UPDATE_OUTPUT=`eval "${UPDATE_COMMAND}"`
                RET_CODE=$?
                if [ "${RET_CODE}" -ne 0 ]; then
                    schema_update_log "err" "Failure in upgrade command [${UPDATE_COMMAND}]: ${UPDATE_OUTPUT}. Exiting" "all" "pretty"
                    return 1
                fi

                # If "ver" in current filename is NEW_VERSION we are done
                if [ "${START_VER}" == "${NEW_VERSION}" ]; then
                    if [ "${VERBOSE}" ]; then
                        schema_update_log "info" "Found last upgrade file $(basename ${sql_file}) for "\
"${FLEDGE_DB_VERSION} to ${NEW_VERSION} version upgrade" "logonly" "pretty"
                    fi
                    # Report success
                    schema_update_log "info" "Fledge DB schema has been upgraded to version [${NEW_VERSION}]" "all" "pretty"
                    return 0
                fi
            fi
        done
        # Report error
        if [ "${START_UPGRADE}" ]; then
             schema_update_log "err" "Error: the Fledge DB schema has not been upgraded "\
"to version [${NEW_VERSION}], this sql file is [$${sql_file}]" "all" "pretty"
            return 0
        fi
}

# Perform DB Downgrade
db_downgrade()
{
    DOWNGRADE_SCRIPTS_DIR="$FLEDGE_ROOT/scripts/plugins/storage/${PLUGIN_NAME}/downgrade"
    # Start from next schema revision
    CHECK_VER=`expr ${FLEDGE_DB_VERSION} - 1`
    while [ "${CHECK_VER}" -ge ${NEW_VERSION} ]
    do
        DOWNGRADE_SCRIPT="${DOWNGRADE_SCRIPTS_DIR}/${CHECK_VER}.sql"
        if [ ! -e "${DOWNGRADE_SCRIPT}" ]; then
            schema_update_log "err" "Error in schema Downgrade: cannot find file ${DOWNGRADE_SCRIPT} "\
"required for [${FLEDGE_DB_VERSION}] to [${NEW_VERSION}] downgrade. Exiting" "all" "pretty"
            return 1
        fi
        CHECK_VER=`expr $CHECK_VER - 1`
    done

    START_DOWNGRADE=""
    CHECK_VER=`expr ${FLEDGE_DB_VERSION} - 1`
    # sort in descending order
    for sql_file in `ls -1 ${DOWNGRADE_SCRIPTS_DIR}/*.sql | sort -rV`
        do
            # Get start_ver from filename START_VER-to-END_VER.sql
            START_VER=`echo $(basename -s '.sql' $sql_file)`

            # Skip current file?
            # Logic is: sql_file name has START_VER != FLEDGE_DB_VERSION skip it
            # else mark START_DOWNGRADE
            if [ ! "${START_DOWNGRADE}" ] && [ "${START_VER}" != "${CHECK_VER}" ]; then
                if [ "${VERBOSE}" ]; then
                    schema_update_log "info" "Skipping downgrade $(basename ${sql_file}) "\
"for Fledge downgrade from ${FLEDGE_DB_VERSION} to ${NEW_VERSION}" "logonly" "pretty"
                fi

                # Get next file in the list
                continue
            else
                START_DOWNGRADE="Y"
            fi

            # Perform Downgrade
            if [ "${START_DOWNGRADE}" ]; then

                # Evaluates if a shell script is available, in case it is executed instead of the .sql file
                file_name=$(basename ${sql_file})
                file_name_shell=${file_name%.*}.sh
                file_name_path="${DOWNGRADE_SCRIPTS_DIR}/${file_name_shell}"

                if [ -f "${file_name_path}" ]; then

                    schema_update_log "debug" "downgrade shell calling [${file_name_path}]" "logonly" "pretty"

                    ${file_name_path}

                    RET_CODE=$?
                    if [ "${RET_CODE}" -ne 0 ]; then
                        schema_update_log "err" "Failure in downgrade, executing ${file_name_path}. Exiting" "all" "pretty"
                        return 1
                    fi
                else
                    schema_update_log "debug" "downgrade sql calling [${sql_file}]" "logonly" "pretty"

                    # Prepare command string for message reporting
                    SQL_COMMAND="${SQLITE_SQL} '${DEFAULT_SQLITE_DB_FILE}' \"ATTACH DATABASE "\
"'${DEFAULT_SQLITE_DB_FILE}' AS 'fledge'; .read '${sql_file}' .quit\""
                    if [ "${VERBOSE}" ]; then
                        schema_update_log "info" "Applying downgrade $(basename ${sql_file}) ..." "logonly" "pretty"
                        schema_update_log "info" "Calling [${SQL_COMMAND}]" "logonly" "pretty"
                    fi

                    # Call the DB script
                    COMMAND_OUTPUT=`${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" 2>&1 <<EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge';
.read '${sql_file}'
.quit
EOF`
                    RET_CODE=$?
                    if [ "${RET_CODE}" -ne 0 ]; then
                        schema_update_log "err" "Failure in downgrade command [${SQL_COMMAND}]: ${COMMAND_OUTPUT}. Exiting" "all" "pretty"
                        return 1
                    fi

                    # Update DB version
                    UPDATE_COMMAND="${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" \"ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge'; UPDATE fledge.version SET id = '${START_VER}';\" 2>&1"
                    UPDATE_OUTPUT=`eval "${UPDATE_COMMAND}"`
                    RET_CODE=$?
                    if [ "${RET_CODE}" -ne 0 ]; then
                        schema_update_log "err" "Failure in downgrade command [${UPDATE_COMMAND}]: ${UPDATE_OUTPUT}. Exiting" "all" "pretty"
                        return 1
                    fi

                fi

                # Update DB version
                UPDATE_COMMAND="${SQLITE_SQL} "${DEFAULT_SQLITE_DB_FILE}" \"ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge'; UPDATE fledge.version SET id = '${START_VER}';\" 2>&1"
                UPDATE_OUTPUT=`eval "${UPDATE_COMMAND}"`
                RET_CODE=$?
                if [ "${RET_CODE}" -ne 0 ]; then
                    schema_update_log "err" "Failure in downgrade command [${UPDATE_COMMAND}]: ${UPDATE_OUTPUT}. Exiting" "all" "pretty"
                    return 1
                fi

                # If "ver" in current filename is NEW_VERSION we are done
                if [ "${START_VER}" == "${NEW_VERSION}" ]; then
                    if [ "${VERBOSE}" ]; then
                        schema_update_log "info" "Found last downgrade file $(basename ${sql_file}) for "\
"${FLEDGE_DB_VERSION} to ${NEW_VERSION} version downgrade" "logonly" "pretty"
                    fi
                    # Report success
                    schema_update_log "info" "Fledge DB schema has been downgraded to version [${NEW_VERSION}]" "all" "pretty"
                    return 0
                fi
            fi
        done
        # Report error
        if [ "${START_DOWNGRADE}" ]; then
            schema_update_log "err" "Error: the Fledge DB schema has not been downgraded "\
"to version [${NEW_VERSION}], this sql file is [${sql_file}]" "all" "pretty"
            return 0
        fi
}

# Check whether we need to Upgrade or Downgrade
CHECK_OPERATION=`printf '%s\n' "${NEW_VERSION}" "${FLEDGE_DB_VERSION}" | sort -V | head -n 1`
if [ "${CHECK_OPERATION}" == "${NEW_VERSION}" ]; then
    SCHEMA_OPT="DOWNGRADE"
else
    SCHEMA_OPT="UPGRADE"
fi

# Call the schema operation
if [ "${SCHEMA_OPT}" == "UPGRADE" ]; then
    db_upgrade || exit 1
else
    db_downgrade || exit 1
fi

exit 0