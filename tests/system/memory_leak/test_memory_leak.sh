#!/bin/bash
#
# Tests for checking meomory leaks.

PACKAGE_VERSION=nightly
TEST_RUN_TIME=60
PI_IP="10.0.0.97"
PI_USER="Administrator"
PI_PASSWORD="FogLamp200"
FLEDGE_URL="http://localhost:8081/fledge"


while [[ "$1" != "" ]]; do
    case $1 in
        --package-version )
            shift
            PACKAGE_VERSION=$1
            ;;
        --test-run-time )
            shift
            TEST_RUN_TIME=$1
            ;;
    esac
    shift
done


cleanup(){
  # sudo rm -rf /usr/local/fledge
  rm -rf /tmp/*valgrind*.log /tmp/*valgrind*.xml
}

modify_scripts(){  
  sudo sed -i "/.\/fledge.services.south.*/s/^/valgrind -v --xml=yes --xml-file=\/tmp\/south_valgrind_%p.xml --log-file=\/tmp\/south_valgrind.log --child-silent-after-fork=no --leak-check=full --show-leak-kinds=all --track-origins=yes /" /usr/local/fledge/scripts/services/south_c
  sudo sed -i "/.\/fledge.services.north.*/s/^/valgrind -v --xml=yes --xml-file=\/tmp\/north_valgrind_%p.xml --log-file=\/tmp\/north_valgrind.log --child-silent-after-fork=no --leak-check=full --show-leak-kinds=all --track-origins=yes /" /usr/local/fledge/scripts/services/north_C
  sudo sed -i "/\${storageExec} \"\$@\"/s/^/valgrind -v --xml=yes --xml-file=\/tmp\/storage_valgrind_%p.xml --log-file=\/tmp\/storage_valgrind.log --child-silent-after-fork=no --leak-check=full --show-leak-kinds=all --track-origins=yes /" /usr/local/fledge/scripts/services/storage
}

setup_repo(){
  ../python/scripts/package/remove;
  ../python/scripts/package/setup ${PACKAGE_VERSION};
}

install_plugins(){
  sudo apt install -y fledge-south-sinusoid fledge-south-expression
}

reset_fledge(){
  ../python/scripts/package/reset;
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
}

setup_north_pi_egress () {
  # Add PI North as service
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
}

generate_valgrind_logs(){
  sleep ${TEST_RUN_TIME}
  sudo systemctl stop fledge
  rm -rf reports/$1; mkdir -p reports/$1
  cp -rf /tmp/*valgrind*.log /tmp/*valgrind*.xml reports/$1/.
}

cleanup
setup_repo
modify_scripts
install_plugins
reset_fledge
setup_south
setup_north_pi_egress
generate_valgrind_logs test1
