#!/bin/bash
#
# Tests for checking meomory leaks.

source config.sh

export FLEDGE_ROOT=$(pwd)/fledge

FLEDGE_TEST_BRANCH=$1     #here fledge_test_branch means branch of fledge repository that is needed to be scanned, default is devops

cleanup(){
  # Removing temporary files, fledge and its plugin repository cloned by previous build of the Job 
  echo "Removing Cloned repository and tmp files"
  rm -rf /tmp/*valgrind*.log /tmp/*valgrind*.xml
  rm -rf fledge* reports && echo 'Done.'
}

# Setting up Fledge and installing its plugin
setup(){
   ./scripts/setup fledge-south-sinusoid  ${FLEDGE_TEST_BRANCH} 
}

reset_fledge(){
  ./scripts/reset ${FLEDGE_ROOT} ;
}

add_sinusoid(){ 
  echo -e INFO: "Add South"
  curl -sX POST "$FLEDGE_URL/service" -d \
  '{
     "name": "Sine",
     "type": "south",
     "plugin": "sinusoid",
     "enabled": true,
     "config": {}
  }'  
  echo
  echo 'Updating Readings per second'

  sleep 60
  
  curl -sX PUT "$FLEDGE_URL/category/SineAdvanced" -d '{ "readingsPerSec": "100"}'
  echo
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
           "value": "'$2'"
        },
        "ServerPort": {
           "value": "443"
        },
        "PIWebAPIUserId": {
           "value": "'$3'"
        },
        "PIWebAPIPassword": {
           "value": "'$4'"
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
  cd ${FLEDGE_ROOT}/scripts/
  echo 'stopping fledge'
  ./fledge stop
  cd ../../
}

generate_valgrind_logs(){
  echo 'Creating reports directory';
  mkdir -p reports/test1 ; ls -lrth
  echo 'copying reports '
  cp -rf /tmp/*valgrind*.log /tmp/*valgrind*.xml reports/test1/.  && echo 'copied'
  rm -rf fledge*
}

cleanup
setup
reset_fledge
adding_sinusoid
setup_north_pi_egress
collect_data
generate_valgrind_logs 

