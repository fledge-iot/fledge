#!/bin/bash

__author__="Mohit Singh Tomar"
__copyright__="Copyright (c) 2024 Dianomic Systems Inc."
__license__="Apache 2.0"
__version__="1.0.0"

#######################################################################################################################
# Script Name: test_memcheck.sh
# Description: Tests for checking memory leaks in Fledge.
# Usage: ./test_memcheck.sh FLEDGE_TEST_BRANCH COLLECT_FILES [OPTIONS]
#
# Parameters:
#   FLEDGE_TEST_BRANCH (str): Branch of Fledge Repository on which valgrind test will run.
#   COLLECT_FILES (str): Type of report file needs to be collected from valgrind test, default is LOGS otherwise XML.
#
# Options:
#   --use-filters: If passed, add filters to South Services.
#
# Example:
#   ./test_memcheck.sh develop LOGS
#   ./test_memcheck.sh develop LOGS --use-filters
# 
#########################################################################################################################

set -e
source config.sh

export FLEDGE_ROOT=$(pwd)/fledge

FLEDGE_TEST_BRANCH="$1"    # here fledge_test_branch means branch of fledge repository that is needed to be scanned, default is develop
COLLECT_FILES="${2:-LOGS}"
USE_FILTER="False"
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [ "$3" = "--use-filters" ]; then
   USE_FILTER="True"
fi

if [[  ${COLLECT_FILES} != @(LOGS|XML|) ]]
then
   echo "Invalid argument ${COLLECT_FILES}. Please provide valid arguments: XML or LOGS."
   exit 1
fi

cleanup(){
  # Removing temporary files, fledge and its plugin repository cloned by previous build of the Job 
  echo "Removing Cloned repository and log files"
  rm -rf fledge* reports && echo 'Done.'
}

# Setting up Fledge and installing its plugin
setup(){
   ./scripts/setup "fledge-south-sinusoid fledge-south-random fledge-filter-asset fledge-filter-rename"  "${FLEDGE_TEST_BRANCH}" "${COLLECT_FILES}"
}

reset_fledge(){
  ./scripts/reset ${FLEDGE_ROOT} ;
}

configure_purge(){
   # This function is for updating purge configuration and schedule of python based purge.
   echo -e "Updating Purge Configuration \n"
   row_count="$(printf "%.0f" "$(echo "${READINGSRATE} * 2 * ${PURGE_INTERVAL_SECONDS}"| bc)")"
   curl -X PUT "$FLEDGE_URL/category/PURGE_READ" -d "{\"size\":\"${row_count}\"}"
   echo 
   echo -e "Updated Purge Configuration \n"
   echo -e "Updating Purge Schedule \n"
   echo  > enable_purge.json
   cat enable_purge.json
   curl -X PUT "$FLEDGE_URL/schedule/cea17db8-6ccc-11e7-907b-a6006ad3dba0" -d \
   '{
      "name": "purge",
      "type": 3,
      "repeat": '"${PURGE_INTERVAL_SECONDS}"',
      "exclusive": true,
      "enabled": true
   }'
   echo -e "Updated Purge Schedule \n"
}

add_sinusoid(){ 
  echo -e INFO: "Add South Sinusoid"
  curl -sX POST "$FLEDGE_URL/service" -d \
  '{
     "name": "Sine",
     "type": "south",
     "plugin": "sinusoid",
     "enabled": "false",
     "config": {}
  }'  
  echo
  echo 'Updating Readings per second'

  sleep 60
  
  curl -sX PUT "$FLEDGE_URL/category/SineAdvanced" -d '{ "readingsPerSec": "'${READINGSRATE}'"}'
  echo
}

add_asset_filter_to_sine(){
   echo 'Adding Asset Filter to Sinusoid Service'
   curl -sX POST "$FLEDGE_URL/filter" -d \
   '{
      "name":"asset #1",
      "plugin":"asset",
      "filter_config":{
         "enable":"true",
         "config":{
            "rules":[
               {"asset_name":"sinusoid","action":"rename","new_asset_name":"sinner"}
            ]
         }
      }
   }'

   curl -sX PUT "$FLEDGE_URL/filter/Sine/pipeline?allow_duplicates=true&append_filter=true" -d \
   '{
      "pipeline":["asset #1"],
      "files":[]
   }'
}

