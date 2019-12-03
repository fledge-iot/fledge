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

CURRENT_VERSION_FILE=$1
THIS_VERSION_FILE=$2

# Get installation path as dirname of CURRENT_VERSION_FILE var
INSTALLED_DIR=$(dirname ${CURRENT_VERSION_FILE})
# Get new version path as dirname of THIS_VERSION_FILE var
NEW_VERSION_DIR=$(dirname ${THIS_VERSION_FILE})

# Include common code
if [ ! "${FLEDGE_ROOT}" ]; then
    # Use source path
    FILE_TO_SOURCE="scripts/common/get_storage_plugin.sh"
else
    FILE_TO_SOURCE="${FLEDGE_ROOT}/scripts/common/get_storage_plugin.sh"
fi

source ${FILE_TO_SOURCE} 2> /dev/null
RET_CODE=$?
if [ "${RET_CODE}" -ne 0 ]; then
    echo "Error: Missing get_storage_plugin.sh"
    exit 1
fi

#
# Check required upgrade files
#
# param_1    the storage plugin name
# param_2    current installed Fledge DB schema
# param_3    new DB schema version
# param 4    the installed Fledge path
# return     0 on success, 1 on failure

check_upgrade() {
    PLUGIN_NAME=$1
    FLEDGE_DB_VERSION=$2
    NEW_VERSION=$3
    NEW_VERSION_PATH=$4
    INSTALLATION_PATH=$5
    UPDATE_SCRIPTS_DIR="${NEW_VERSION_PATH}/scripts/plugins/storage/${PLUGIN_NAME}/upgrade"
    # Start from next schema revision
    CHECK_VER=`expr ${FLEDGE_DB_VERSION} + 1 || return 1`
    while [ "${CHECK_VER}" -le ${NEW_VERSION} ]
    do
        UPGRADE_SCRIPT="${UPDATE_SCRIPTS_DIR}/${CHECK_VER}.sql"
        if [ ! -e "${UPGRADE_SCRIPT}" ]; then
            echo "Error in schema Upgrade: cannot find file ${UPGRADE_SCRIPT} "\
"required for DB Upgrade of the existing installation from schema "\
"[${FLEDGE_DB_VERSION}] to [${NEW_VERSION}] in [${INSTALLATION_PATH}]. Exiting"
            return 1
        fi
        CHECK_VER=`expr $CHECK_VER + 1`
    done
    echo "DB schema upgrade from ${FLEDGE_DB_VERSION} to ${NEW_VERSION} can be done. Ok"
    return 0
}

#
# Check required downgrade files
#
# param_1    the storage plugin name
# param_2    current installed Fledge DB schema
# param_3    new DB schema version
# param 4    the installed Fledge path
# return     0 on success, 1 on failure

check_downgrade() {
    PLUGIN_NAME=$1
    FLEDGE_DB_VERSION=$2
    NEW_VERSION=$3
    NEW_VERSION_PATH=$4
    INSTALLATION_PATH=$5
    DOWNGRADE_SCRIPTS_DIR="${NEW_VERSION_PATH}/scripts/plugins/storage/${PLUGIN_NAME}/downgrade"
    # Start from next schema revision
    CHECK_VER=`expr ${FLEDGE_DB_VERSION} - 1`
    while [ "${CHECK_VER}" -ge ${NEW_VERSION} ]
    do
        DOWNGRADE_SCRIPT="${DOWNGRADE_SCRIPTS_DIR}/${CHECK_VER}.sql"
        if [ ! -e "${DOWNGRADE_SCRIPT}" ]; then
            echo "Error in schema Downgrade: cannot find file ${DOWNGRADE_SCRIPT} "\
"required for DB Downgrade of the existing installation from schema "\
"[${FLEDGE_DB_VERSION}] to [${NEW_VERSION}] in [${INSTALLATION_PATH}]. Exiting"
            return 1
        fi
        CHECK_VER=`expr $CHECK_VER - 1`
    done
    echo "DB schema dowgrade from ${FLEDGE_DB_VERSION} to ${NEW_VERSION} can be done. Ok"
    return 0
}

# Set current installation path
INSTALLED_FLEDGE=${INSTALLED_DIR}

# Check whether installed VERSION exists and it's valid
CURRENT_FLEDGE_VERSION_FILE=${CURRENT_VERSION_FILE}

# Abort if INSTALLED_FLEDGE path doesn't exist
if [ ! -d "${INSTALLED_FLEDGE}" ]; then
    echo "Info: Fledge is not installed in [${INSTALLED_FLEDGE}]. Skipping DB schema check"
    exit 0
