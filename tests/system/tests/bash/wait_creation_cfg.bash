#!/bin/bash

# It waits until either the requested FogLAMP configuration is created or it reaches the timeout.
count=1
while [ true ]
do
    curl -s -X GET http://${FOGLAMP_SERVER}:${FOGLAMP_PORT}/foglamp/category/${1}  | jq '.value'  > /dev/null 2>&1
    result=$?

    if [[ "$result" == "0" ]]
    then
        echo "FogLAMP configuration :${1}: available  - N. of retries :${count}:"
        exit 0
    else
        if [[ $count -le ${RETRY_COUNT} ]]
        then
            echo "FogLAMP configuration :${1}: not available, result :${result}: - N. of retries :${count}:"
            sleep 1
            count=$((count+1))
        else
            echo "FogLAMP plugin :${1}: not available  - N. of retries :${count}:"
            exit 1
        fi
    fi
done
