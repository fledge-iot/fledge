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

echo "FogLAMP data migration from Postgres to SQLite"
echo "Warning: this script must be launched from the new source or installed path before starting FogLAMP."
echo -n "Enter YES if you want to continue: "
read continue_dump

if [ "${continue_dump}" != 'YES' ]; then
	echo "Exiting."
	exit 0
fi
echo "Continue"


PG_SQL="$(command -v psql)"
PG_DUMP="$(command -v pg_dump)"
SQLITE_SQL="$(command -v sqlite3)"

# DB table
VERSION_TABLE="foglamp.version"

# Check first if the version table exists in Postgres FogLAMP database
CURR_VERR=`${PG_SQL} -d foglamp -q -A -t -c "SELECT to_regclass('${VERSION_TABLE}')"`
ret_code=$?

if [ ! "${CURR_VERR}" ] || [ "${ret_code}" -ne 0 ]; then
	echo "Error: FogLAMP table '${VERSION_TABLE}' doesn't exist. Exiting."
	exit 1
fi

# Fetch FogLAMP DB version
CURR_VERR=`${PG_SQL} -d foglamp -q -A -t -c "SELECT id FROM ${VERSION_TABLE}" | tr -d ' '`
if [ ! "${CURR_VERR}" ]; then
	echo "Error: FogLAMP version not set in '${VERSION_TABLE}'. Exiting"
	exit 1
fi

# Check FOGLAMP_ROOT
if [ -z ${FOGLAMP_ROOT+x} ]; then
	echo "Error: FOGLAMP_ROOT env var must be the new bein installed path"
	exit 2
fi

# New FogLAMP setup
FOGLAMP_VERSION_FILE="${FOGLAMP_ROOT}/VERSION"
FOGLAMP_VERSION=`cat ${FOGLAMP_VERSION_FILE} | tr -d ' ' | grep -i "FOGLAMP_VERSION=" | sed -e 's/\(.*\)=\(.*\)/\2/g'`
FOGLAMP_SCHEMA=`cat ${FOGLAMP_VERSION_FILE} | tr -d ' ' | grep -i "FOGLAMP_SCHEMA=" | sed -e 's/\(.*\)=\(.*\)/\2/g'`

echo "New FogLAMP version is ${FOGLAMP_VERSION}, DB schema version ${FOGLAMP_SCHEMA}"

if [ "${FOGLAMP_SCHEMA}" != "${CURR_VERR}" ]; then
	echo "Error: Current Postgres DB schema ${CURR_VERR} is different from new FogLAMP schema ${FOGLAMP_SCHEMA}. Exiting."
	exit 3
fi

echo "Migrating Postgres FogLAMP database schema version "${CURR_VERR}" into a SQLite3 database ..."

# Working dir for temp files
WORKDIR=`mktemp -d`
trap "rm -rf $WORKDIR" EXIT KILL

${PG_DUMP} foglamp -a --inserts | grep INSERT > ${WORKDIR}/dump.sql
sed -i -- "s/, true/, 't'/g" ${WORKDIR}/dump.sql
sed -i -- "s/, false/, 'f'/g" ${WORKDIR}/dump.sql

num_inserts=( $(wc -l ${WORKDIR}/dump.sql) )
start_time=`date`
echo "${start_time} Import: there are ${num_inserts[0]} rows to import"

rm -rf ./foglamp.db
start_time=`date`
${SQLITE_SQL} ./foglamp.db <<EOF
ATTACH DATABASE './foglamp.db' AS 'foglamp';
.read ${FOGLAMP_ROOT}/scripts/plugins/storage/sqlite/init.sql
-- FogLAMP schema created
BEGIN;
DELETE FROM foglamp.roles;
DELETE FROM foglamp.users;
DELETE FROM foglamp.user_pwd_history;
DELETE FROM foglamp.user_logins;
DELETE FROM foglamp.log_codes;
DELETE FROM foglamp.configuration;
DELETE FROM foglamp.destinations;
DELETE FROM foglamp.streams;
DELETE FROM foglamp.schedules;
DELETE FROM foglamp.scheduled_processes;
DELETE FROM foglamp.statistics;
-- Removed FogLAMP init data
.read '${WORKDIR}/dump.sql'
-- New data imported
COMMIT;
.quit
EOF
ret_code=$?
end_time=`date`
rm -rf ./dump.sql

if [ "${ret_code}" -eq 0 ]; then
	echo "${end_time} Import: Postgres to SQLite3 data migration successfully completed"
	echo "SQLite3 db created, move '${PWD}/foglamp.db' to '${FOGLAMP_ROOT}/data' folder or move to 'DEFAULT_SQLITE_DB_FILE' if set."
else
	echo "${end_time} *** ERROR: Postgres to SQLite3 data migration terminated with errors."
	echo "*** Import error: check '${PWD}/foglamp.db'"
	echo "If possible move '${PWD}/foglamp.db' to '${FOGLAMP_ROOT}/data' folder or move to 'DEFAULT_SQLITE_DB_FILE' if set."
fi

exit ${ret_code}
