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

# Redirects std out/err for all the following commands
exec 8>&1                                      # Backups stdout
exec 1>>"${RESULT_DIR}/${TEST_NAME}_out.temp"
exec 2>>"${RESULT_DIR}/${TEST_NAME}_err.temp"

#
# Checks if the COAP plugin code is already available in the FogLAMP directory tree
#
if [[ ! -f "${COAPFile}" ]]
then

    echo "COAP plugin code does not exists - |${COAPFile}|, retrieving the code from the github repository."

    # Extracts the COAP plugin code
    cd ${TMP_DIR}
    rm -rf ${PLUGIN_COAP_NAME}
    git clone ${PLUGIN_COAP_REPO}
    cd ${PLUGIN_COAP_NAME}

    # Copies the COAP plugin code into the FogLAMP directory tree
    mkdir -p ${FOGLAMP_ROOT}/python/foglamp/plugins/south/coap
    cp -r  ${TMP_DIR}/${PLUGIN_COAP_NAME}/python/foglamp/plugins/south/coap/* ${FOGLAMP_ROOT}/python/foglamp/plugins/south/coap

else
    echo "COAP plugin code is already available - |${COAPFile}|"
fi

#
# Enables the plugin if needed
#

# Checks if the COAP plugin code is already enabled
export COAP_PLUGIN=`curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service| jq --raw-output '.services | .[] | select(.name=="coap") | .name'`

echo COAP_PLUGIN -${COAP_PLUGIN}-

if [[ "${COAP_PLUGIN}" == "" ]]
then
    echo "COAP plugin is not already activated, enabling - |${COAP_PLUGIN}|"

    curl -k -s -S -X POST http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service -d '{ "name"   : "coap", "type"   : "south", "plugin" : "coap"}' | jq -S "."

    export SCHEDULE_ID=` curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/schedule | jq --raw-output '.schedules | .[] | select(.processName=="coap") | .id'`

    echo SCHEDULE_ID -${SCHEDULE_ID}-

    curl -k -s -S -X PUT http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/schedule/${SCHEDULE_ID} -d '{ "enabled" : true}'  | jq -S "."

    $TEST_BASEDIR/bash/sleep.bash 10

    curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service | jq -S "."
else
    echo "COAP plugin already active |${COAP_PLUGIN}|"
fi

# Restore stdout
exec 1>&8

curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service| jq --raw-output '.services | .[] | select(.name=="coap") | {name,type,status}'
