#!/bin/bash
#
# Tests for checking meomory leaks.

source config.sh

export FLEDGE_ROOT=${cwd}/fledge
#echo $plugin_repos

fledge_branch=${1:-}

#if [[ -z "$1"  ]]
#then
#	fledge_branch=""
#else
#	fledge_branch=$1  #here fledge_branch means branch of fledge repository from clone is need to be done, default is devops
#fi


cleanup(){
  # sudo rm -rf /usr/local/fledge
  rm -rf /tmp/*valgrind*.log /tmp/*valgrind*.xml
  echo "Removig Repositories..."
  rm -rf fledge* reports && echo 'Done.'
}

#Setting up Fledge and installing its plugin
setup_repo(){
   ./scripts/setup ${PACKAGE_VERSION} fledge-south-sinusoid  ${fledge_branch} 
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

generate_valgrind_logs(){
  sleep ${TEST_RUN_TIME}
  cwd=`pwd`
  cd ${FLEDGE_ROOT}/scripts/
  echo 'stopping fledge'
  ./fledge stop 
  cd ../../
  echo $1
  echo 'Creating reports directory';
  mkdir -p reports/$1 ; ls -lrth
  echo 'copying reports '
  cp -rf /tmp/*valgrind*.log /tmp/*valgrind*.xml reports/$1/.  && echo 'copied'
  rm -rf fledge*
}

cleanup
setup_repo
reset_fledge
setup_south
setup_north_pi_egress
generate_valgrind_logs test1
