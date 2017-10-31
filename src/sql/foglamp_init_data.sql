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

-- PURGE: The cleaning process is on by default
--   age          : Age of data to be retained, all data that is older than this value will be removed by the purge process. This value is expressed in hours.
--   enabled      : A boolean switch that can be used to disable the purging of data. This is used if the process should be stopped from running.
--   retainUnsent : Retain data that has not been sent to tany historian yet.
-- INSERT INTO foglamp.configuration ( key, description, value )
--      VALUES ( 'PURGE', 'Purge data process', '{ "age" : 72, "enabled" : true, "retainUnsent" : false }' );

-- LOGPR: Log Partitioning
--        unit: unit used for partitioning. Valid values are minute, half-hour, hour, 6-hour, half-day, day, week, fortnight, month. Default is day
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'LOGPART', 'Log Partitioning', '{ "unit" : "day" }' );

-- SENSR: Sensors and devices
--        status      : the process is on or off, it is on by default
--        time window : the time window when the process is active, always active by default (it means every second)
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'SENSORS',
              'Sensors and Device Interface',
              '{ "category" : "CoAP", "configuration" : { "port" : { "description" : "Port to listen on", "default" : "5432", "value" : "5432", "type" : "integer" }, "url" : { "description" : "URL to accept data on", "default" : "sensor/reading-values", "value" : "sensor/reading-values", "type" : "string" }, "certificate" : { "description" : "X509 certificate used to identify ingress interface", "value" : "47676565", "type" : "x509 certificate" } } }' );

-- STRMN: Streaming
--        status      : the process is on or off, it is on by default
--        time window : the time window when the process is active, always active by default (it means every second)
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'STREAMING', 'Streaming', '{ "status" : "day", "window" : [ "always" ] }' );

-- SYPRG: System Purge
--        retention : data retention in seconds. Default is 3 days (259200 seconds)
--        last purge: ts of the last purge call
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'SYPURGE', 'System Purge', to_jsonb( '{ "retention" : 259200, "last purge" : "' || now() || '" }' ) );

-- COAP:  CoAP device server
--        plugin: python module to load dynamically
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'COAP', 'CoAP Plugin Configuration', ' { "plugin" : { "type" : "string", "value" : "coap", "default" : "coap", "description" : "Python module name of the plugin to load" } } ');

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
            ( 'SENT_1',     'The number of readings sent to the historian', 0, 0 ),
            ( 'SENT_2',     'The number of statistics data sent to the historian', 0, 0 ),
            ( 'UNSENT',     'The number of readings filtered out in the send process', 0, 0 ),
            ( 'PURGED',     'The number of readings removed from the buffer by the purge process', 0, 0 ),
            ( 'UNSNPURGED', 'The number of readings that were purged from the buffer before being sent', 0, 0 ),
            ( 'DISCARDED',  'The number of readings discarded at the input side by FogLAMP, i.e. discarded before being  placed in the buffer. This may be due to some error in the readings themselves.', 0, 0 );

-- Schedules
-- Use this to create guids: https://www.uuidgenerator.net/version1 */
-- Weekly repeat for timed schedules: set schedule_interval to 168:00:00

insert into foglamp.scheduled_processes (name, script) values ('COAP', '["python3", "-m", "foglamp.device"]');
insert into foglamp.scheduled_processes (name, script) values ('purge', '["python3", "-m", "foglamp.data_purge"]');
insert into foglamp.scheduled_processes (name, script) values ('stats collector', '["python3", "-m", "foglamp.statistics_history"]');
insert into foglamp.scheduled_processes (name, script) values ('sending process', '["python3", "-m", "foglamp.sending_process", "--stream_id", "1", "--debug_level", "1"]');
-- FogLAMP statistics into PI
insert into foglamp.scheduled_processes (name, script) values ('statistics to pi','["python3", "-m", "foglamp.sending_process", "--stream_id", "2", "--debug_level", "1"]');


-- Start the device server at start-up
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type,
schedule_interval, exclusive)
values ('ada12840-68d3-11e7-907b-a6006ad3dba0', 'device', 'COAP', 1,
'0:0', true);

-- Run the purge process every 5 minutes
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type,
schedule_time, schedule_interval, exclusive)
values ('cea17db8-6ccc-11e7-907b-a6006ad3dba0', 'purge', 'purge', 3,
NULL, '00:05:00', true);

-- Run the statistics collector every 15 seconds
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type,
schedule_time, schedule_interval, exclusive)
values ('2176eb68-7303-11e7-8cf7-a6006ad3dba0', 'stats collector', 'stats collector', 3,
NULL, '00:00:15', true);

-- Run the sending process every 15 seconds
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type,
schedule_time, schedule_interval, exclusive)
values ('2b614d26-760f-11e7-b5a5-be2e44b06b34', 'sending process', 'sending process', 3,
NULL, '00:00:15', true);

-- Run FogLAMP statistics into PI every 25 seconds
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type,
schedule_time, schedule_interval, exclusive)
values ('1d7c327e-7dae-11e7-bb31-be2e44b06b34', 'statistics to pi', 'statistics to pi', 3,
NULL, '00:00:25', true);

-- OMF translator configuration
INSERT INTO foglamp.destinations(id,description, ts)                       VALUES (1,'OMF', now());
INSERT INTO foglamp.streams(id,destination_id,description, last_object,ts) VALUES (1,1,'OMF translator', 0,now());  

-- FogLAMP statistics into PI configuration
INSERT INTO foglamp.streams (id,destination_id,description, last_object,ts ) VALUES (2,1,'FogLAMP statistics into PI', 0,now());
