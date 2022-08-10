#!/bin/bash
#
# Tests for checking meomory leaks.

source config.sh

export FLEDGE_ROOT=$(pwd)/fledge

fledge_test_branch=$1     #here fledge_test_branch means branch of fledge repository that is needed to be scanned, default is devops


cleanup(){
  # sudo rm -rf /usr/local/fledge
  rm -rf /tmp/*valgrind*.log /tmp/*valgrind*.xml
  echo "Removig Repositories..."
  rm -rf fledge* reports && echo 'Done.'
}

#Setting up Fledge and installing its plugin
setup_repo(){
   ./scripts/setup fledge-south-sinusoid  ${fledge_test_branch} 
}


reset_fledge(){
  ./scripts/reset ${FLEDGE_ROOT} ;
}

setup_south(){ 
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
  echo 'Updateing Readings per second'

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
           "value": "'$3'"
        },
        "PIWebAPIUserId": {
           "value": "'$4'"
        },
        "PIWebAPIPassword": {
           "value": "'$5'"
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

generate_valgrind_logs(){
  sleep $6
  cd ${FLEDGE_ROOT}/scripts/
  echo 'stopping fledge'
  ./fledge stop 
  cd ../../
  echo 'Creating reports directory';
  mkdir -p reports/test1 ; ls -lrth
  echo 'copying reports '
  cp -rf /tmp/*valgrind*.log /tmp/*valgrind*.xml reports/$1/.  && echo 'copied'
  rm -rf fledge*
}

cleanup
setup_repo
reset_fledge
setup_south
setup_north_pi_egress
generate_valgrind_logs 
