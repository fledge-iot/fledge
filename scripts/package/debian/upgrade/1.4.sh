#!/bin/sh

remove_directory="/usr/local/foglamp/python/foglamp/plugins/north/omf/"

# Remove dir if exists
if [ -d "${remove_directory}" ]; then
    echo "FogLAMP package update: removing 'omf' Python north plugin ..."
    rm -rf "${remove_directory}"

    # Check
    if [ -d "${remove_directory}" ]; then
        echo "ERROR: FogLAMP plugin 'omf' not removed in '${remove_directory}'"
        exit 1
    else
        echo "FogLAMP plugin 'omf' removed in '${remove_directory}'"
    fi
fi

# The dummy C plugin has been renamed to random, remove the old plugin
dummy_directory="/usr/local/foglamp/plugins/south/dummy"

if [ -d $dummy_directory ]; then
	echo "FogLAMP package update: removing 'dummy' South plugin"
	rm -rf $dummy_directory
fi

# The omf C plugin has been renamed to PI_Server, remove the old plugin
omf_directory="/usr/local/foglamp/plugins/north/omf"
if [ -d $omf_directory ]; then
	echo "FogLAMP package update: removing 'omf' North plugin"
	rm -rf $omf_directory
fi
