#!/bin/bash

##--------------------------------------------------------------------
## Copyright (c) 2022 OSIsoft, LLC
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##--------------------------------------------------------------------

__author__="Massimiliano Pinto"
__version__="1.0"

# Get the storage database plugin from the Storage microservice cache file
get_readings_plugin() {
    # Capture the output to a variable
    if [ "${FLEDGE_ROOT}" ]; then
        res=$($FLEDGE_ROOT/scripts/services/storage --readingsPlugin 2>/dev/null)
    elif [ -x scripts/services/storage ]; then
        res=$(scripts/services/storage --readingsPlugin 2>/dev/null)
    else
        logger "Unable to find Fledge storage script."
        exit 1
    fi
    
    # Extract the first word from the result
    plugin=$(echo "$res" | cut -d' ' -f1)
    
    # Check if the first three words are "Use main plugin"
    if [[ "$res" =~ "Use main plugin" ]]; then
        if [ "${FLEDGE_ROOT}" ]; then
            # Run the --plugin command to get the actual plugin name
            plugin=$($FLEDGE_ROOT/scripts/services/storage --plugin 2>/dev/null | cut -d' ' -f1)
        elif [ -x scripts/services/storage ]; then
            # Run the local --plugin command
            plugin=$(scripts/services/storage --plugin 2>/dev/null | cut -d' ' -f1)
        else
            # Log an error and exit if the storage script is not found
            logger "Unable to fetch plugin information."
            exit 1
        fi
    fi
    
    # Return the plugin name
    echo "$plugin"
}
