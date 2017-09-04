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


-- Statistics
INSERT INTO foglamp.statistics ( key, description, value, previous_value )
     VALUES ( 'READINGS',   'The number of readings received by FogLAMP since startup', 0, 0 ),
            ( 'BUFFERED',   'The number of readings currently in the FogLAMP buffer', 0, 0 ),
            ( 'SENT',       'The number of readings sent to the historian', 0, 0 ),
            ( 'UNSENT',     'The number of readings filtered out in the send process', 0, 0 ),
            ( 'PURGED',     'The number of readings removed from the buffer by the purge process', 0, 0 ),
            ( 'UNSNPURGED', 'The number of readings that were purged from the buffer before being sent', 0, 0 ),
            ( 'DISCARDED',  'The number of readings discarded at the input side by FogLAMP, i.e. discarded before being  placed in the buffer. This may be due to some error in the readings themselves.', 0, 0 );

-- Schedules
-- Use this to create guids: https://www.uuidgenerator.net/version1 */
-- Weekly repeat for timed schedules: set schedule_interval to 168:00:00

INSERT INTO foglamp.scheduled_processes (name, script) VALUES ('device', '["python3", "-m", "foglamp.device"]');
INSERT INTO foglamp.scheduled_processes (name, script) VALUES ('purge', '["python3", "-m", "foglamp.data_purge"]');
INSERT INTO foglamp.scheduled_processes (name, script) VALUES ('stats collector', '["python3", "-m", "foglamp.update_statistics_history"]');
INSERT INTO foglamp.scheduled_processes (name, script) VALUES ('omf translator', '["python3", "-m", "foglamp.translators.omf_translator"]');
INSERT INTO foglamp.scheduled_processes (name, script) VALUES ('statistics to pi', '["python3", "-m", "foglamp.translators.statistics_to_pi"]');

-- Start the device server at start-up
INSERT INTO foglamp.schedules( id, schedule_name, process_name, schedule_type, schedule_interval, exclusive )
     VALUES ( 'ada12840-68d3-11e7-907b-a6006ad3dba0', 'device', 'device', 1, '0:0', true );

-- Run the purge process every 5 minutes
INSERT INTO foglamp.schedules( id, schedule_name, process_name, schedule_type, schedule_time, schedule_interval, exclusive )
     VALUES ( 'cea17db8-6ccc-11e7-907b-a6006ad3dba0', 'purge', 'purge', 3, NULL, '00:05:00', true );

-- Run the statistics collector every 15 seconds
INSERT INTO foglamp.schedules( id, schedule_name, process_name, schedule_type, schedule_time, schedule_interval, exclusive )
     VALUES ( '2176eb68-7303-11e7-8cf7-a6006ad3dba0', 'stats collector', 'stats collector', 3, NULL, '00:00:15', true );

-- Run FogLAMP statistics into PI  every 30 seconds
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type,
schedule_time, schedule_interval, exclusive)
values ('1d7c327e-7dae-11e7-bb31-be2e44b06b34', 'statistics to pi', 'statistics to pi', 3,
NULL, '00:00:30', true);


-- Run the omf transfalor every 15 seconds
INSERT INTO foglamp.schedules( id, schedule_name, process_name, schedule_type, schedule_time, schedule_interval, exclusive )
     VALUES ( '2b614d26-760f-11e7-b5a5-be2e44b06b34', 'omf translator', 'omf translator', 3, NULL, '00:00:15', true );

-- Temporary  omf translator configuration
INSERT INTO foglamp.destinations(id,description, ts)                       VALUES (1,'OMF', now());
INSERT INTO foglamp.streams(id,destination_id,description, last_object,ts) VALUES (1,1,'OMF translator', 0,now());  

-- Temporary FogLAMP statistics into PI configuration
INSERT INTO foglamp.streams (id,destination_id,description, last_object,ts ) VALUES (2,1,'FogLAMP statistics into PI', 0,now());
