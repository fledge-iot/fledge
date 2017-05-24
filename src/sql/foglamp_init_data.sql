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
     VALUES ( 'CLEAN', 'Cleaning Process' );        -- The Cleaning process


-- Configuration parameters
DELETE FROM foglamp.configuration;
INSERT INTO foglamp.configuration ( key, value )
     VALUES ( 'CLEAN', '{ "status" : "on" }' );


-- Roles
DELETE FROM foglamp.roles;
INSERT INTO foglamp.roles ( id, name, description )
     VALUES ( 1, 'Power User', 'A user with special privileges' );

-- Resources
DELETE FROM foglamp.resources;
INSERT INTO foglamp.resources ( id, code, description )
     VALUES ( 1, 'CLEAN_MGR', 'Can Start / Stop the cleaning process' );
INSERT INTO foglamp.resources ( id, code, description )
     VALUES ( 2, 'CLEAN_RULE', 'Can view or set cleaning rules' );

-- Roles/Resources Permissions
DELETE FROM foglamp.role_resource_permission;
INSERT INTO foglamp.role_resource_permission ( role_id, resource_id, access )
     VALUES ( 1, 1, '{ "access": "set" }' );
INSERT INTO foglamp.role_resource_permission ( role_id, resource_id, access )
     VALUES ( 1, 2, '{ "access": ["create","read","write","delete"] }' );


