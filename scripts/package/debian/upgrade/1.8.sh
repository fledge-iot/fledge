#!/usr/bin/env bash

pi_server_v2_directory="/usr/local/foglamp/plugins/north/PI_Server_V2"
if [[ -d ${pi_server_v2_directory} ]]; then
	echo "Removing 'PI_Server_V2' North plugin"
	rm -rf ${pi_server_v2_directory}
fi

ocs_v2_directory="/usr/local/foglamp/plugins/north/ocs_V2"
if [[ -d ${ocs_v2_directory} ]]; then
	echo "Removing 'ocs_V2' North plugin"
	rm -rf ${ocs_v2_directory}
fi