else
    DIR_EMPTY=`ls -1A ${INSTALLED_FLEDGE} | wc -l`
    if [ "${DIR_EMPTY}" -eq 0 ]; then
        echo "Info: ${INSTALLED_FLEDGE} is empty right now. Skipping DB schema check."
        exit 0
    fi
    if [ ! -f "${CURRENT_FLEDGE_VERSION_FILE}" ]; then
        # Set WARNING if VERSION file is not present in install path
        echo "Warning: Fledge version file [${CURRENT_FLEDGE_VERSION_FILE}] "\
             "not found in ${INSTALLED_FLEDGE}. It can be an old Fledge setup. Skipping DB schema check."
        exit 0
    fi 
    if [ ! -s "${CURRENT_FLEDGE_VERSION_FILE}" ]; then
        # Abort if VERSION file is empty
        echo "Error: Fledge version file [${CURRENT_FLEDGE_VERSION_FILE}] is empty. "\
             "DB schema check cannot be performed. Exiting."
        exit 1
    fi
fi

# Check whether VERSION file in the new installing path exists and it's valid
FLEDGE_VERSION_FILE=${THIS_VERSION_FILE}
if [ ! -f "${FLEDGE_VERSION_FILE}" ]; then
    # Abort on missing VERSION file
    echo "Error: Fledge version file [${FLEDGE_VERSION_FILE}] not found "\
         "in new installing path. Exiting"
    exit 1
else
    if [ ! -s "${FLEDGE_VERSION_FILE}" ]; then
        # Abort on empty VERSION file
        echo "Error: Fledge version file [${FLEDGE_VERSION_FILE}] in source tree is empty. "\
             "DB schema check cannot be performed. Exiting."
        exit 1
    fi
fi

PLUGIN_TO_USE=`get_storage_plugin`
RET_CODE=$?
if [ "${RET_CODE}" -ne 0 ]; then
    echo "Error: get_storage_plugin call failed."
    exit 1
fi

###
# Check for required files done
# Now getting Fledge version and DB schema version
#

###
# - 1 - Get Fledge version from installed VERSION file
# abort on missing variables
#
CURRENT_FLEDGE_VERSION=`cat ${CURRENT_FLEDGE_VERSION_FILE} | tr -d ' ' | grep -i "FLEDGE_VERSION=" | sed -e 's/\(.*\)=\(.*\)/\2/g'`
CURRENT_FLEDGE_SCHEMA=`cat ${CURRENT_FLEDGE_VERSION_FILE} | tr -d ' ' | grep -i "FLEDGE_SCHEMA=" | sed -e 's/\(.*\)=\(.*\)/\2/g'`
if [ ! "${CURRENT_FLEDGE_VERSION}" ]; then
    echo "Error FLEDGE_VERSION is not set, check [${CURRENT_FLEDGE_VERSION_FILE}] file. Exiting."
    exit  1
fi
if [ ! "${CURRENT_FLEDGE_SCHEMA}" ]; then
    echo "Error FLEDGE_SCHEMA is not set, check [${CURRENT_FLEDGE_VERSION_FILE}] file. Exiting."
    exit 1
fi

###
# - 2 - Get Fledge version from source tree VERSION file
# abort on missing variables
#
FLEDGE_VERSION=`cat ${FLEDGE_VERSION_FILE} | tr -d ' ' | grep -i "FLEDGE_VERSION=" | sed -e 's/\(.*\)=\(.*\)/\2/g'`
FLEDGE_SCHEMA=`cat ${FLEDGE_VERSION_FILE} | tr -d ' ' | grep -i "FLEDGE_SCHEMA=" | sed -e 's/\(.*\)=\(.*\)/\2/g'`
if [ ! "${FLEDGE_VERSION}" ]; then
    echo "Error FLEDGE_VERSION is not set, check [${FLEDGE_VERSION_FILE}] file. Exiting."
    exit  1
fi
if [ ! "${FLEDGE_SCHEMA}" ]; then
    echo "Error FLEDGE_SCHEMA is not set, check [${FLEDGE_VERSION_FILE}] file. Exiting."
    exit 1
fi

###
# Found DB schema versions are the same, nothing to do
#
if [ "${CURRENT_FLEDGE_SCHEMA}" == "${FLEDGE_SCHEMA}" ]; then
    echo "Info: DB schema is up-to-date in version ${FLEDGE_VERSION}"
    exit 0
fi

##
# Check whether we need to Upgrade or Downgrade the DB schema
#
CHECK_OPERATION=`printf '%s\n' "${FLEDGE_SCHEMA}" "${CURRENT_FLEDGE_SCHEMA}" | sort -V | head -n 1`
if [ "${CHECK_OPERATION}" == "${FLEDGE_SCHEMA}" ]; then
    SCHEMA_OPT="DOWNGRADE"
else
    SCHEMA_OPT="UPGRADE"
fi

###
# Call the schema operation with params:
# plugin_name
# current installed db schema
# new db schema
# new Fledge version path
#
if [ "${SCHEMA_OPT}" == "UPGRADE" ]; then
    check_upgrade ${PLUGIN_TO_USE} ${CURRENT_FLEDGE_SCHEMA} ${FLEDGE_SCHEMA} ${NEW_VERSION_DIR} ${INSTALLED_FLEDGE} || exit 1
else
    check_downgrade ${PLUGIN_TO_USE} ${CURRENT_FLEDGE_SCHEMA} ${FLEDGE_SCHEMA} ${NEW_VERSION_DIR} ${INSTALLED_FLEDGE} || exit 1
fi

exit 0
