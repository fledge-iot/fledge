#!/bin/bash

##--------------------------------------------------------------------
## Copyright (c) 2017 OSIsoft, LLC
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

##
## write_log
## This script is used to get information regarding the Storage Plugin
## from the FogLAMP configuration file $FOGLAMP_DATA/etc/foglamp.json

get_engine_management() {

    # Remove new lines and store in a variable
    json_foglamp=`tr -d '\n' < $FOGLAMP_DATA/etc/foglamp.json`

    # Remove tabs
    json_foglamp=`echo $json_foglamp | tr -d '\t'`

    middle_grep="\"plugin\" *: *\"${1}\" *, *\"managed\" *:.*"
    echo `echo $json_foglamp | grep -o "\"storage plugins\" *: *{.*" | grep -o "{.*" | grep -o "$middle_grep" | grep -o -e "true" -e "false"`

}

