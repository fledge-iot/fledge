#!/bin/sh

##--------------------------------------------------------------------
## Copyright (c) 2018 Dianomic Systems
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

# This script is called by Debian package "postint" script
# only if package has been update.

PKG_NAME="foglamp"

# $1 is previous version passed by 'postinst" script
if [ ! "$1" ]; then
	exit 0
fi

previous_version=$1
# Get current new installed package version
this_version=`dpkg -s ${PKG_NAME} | grep '^Version:' | awk '{print $2}'`
# Location of upgrade scripts
UPGRADE_SCRIPTS_DIR="/usr/local/foglamp/scripts/package/debian/upgrade"

# We use dpkg --compare-versions for all version checks
# Check first 'previous_version' is less than 'this_version':
# if same version we take no actions
discard_out=`dpkg --compare-versions ${previous_version} ne ${this_version}`
ret_code=$?
# Check whether we can call upgrade scripts
if [ "${ret_code}" -eq "0" ]; then 
	# List all *.sh files in upgrade dir, ascending order
	# 1.3.sh, 1.4.sh, 1.5.sh etc 
	STOP_UPGRADE=""
	for upgrade_file in `ls -1 ${UPGRADE_SCRIPTS_DIR}/*.sh | sort -V`
		do
			# Extract script version file from name
			update_file_ver=`basename -s '.sh' $upgrade_file)`
			# Check update_file_ver is less than previous_version
			discard_out=`dpkg --compare-versions ${update_file_ver} le ${previous_version}`
			file_check=$?
			# If update_file_ver is equal or greater than previous_version
			# we skip previous upgrade scripts
			if [ "${file_check}" -eq "1" ]; then
				#
				# We can call upgrade scripts from:
				# previous_version up to this_version
				#
				discard_out=`dpkg --compare-versions ${update_file_ver} gt ${this_version}`
				file_check=$?
				if [ "${file_check}" -eq "0" ]; then
					# Stop here: update_file_ver is greater than this package version
					STOP_UPGRADE="Y"
					break
				else
					# We can call the current update script
					if [ -x "${upgrade_file}" ] && [ -s "${upgrade_file}" ] && [ -O "${upgrade_file}" ]; then
						echo "Executing FogLAMP package upgrade from ${previous_version} to ${update_file_ver}, script ${upgrade_file} ..."
						# Call upgrade script
						${upgrade_file}
					fi
				fi
			fi
			if [ "${STOP_UPGRADE}" ]; then
				break
			fi
		done
fi
