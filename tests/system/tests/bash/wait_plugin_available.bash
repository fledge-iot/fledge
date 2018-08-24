#!/bin/bash

#
# Expected input parameters :
#
#   $1 = FogLAMP plugin to evaluate
#

declare FOGLAMP_SERVER
declare FOGLAMP_PORT
declare RETRY_COUNT

# Waits until either the requested plug is loaded or the timeout is reached.
count=1
while [ true ]
do

    # Checks if the plugin is available
    value=$(curl -k -s -S -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/service| jq --raw-output '.services | .[] | select(.name=="'${1}'") | .name')

    if [[ "${value}" == "$1" ]]; then

        echo "FogLAMP plugin :${value}: available  - N. of retries :${count}:"
        exit 0
    else
        if [[ $count -le ${RETRY_COUNT} ]]
        then
            echo "FogLAMP plugin :${1}: not available, currently :${value}: - N. of retries :${count}:"
            sleep 1
            count=$((count+1))
        else
            echo "FogLAMP plugin :${1}: not available  - N. of retries :${count}:"
            exit 1
        fi
    fi
done
