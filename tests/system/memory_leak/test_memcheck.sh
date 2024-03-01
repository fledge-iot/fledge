#!/bin/bash
#
# Tests for checking meomory leaks.

set -e
source config.sh

export FLEDGE_ROOT=$(pwd)/fledge

FLEDGE_TEST_BRANCH="$1"    # here fledge_test_branch means branch of fledge repository that is needed to be scanned, default is develop

COLLECT_FILES="${2:-LOGS}"

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

add_sinusoid(){ 
  echo -e INFO: "Add South Sinusoid"
  curl -sX POST "$FLEDGE_URL/service" -d \
  '{
     "name": "Sine",
     "type": "south",
     "plugin": "sinusoid",
     "enabled": "true",
     "config": {}
  }'  
  echo
  echo 'Updating Readings per second'

  sleep 60
  
  curl -sX PUT "$FLEDGE_URL/category/SineAdvanced" -d '{ "readingsPerSec": "'${READINGSRATE}'"}'
  echo
}

add_filter_asset_to_sine(){
   echo 'Setting Asset Filter'
   curl -sX POST "$FLEDGE_URL/filter" -d \
   '{
      "name":"assset1",
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
      "pipeline":["assset1"],
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
     "enabled": "true",
     "config": {}
  }'
  echo
  echo 'Updating Readings per second'

  sleep 60

  curl -sX PUT "$FLEDGE_URL/category/RandomAdvanced" -d '{ "readingsPerSec": "'${READINGSRATE}'"}'
  echo

}

add_filter_rename_to_random(){
   echo 'Setting Rename Filter'
   curl -sX POST "$FLEDGE_URL/filter" -d \
   '{
      "name":"re1",
      "plugin":"rename",
      "filter_config":{
         "find":"Random",
         "replaceWith":"Randomizer",
         "enable":"true"
      }
   }'

   curl -sX PUT "$FLEDGE_URL/filter/Random/pipeline?allow_duplicates=true&append_filter=true" -d \
   '{
      "pipeline":["re1"],
      "files":[]
   }'
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
collect_data(){
  sleep ${TEST_RUN_TIME}
  # TODO: remove set +e / set -e 
  # FOGL-6840  fledge stop returns exit code 1 
  set +e
  ${FLEDGE_ROOT}/scripts/fledge stop && echo $?
  set -e
}

generate_valgrind_logs(){
  echo 'Creating reports directory';
  mkdir -p reports/ ; ls -lrth
  echo 'copying reports '
  extension="xml"
  if [[ "${COLLECT_FILES}" == "LOGS" ]]; then extension="log"; fi
  cp -rf /tmp/*valgrind*.${extension} reports/. && echo 'copied'
}

cleanup
setup
reset_fledge
add_sinusoid
add_filter_asset_to_sine
add_random
add_filter_rename_to_random
setup_north_pi_egress
collect_data
generate_valgrind_logs 

