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

##
## write_log
## This script is used to execute a command and control the output


# Paramaters: $1 - The command to execute
#             $2 - write_log function
#             $3 - The message to show in case of error
#
try_catch() {

  set +e
  command_output=$( $1 2>&1 )
  command_rescode=$?

  if [[ $command_rescode -ne 0 ]]; then
    $2 "err" "$3" "all" "pretty"
    $2 "err" "Command Output: $command_output" "all" "pretty"
    exit $comand_rescode
  fi
  set -e

}


