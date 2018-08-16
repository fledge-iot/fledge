#!/bin/bash

# Declares used variables
declare SUITE_BASEDIR
declare FOGLAMP_ROOT
declare TMP_DIR
declare FOGLAMP_SERVER
declare FOGLAMP_PORT

declare TEST_BASEDIR
declare TEST_NAME
declare RESULT_DIR

declare PLUGIN_COAP_NAME
declare PLUGIN_COAP_REPO

# Reads configuration setting
source ${SUITE_BASEDIR}/suite.cfg

# Definitions
COAPFile=${FOGLAMP_ROOT}/python/foglamp/plugins/south/coap/coap.py
COAPRequirementsFile=${TMP_DIR}/${PLUGIN_COAP_NAME}/python/requirements-coap.txt

# Redirects std out/err for all the following commands
exec 8>&1                                      # Backups stdout
exec 1>>"${RESULT_DIR}/${TEST_NAME}_out.temp"
exec 2>>"${RESULT_DIR}/${TEST_NAME}_err.temp"

#
# Checks if the COAP plugin code is already available in the temporary directory
#
if [[ ! -f "${COAPRequirementsFile}" ]]
then
    echo "COAP plugin code does not exists in the temporary directory - |${COAPRequirementsFile}|, retrieving the code from the github repository."

    # Extracts the COAP plugin code
    cd ${TMP_DIR}
    rm -rf ${PLUGIN_COAP_NAME}
    git clone ${PLUGIN_COAP_REPO}
    cd ${PLUGIN_COAP_NAME}
else
    echo "COAP plugin code is already available - |${COAPRequirementsFile}|"
fi

#
# Checks if the COAP plugin code is already available in the FogLAMP directory tree
#
if [[ ! -f "${COAPFile}" ]]
then
    echo "COAP plugin code does not exists in the FogLAMP directory- |${COAPFile}|, copying the code."

    # Copies the COAP plugin code into the FogLAMP directory tree
    mkdir -p ${FOGLAMP_ROOT}/python/foglamp/plugins/south/coap
    cp -r  ${TMP_DIR}/${PLUGIN_COAP_NAME}/python/foglamp/plugins/south/coap/* ${FOGLAMP_ROOT}/python/foglamp/plugins/south/coap

else
    echo "COAP plugin code is already available - |${COAPFile}|"
fi

#
# Installs python libraries required by the plugin
#
pip3 install --user -Ir  "${COAPRequirementsFile}" --no-cache-dir
if [[ "$?" != "0" ]]; then
    exit 1
fi

#
# Enables the plugin
#
curl -k -s -S -X POST http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service -d '{ "name"   : "coap", "type"   : "south", "plugin" : "coap",  "enabled": true}' | jq -S "."

#
# Waits the availability of the plugin
#
$TEST_BASEDIR/bash/wait_plugin_available.bash "coap"

# Checks if the COAP plugin is enabled
export COAP_PLUGIN=`curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service| jq --raw-output '.services | .[] | select(.name=="coap") | .name'`

echo COAP_PLUGIN -${COAP_PLUGIN}-

if [[ "${COAP_PLUGIN}" == "" ]]
then
    echo "COAP plugin is not already activated, enabling - |${COAP_PLUGIN}|"

    export SCHEDULE_ID=` curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/schedule | jq --raw-output '.schedules | .[] | select(.processName=="coap") | .id'`

    echo SCHEDULE_ID -${SCHEDULE_ID}-

    curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/schedule/${SCHEDULE_ID}   | jq -S "."

    curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service | jq -S "."
else
    echo "COAP plugin already active |${COAP_PLUGIN}|"
fi

# Restore stdout
exec 1>&8

curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service| jq --raw-output '.services | .[] | select(.name=="coap") | {name,type,status}'