add_random(){
  echo -e INFO: "Add South Random"
  curl -sX POST "$FLEDGE_URL/service" -d \
  '{
     "name": "Random",
     "type": "south",
     "plugin": "Random",
     "enabled": "false",
     "config": {}
  }'
  echo
  echo 'Updating Readings per second'

  sleep 60

  curl -sX PUT "$FLEDGE_URL/category/RandomAdvanced" -d '{ "readingsPerSec": "'${READINGSRATE}'"}'
  echo

}

add_rename_filter_to_random(){
   echo -e "\nAdding Rename Filter to Random Service"
   curl -sX POST "$FLEDGE_URL/filter" -d \
   '{
      "name":"rename #1",
      "plugin":"rename",
      "filter_config":{
         "find":"Random",
         "replaceWith":"Randomizer",
         "enable":"true"
      }
   }'

   curl -sX PUT "$FLEDGE_URL/filter/Random/pipeline?allow_duplicates=true&append_filter=true" -d \
   '{
      "pipeline":["rename #1"],
      "files":[]
   }'
}

enable_services(){
   echo -e "\nEnable Services"
   curl -sX PUT "$FLEDGE_URL/schedule/enable" -d '{"schedule_name":"Sine"}'
   sleep 20
   curl -sX PUT "$FLEDGE_URL/schedule/enable" -d '{"schedule_name": "Random"}'
   sleep 20
}

setup_north_pi_egress () {
  # Add PI North as service
  echo 'Setting up North'
  curl -sX POST "$FLEDGE_URL/service" -d \
  '{
     "name": "PI Server",
     "plugin": "OMF",
     "type": "north",
     "enabled": true,
     "config": {
        "PIServerEndpoint": {
           "value": "PI Web API"
        },
        "ServerHostname": {
           "value": "'${PI_IP}'"
        },
        "ServerPort": {
           "value": "443"
        },
        "PIWebAPIUserId": {
           "value": "'${PI_USER}'"
        },
        "PIWebAPIPassword": {
           "value": "'${PI_PASSWORD}'"
        },
        "NamingScheme": {
           "value": "Backward compatibility"
        },
        "PIWebAPIAuthenticationMethod": {
           "value": "basic"
        },
        "compression": {
           "value": "true"
        }
     }
  }'
  echo
  echo 'North setup done'
}

# This Function keep the fledge and its plugin running state for the "TEST_RUN_TIME" seconds then stop the fledge, So that data required for mem check be collected.
collect_data() {
  echo "Collecting Data and Generating reports"
  sleep "${TEST_RUN_TIME}"
  set +e

  echo "===================== COLLECTING SUPPORT BUNDLE / SYSLOG ============================"
  mkdir -p reports/ && ls -lrth
  BUNDLE=$(curl -sX POST "$FLEDGE_URL/support")
  # Check if the bundle is created using jq
  if jq -e 'has("bundle created")' <<< "$BUNDLE" > /dev/null; then
    echo "Support Bundle Created"
    # Use proper quoting for variable expansion
    cp -r "$FLEDGE_ROOT/data/support/"* reports/ && \
    echo "Support bundle has been saved to path: $SCRIPT_DIR/reports"
  else
    echo "Failed to Create support bundle"
    # Use proper quoting for variable expansion
    cp /var/log/syslog reports/ && \
    echo "Syslog Saved to path: $SCRIPT_DIR/reports"
  fi
  echo "===================== COLLECTED SUPPORT BUNDLE / SYSLOG ============================"
  # Use proper quoting for variable expansion
  "${FLEDGE_ROOT}/scripts/fledge" stop && echo $?
  set -e
}


generate_valgrind_logs(){
  echo 'Creating reports directory';
  mkdir -p reports/ ; ls -lrth
  echo 'copying reports'
  extension="xml"
  if [[ "${COLLECT_FILES}" == "LOGS" ]]; then extension="log"; fi
  cp -rf /tmp/*valgrind*.${extension} reports/. && echo 'copied'
}

cleanup
setup
reset_fledge
configure_purge
add_sinusoid
add_random
if [ "${USE_FILTER}" = "True" ]; then
   add_asset_filter_to_sine
   add_rename_filter_to_random
fi
enable_services
setup_north_pi_egress
collect_data
generate_valgrind_logs 

