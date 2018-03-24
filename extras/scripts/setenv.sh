#!/bin/sh

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

#
# This script sets the user environment to facilitate the administration
# of FogLAMP
#
# You can execute this script from shell, using for example this command:
#
# source /usr/local/foglamp/extras/scripts/setenv.sh
#
# or you can add the same command at the bottom of your profile script
# {HOME}/.profile.
#

export FOGLAMP_ROOT="/usr/local/foglamp"
export FOGLAMP_DATA="${FOGLAMP_ROOT}/data"

export PATH="${FOGLAMP_ROOT}/bin:${PATH}"

