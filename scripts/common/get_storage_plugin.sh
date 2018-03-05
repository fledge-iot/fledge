#!/bin/bash

##--------------------------------------------------------------------
## Copyright (c) 2018 OSIsoft, LLC
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

## Get the default storage database plugin from the foglamp config file
get_default_storage_plugin() {
    # Remove new lines and store in a variable
    json_foglamp=`tr -d '\n' < $1`

    # Remove tabs
    json_foglamp=`echo $json_foglamp | tr -d '\t'`

    echo `echo $json_foglamp | grep -o '"default storage plugin" *:.*' | grep -o ':.*' | grep -o '".*' | cut -d'"' -f2`
}

# Get the storage database plugin from the Storage microservice cache file
get_plugin_from_storage() {
    # Remove new lines and store in a variable
    json_storage=`tr -d '\n' < $1`

    # Remove tabs
    json_storage=`echo $json_storage | tr -d '\t'`

    echo `echo $json_storage | grep -o '"plugin" *: *{.*' | grep -o '{.*' | grep -o '"value" *:.*' | grep -o ':.*' | grep -o '".*' | cut -d'"' -f2`
}
