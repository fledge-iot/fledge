----------------------------------------------------------------------
-- Copyright (c) 2017 DB Software, Inc.
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
----------------------------------------------------------------------

--
-- foglamp_init_data.sql
--
-- PostgreSQL script to insert the first set of data necessary to run FogLAMP
--

-- NOTE:
-- This script must be launched with:
-- PGPASSWORD=foglamp psql -U foglamp -h localhost -f foglamp_init_data.sql foglamp


----------------------------------------------------------------------
-- 
----------------------------------------------------------------------

-- Log Codes
DELETE FROM foglamp.log_codes;
INSERT INTO foglamp.log_codes ( code, description )
     VALUES ( 'PURGE', 'Data Purging Process' ),
            ( 'LOGGN', 'Logging Process' ),
            ( 'STRMN', 'Streaming Process' ),
            ( 'SYPRG', 'System Purge' );


-- Configuration parameters
DELETE FROM foglamp.configuration;

-- CLEAN: The cleaning process is on by default
--        age     : Age of the data to be retained
--        enabled : When true, purging is enabled and data can be removed
INSERT INTO foglamp.configuration ( key, value )
     VALUES ( 'PURGE', '{ "age" : 259200, "enabled" : true }' );

-- LOGPR: Log Partitioning
--        unit: unit used for partitioning. Valid values are minute, half-hour, hour, 6-hour, half-day, day, week, fortnight, month. Default is day
INSERT INTO foglamp.configuration ( key, value )
     VALUES ( 'LOGPR', '{ "unit" : "day" }' );

-- STRMN: Streaming
--        status      : the process is on or off, it is on by default
--        time window : the time window when the process is active, always active by default (it means every second)
INSERT INTO foglamp.configuration ( key, value )
     VALUES ( 'STRMN', '{ "status" : "day", "window" : [ "always" ] }' );

-- SYPRG: System Purge
--        retention : data retention in seconds. Default is 3 days (259200 seconds)
--        last purge: ts of the last purge call
INSERT INTO foglamp.configuration ( key, value )
     VALUES ( 'SYPRG', to_jsonb( '{ "retention" : 259200, "last purge" : "' || now() || '" }' ) );


-- DELETE data for roles, resources and permissions
DELETE FROM foglamp.role_resource_permission;
DELETE FROM foglamp.roles;
DELETE FROM foglamp.resources;


-- Roles
INSERT INTO foglamp.roles ( id, name, description )
     VALUES ( 1, 'Power User', 'A user with special privileges' );


-- Resources
INSERT INTO foglamp.resources ( id, code, description )
     VALUES ( 1, 'PURGE_MGR', 'Can Start / Stop the purging process' );
INSERT INTO foglamp.resources ( id, code, description )
     VALUES ( 2, 'PURGE_RULE', 'Can view or set purging rules' );


-- Roles/Resources Permissions
INSERT INTO foglamp.role_resource_permission ( role_id, resource_id, access )
     VALUES ( 1, 1, '{ "access": "set" }' );
INSERT INTO foglamp.role_resource_permission ( role_id, resource_id, access )
     VALUES ( 1, 2, '{ "access": ["create","read","write","delete"] }' );



