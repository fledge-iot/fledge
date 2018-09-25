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

# Get the storage database plugin from the Storage microservice cache file
get_storage_plugin() {
if [ "${FOGLAMP_ROOT}" ]; then
    $FOGLAMP_ROOT/scripts/services/storage --plugin | cut -d' ' -f1
elif [ -x scripts/services/storage ]; then
    scripts/services/storage --plugin | cut -d' ' -f1
else
    logger "Unable to find FogLAMP storage script."
    exit 1
fi
}
