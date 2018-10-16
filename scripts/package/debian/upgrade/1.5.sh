#!/bin/sh

# The PI_Server C plugin has been renamed to PI_Server_V2, remove the old plugin
omf_directory="/usr/local/foglamp/plugins/north/PI_Server"
if [ -d $omf_directory ]; then
	echo "FogLAMP package update: removing 'PI_Server' North plugin"
	rm -rf $omf_directory
fi
