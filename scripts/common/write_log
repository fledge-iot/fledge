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
## This script is used to write in the syslog and to echo output to stderr
## and stdout

set -e
#set -x


## The Loggging Handler
#
# Paramaters: $1 - Severity:
#                  - debug
#                  - info
#                  - notice
#                  - err
#                  - crit
#                  - alert
#                  - emerg
#             $2 - Message
#             $3 - Output:
#                  - logonly : send the message only to syslog
#                  - all     : send the message to syslog and stdout
#                  - outonly " send the message only to stdout
#             $4 - Format
#                - pretty : Do not show the date and priority
#
write_log() {

    MODULE="foglamp.storage.postgres"

    # Check log severity
    if ! [[ "$1" =~ ^(debug|info|notice|err|crit|alert|emerg)$ ]]; then
        write_log "err" "Internal error: unrecognized priority: $1" $3
        exit 1
    fi

    # Log to syslog
    if [[ "$3" =~ ^(logonly|all)$ ]]; then
        logger -p local0.$1 -t $MODULE $2
    fi

    # Log to Stdout
    if [[ "$3" =~ ^(outonly|all)$ ]]; then
        if [[ "$4" == "pretty" ]]; then
            echo "$2" >&2
        else
            echo "[$(date +'%Y-%m-%d %H:%M:%S')]: $@" >&2
        fi
    fi

}


