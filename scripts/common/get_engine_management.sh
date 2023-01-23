#!/bin/bash

##--------------------------------------------------------------------
## Copyright (c) 2017 OSIsoft, LLC
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
#     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##--------------------------------------------------------------------

##
## This script is used to get information regarding the Storage Plugin


get_engine_management() {

  storage_info=( $($FLEDGE_ROOT/scripts/services/storage --plugin) )

  if [ "${storage_info[0]}" != "$1" ]; then
	  # Not the storage plugin, maybe beign used for readings
    storage_info=( $($FLEDGE_ROOT/scripts/services/storage --readingplugin) )
    if [ "${storage_info[0]}" != "$1" ]; then
	    echo ""
    else
    	echo "${storage_info[1]}"
    fi
  else
    echo "${storage_info[1]}"
  fi

}

