#!/bin/bash

#
# Expected input parameters :
#
#   $1 = FogLAMP status to achieve {RUNNING|STOPPED}
#

function evaluate_foglamp_status {

    output=$(${FOGLAMP_EXE} status 2>&1)

    # To upper case
    output=${output^^}

    if [[ ${output} =~ 'FOGLAMP UPTIME' ]]; then

        status="RUNNING"

    elif [[ ${output} =~ 'FOGLAMP NOT RUNNING.' ]]; then

        status="STOPPED"
    else
        status="NOT_DEFINED"
    fi

    echo ${status}
}

# Waits until either the requested status of FogLAMP is reached or it reaches the timeout.
count=0
while [ true ]
do

    value=$(evaluate_foglamp_status)

    if [[ "${value}" == "$1" ]]; then

        echo FogLAMP status reached :${value}: - N. of retries :${count}:                                               >> $RESULT_DIR/$TEST_NAME.1.temp 2>&1
        echo FogLAMP "${value}"
        exit 0
    else
        if [[ $count -le ${RETRY_COUNT} ]]
        then
            echo FogLAMP status :$1: not reached, currently :${value}: - N. of retries :${count}:                         >> $RESULT_DIR/$TEST_NAME.1.temp 2>&1
            sleep 1
            count=$((count+1))
        else
            echo FogLAMP status reached :${value}: - N. of retries :${count}:                                           >> $RESULT_DIR/$TEST_NAME.1.temp 2>&1
            echo FogLAMP "${value}"
            exit 1
        fi
    fi
done

