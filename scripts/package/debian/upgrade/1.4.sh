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
