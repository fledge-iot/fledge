----------------------------------------------------------------------
-- Copyright (c) 2017 OSIsoft, LLC
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
-- init.sql
--
-- PostgreSQL script to create the FogLAMP persistent Layer
--

-- NOTE:
-- This script must be launched with:
-- psql -U postgres -d postgres -f init.sql


----------------------------------------------------------------------
-- DDL CONVENTIONS
--
-- Tables:
-- * Names are in plural, terms are separated by _
-- * Columns are, when possible, not null and have a default value.
--   For example, jsonb columns are '{}' by default.
--
-- Columns:
-- id      : It is commonly the PK of the table, a smallint, integer or bigint.
-- xxx_id  : It usually refers to a FK, where "xxx" is name of the table.
-- code    : Usually an AK, based on fixed lenght characters.
-- ts      : The timestamp with microsec precision and tz. It is updated at
--           every change.


-- This first part of the script must be executed by the postgres user

-- Disable the NOTICE notes
SET client_min_messages TO WARNING;

-- Dropping objects
DROP SCHEMA IF EXISTS foglamp CASCADE;
DROP DATABASE IF EXISTS foglamp;


-- Create the foglamp database
CREATE DATABASE foglamp WITH
    ENCODING = 'UTF8';

GRANT CONNECT ON DATABASE foglamp TO PUBLIC;


-- Connect to foglamp database
\connect foglamp

----------------------------------------------------------------------
-- SCHEMA CREATION
----------------------------------------------------------------------

-- Create the foglamp schema
CREATE SCHEMA foglamp;
GRANT USAGE ON SCHEMA foglamp TO PUBLIC;

------ SEQUENCES
CREATE SEQUENCE foglamp.asset_messages_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.asset_status_changes_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.asset_status_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.asset_types_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.assets_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.destinations_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.links_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.resources_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.roles_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.streams_id_seq
    INCREMENT 1
    START 5
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.user_pwd_history_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.user_logins_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.users_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.backups_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE foglamp.asset_tracker_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

----- TABLES & SEQUENCES

-- Log Codes Table
-- List of tasks that log info into foglamp.log.
CREATE TABLE foglamp.log_codes (
       code        character(5)          NOT NULL,   -- The process that logs actions
       description character varying(80) NOT NULL,
       CONSTRAINT log_codes_pkey PRIMARY KEY (code) );


-- Generic Log Table
-- General log table for FogLAMP.
CREATE SEQUENCE foglamp.log_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE foglamp.log (
       id    bigint                      NOT NULL DEFAULT nextval('foglamp.log_id_seq'::regclass),
       code  character(5)                NOT NULL,                                                -- The process that logged the action
       level smallint                    NOT NULL DEFAULT 0,                                      -- 0 Success - 1 Failure - 2 Warning - 4 Info
       log   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                            -- Generic log structure
       ts    timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT log_pkey PRIMARY KEY (id),
       CONSTRAINT log_fk1 FOREIGN KEY (code)
       REFERENCES foglamp.log_codes (code) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

ALTER SEQUENCE foglamp.log_id_seq OWNED BY foglamp.log.id;

-- Index: log_ix1 - For queries by code
CREATE INDEX log_ix1
    ON foglamp.log USING btree (code, ts, level);


-- Asset status
-- List of status an asset can have.
CREATE TABLE foglamp.asset_status (
       id          integer                NOT NULL DEFAULT nextval('foglamp.asset_status_id_seq'::regclass),
       descriprion character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
        CONSTRAINT asset_status_pkey PRIMARY KEY (id) );


-- Asset Types
-- Type of asset (for example south, sensor etc.)
CREATE TABLE foglamp.asset_types (
       id          integer                NOT NULL DEFAULT nextval('foglamp.asset_types_id_seq'::regclass),
       description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
        CONSTRAINT asset_types_pkey PRIMARY KEY (id) );


-- Assets table
-- This table is used to list the assets used in FogLAMP
-- Reading do not necessarily have an asset, but whenever possible this
-- table provides information regarding the data collected.
CREATE TABLE foglamp.assets (
       id           integer                     NOT NULL DEFAULT nextval('foglamp.assets_id_seq'::regclass),         -- The internal PK for assets
       code         character varying(50),                                                                           -- A unique code  (AK) used to match readings and assets. It can be anything.
       description  character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default", -- A brief description of the asset
       type_id      integer                     NOT NULL,                                                            -- FK for the type of asset
       address      inet                        NOT NULL DEFAULT '0.0.0.0'::inet,                                    -- An IPv4 or IPv6 address, if needed. Default means "any address"
       status_id    integer                     NOT NULL,                                                            -- Status of the asset, FK to the asset_status table
       properties   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                        -- A generic JSON structure. Some elements (for example "labels") may be used in the rule to send messages to the south devices or data to the cloud
       has_readings boolean                     NOT NULL DEFAULT false,                                              -- A boolean column, when TRUE, it means that the asset may have rows in the readings table
       ts           timestamp(6) with time zone NOT NULL DEFAULT now(),
         CONSTRAINT assets_pkey PRIMARY KEY (id),
         CONSTRAINT assets_fk1 FOREIGN KEY (status_id)
         REFERENCES foglamp.asset_status (id) MATCH SIMPLE
                 ON UPDATE NO ACTION
                 ON DELETE NO ACTION,
         CONSTRAINT assets_fk2 FOREIGN KEY (type_id)
         REFERENCES foglamp.asset_types (id) MATCH SIMPLE
                 ON UPDATE NO ACTION
                 ON DELETE NO ACTION );

-- Index: fki_assets_fk1
CREATE INDEX fki_assets_fk1
    ON foglamp.assets USING btree (status_id);

-- Index: fki_assets_fk2
CREATE INDEX fki_assets_fk2
    ON foglamp.assets USING btree (type_id);

-- Index: assets_ix1
CREATE UNIQUE INDEX assets_ix1
    ON foglamp.assets USING btree (code);


-- Asset Status Changes
-- When an asset changes its status, the previous status is added here.
-- tart_ts contains the value of ts of the row in the asset table.
CREATE TABLE foglamp.asset_status_changes (
       id         bigint                      NOT NULL DEFAULT nextval('foglamp.asset_status_changes_id_seq'::regclass),
       asset_id   integer                     NOT NULL,
       status_id  integer                     NOT NULL,
       log        jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       start_ts   timestamp(6) with time zone NOT NULL,
       ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_status_changes_pkey PRIMARY KEY (id),
       CONSTRAINT asset_status_changes_fk1 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT asset_status_changes_fk2 FOREIGN KEY (status_id)
       REFERENCES foglamp.asset_status (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_asset_status_changes_fk1
    ON foglamp.asset_status_changes USING btree (asset_id);

CREATE INDEX fki_asset_status_changes_fk2
    ON foglamp.asset_status_changes USING btree (status_id);


-- Links table
-- Links among assets in 1:M relationships.
CREATE TABLE foglamp.links (
       id         integer                     NOT NULL DEFAULT nextval('foglamp.links_id_seq'::regclass),
       asset_id   integer                     NOT NULL,
       properties jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT links_pkey PRIMARY KEY (id),
       CONSTRAINT links_fk1 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_links_fk1
    ON foglamp.links USING btree (asset_id);


-- Assets Linked table
-- In links, relationship between an asset and other assets.
CREATE TABLE foglamp.asset_links (
       link_id  integer                     NOT NULL,
       asset_id integer                     NOT NULL,
       ts       timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_links_pkey PRIMARY KEY (link_id, asset_id) );

CREATE INDEX fki_asset_links_fk1
    ON foglamp.asset_links USING btree (link_id);

CREATE INDEX fki_asset_link_fk2
    ON foglamp.asset_links USING btree (asset_id);


-- Asset Message Status table
-- Status of the messages to send South
CREATE SEQUENCE foglamp.asset_message_status_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE foglamp.asset_message_status (
       id          integer                NOT NULL DEFAULT nextval('foglamp.asset_message_status_id_seq'::regclass),
       description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
        CONSTRAINT asset_message_status_pkey PRIMARY KEY (id) );


-- Asset Messages table
-- Messages directed to the south devices.
CREATE TABLE foglamp.asset_messages (
       id        bigint                      NOT NULL DEFAULT nextval('foglamp.asset_messages_id_seq'::regclass),
       asset_id  integer                     NOT NULL,
       status_id integer                     NOT NULL,
       message   jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       ts        timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_messages_pkey PRIMARY KEY (id),
       CONSTRAINT asset_messages_fk1 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT asset_messages_fk2 FOREIGN KEY (status_id)
       REFERENCES foglamp.asset_message_status (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_asset_messages_fk1
    ON foglamp.asset_messages USING btree (asset_id);

CREATE INDEX fki_asset_messages_fk2
    ON foglamp.asset_messages USING btree (status_id);


-- Readings table
-- This tables contains the readings for assets.
-- An asset can be a south with multiple sensor, a single sensor,
-- a software or anything that generates data that is sent to FogLAMP
CREATE SEQUENCE foglamp.readings_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE foglamp.readings (
    id         bigint                      NOT NULL DEFAULT nextval('foglamp.readings_id_seq'::regclass),
    asset_code character varying(50)       NOT NULL,                      -- The provided asset code. Not necessarily located in the
                                                                          -- assets table.
    read_key   uuid                        UNIQUE,                        -- An optional unique key used to avoid double-loading.
    reading    jsonb                       NOT NULL DEFAULT '{}'::jsonb,  -- The json object received
    user_ts    timestamp(6) with time zone NOT NULL DEFAULT now(),        -- The user timestamp extracted by the received message
    ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
    CONSTRAINT readings_pkey PRIMARY KEY (id) );

CREATE INDEX fki_readings_fk1
    ON foglamp.readings USING btree (asset_code, user_ts desc);

CREATE INDEX readings_ix1
    ON foglamp.readings USING btree (read_key);


-- Destinations table
-- Multiple destinations are allowed, for example multiple PI servers.
CREATE TABLE foglamp.destinations (
       id            integer                     NOT NULL DEFAULT nextval('foglamp.destinations_id_seq'::regclass),   -- Sequence ID
       type          smallint                    NOT NULL DEFAULT 1,                                                  -- Enum : 1: OMF, 2: Elasticsearch
       description   character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default", -- A brief description of the destination entry
       properties    jsonb                       NOT NULL DEFAULT '{ "streaming" : "all" }'::jsonb,                   -- A generic set of properties
       active_window jsonb                       NOT NULL DEFAULT '[ "always" ]'::jsonb,                              -- The window of operations
       active        boolean                     NOT NULL DEFAULT true,                                               -- When false, all streams to this destination stop and are inactive
       ts            timestamp(6) with time zone NOT NULL DEFAULT now(),                                              -- Creation or last update
       CONSTRAINT destination_pkey PRIMARY KEY (id) );


-- Streams table
-- List of the streams to the Cloud.
CREATE TABLE foglamp.streams (
       id             integer                     NOT NULL DEFAULT nextval('foglamp.streams_id_seq'::regclass),         -- Sequence ID
       destination_id integer                     NOT NULL,                                                             -- FK to foglamp.destinations
       description    character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",  -- A brief description of the stream entry
       properties     jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- A generic set of properties
       object_stream  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Definition of what must be streamed
       object_block   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Definition of how the stream must be organised
       object_filter  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Any filter involved in selecting the data to stream
       active_window  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- The window of operations
       active         boolean                     NOT NULL DEFAULT true,                                                -- When false, all data to this stream stop and are inactive
       last_object    bigint                      NOT NULL DEFAULT 0,                                                   -- The ID of the last object streamed (asset or reading, depending on the object_stream)
       ts             timestamp(6) with time zone NOT NULL DEFAULT now(),                                               -- Creation or last update
       CONSTRAINT strerams_pkey PRIMARY KEY (id),
       CONSTRAINT streams_fk1 FOREIGN KEY (destination_id)
       REFERENCES foglamp.destinations (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_streams_fk1
    ON foglamp.streams USING btree (destination_id);


-- Configuration table
-- The configuration in JSON format.
-- The PK is also used in the REST API
-- Values is a jsonb column
-- ts is set by default with now().
CREATE TABLE foglamp.configuration (
       key         character varying(255)      NOT NULL COLLATE pg_catalog."default", -- Primary key
       description character varying(255)      NOT NULL,                              -- Description, in plain text
       value       jsonb                       NOT NULL DEFAULT '{}'::jsonb,          -- JSON object containing the configuration values
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                -- Timestamp, updated at every change
       CONSTRAINT configuration_pkey PRIMARY KEY (key) );


-- Configuration changes
-- This table has the same structure of foglamp.configuration, plus the timestamp that identifies the time it has changed
-- The table is used to keep track of the changes in the "value" column
CREATE TABLE foglamp.configuration_changes (
       key                 character varying(255)      NOT NULL COLLATE pg_catalog."default",
       configuration_ts    timestamp(6) with time zone NOT NULL,
       configuration_value jsonb                       NOT NULL,
       ts                  timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT configuration_changes_pkey PRIMARY KEY (key, configuration_ts) );


-- Statistics table
-- The table is used to keep track of the statistics for FogLAMP
CREATE TABLE foglamp.statistics (
       key         character varying(56)       NOT NULL COLLATE pg_catalog."default", -- Primary key, all uppercase
       description character varying(255)      NOT NULL,                              -- Description, in plan text
       value       bigint                      NOT NULL DEFAULT 0,                    -- Integer value, the statistics
       previous_value       bigint             NOT NULL DEFAULT 0,                    -- Integer value, the prev stat to be updated by metrics collector
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                -- Timestamp, updated at every change
       CONSTRAINT statistics_pkey PRIMARY KEY (key) );


-- Statistics history
-- Keeps history of the statistics in foglamp.statistics
-- The table is updated at startup
CREATE SEQUENCE foglamp.statistics_history_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE foglamp.statistics_history (
       id          bigint                      NOT NULL DEFAULT nextval('foglamp.statistics_history_id_seq'::regclass),
       key         character varying(56)       NOT NULL COLLATE pg_catalog."default",                         -- Coumpund primary key, all uppercase
       history_ts  timestamp(6) with time zone NOT NULL,                                                      -- Compound primary key, the highest value of statistics.ts when statistics are copied here.
       value       bigint                      NOT NULL DEFAULT 0,                                            -- Integer value, the statistics
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                                        -- Timestamp, updated at every change
       CONSTRAINT statistics_history_pkey PRIMARY KEY (key, history_ts) );

CREATE INDEX statistics_history_ix2
    ON foglamp.statistics_history(key);


-- Resources table
-- A resource and be anything that is available or can be done in FogLAMP. Examples:
-- - Access to assets
-- - Access to readings
-- - Access to streams
CREATE TABLE foglamp.resources (
    id          bigint                 NOT NULL DEFAULT nextval('foglamp.resources_id_seq'::regclass),
    code        character(10)          NOT NULL COLLATE pg_catalog."default",
    description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
    CONSTRAINT  resources_pkey PRIMARY KEY (id) );

CREATE UNIQUE INDEX resource_ix1
    ON foglamp.resources USING btree (code COLLATE pg_catalog."default");


-- Roles table
CREATE TABLE foglamp.roles (
    id          integer                NOT NULL DEFAULT nextval('foglamp.roles_id_seq'::regclass),
    name        character varying(25)  NOT NULL COLLATE pg_catalog."default",
    description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
    CONSTRAINT  roles_pkey PRIMARY KEY (id) );

CREATE UNIQUE INDEX roles_ix1
    ON foglamp.roles USING btree (name COLLATE pg_catalog."default");


-- Roles, Resources and Permssions table
-- For each role there are resources associated, with a given permission.
CREATE TABLE foglamp.role_resource_permission (
       role_id     integer NOT NULL,
       resource_id integer NOT NULL,
       access      jsonb   NOT NULL DEFAULT '{}'::jsonb,
       CONSTRAINT role_resource_permission_pkey PRIMARY KEY (role_id, resource_id),
       CONSTRAINT role_resource_permissions_fk1 FOREIGN KEY (role_id)
       REFERENCES foglamp.roles (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT role_resource_permissions_fk2 FOREIGN KEY (resource_id)
       REFERENCES foglamp.resources (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_role_resource_permissions_fk1
    ON foglamp.role_resource_permission USING btree (role_id);

CREATE INDEX fki_role_resource_permissions_fk2
    ON foglamp.role_resource_permission USING btree (resource_id);


-- Roles Assets Permissions table
-- Combination of roles, assets and access
CREATE TABLE foglamp.role_asset_permissions (
    role_id    integer NOT NULL,
    asset_id   integer NOT NULL,
    access     jsonb   NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT role_asset_permissions_pkey PRIMARY KEY (role_id, asset_id),
    CONSTRAINT role_asset_permissions_fk1 FOREIGN KEY (role_id)
    REFERENCES foglamp.roles (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
    CONSTRAINT role_asset_permissions_fk2 FOREIGN KEY (asset_id)
    REFERENCES foglamp.assets (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
    CONSTRAINT user_asset_permissions_fk1 FOREIGN KEY (role_id)
    REFERENCES foglamp.roles (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION );

CREATE INDEX fki_role_asset_permissions_fk1
    ON foglamp.role_asset_permissions USING btree (role_id);

CREATE INDEX fki_role_asset_permissions_fk2
    ON foglamp.role_asset_permissions USING btree (asset_id);


-- Users table
-- FogLAMP users table.
-- Authentication Method:
-- 0 - Disabled
-- 1 - PWD
-- 2 - Public Key
CREATE TABLE foglamp.users (
       id                integer                     NOT NULL DEFAULT nextval('foglamp.users_id_seq'::regclass),
       uname             character varying(80)       NOT NULL COLLATE pg_catalog."default",
       role_id           integer                     NOT NULL,
       description       character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
       pwd               character varying(255)      COLLATE pg_catalog."default",
       public_key        character varying(255)      COLLATE pg_catalog."default",
       enabled           boolean                     NOT NULL DEFAULT TRUE,
       pwd_last_changed  timestamp(6) with time zone NOT NULL DEFAULT now(),
       access_method smallint                        NOT NULL DEFAULT 0,
          CONSTRAINT users_pkey PRIMARY KEY (id),
          CONSTRAINT users_fk1 FOREIGN KEY (role_id)
          REFERENCES foglamp.roles (id) MATCH SIMPLE
                  ON UPDATE NO ACTION
                  ON DELETE NO ACTION );

CREATE INDEX fki_users_fk1
    ON foglamp.users USING btree (role_id);

CREATE UNIQUE INDEX users_ix1
    ON foglamp.users USING btree (uname COLLATE pg_catalog."default");

-- User Login table
-- List of logins executed by the users.
CREATE TABLE foglamp.user_logins (
       id               integer                     NOT NULL DEFAULT nextval('foglamp.user_logins_id_seq'::regclass),
       user_id          integer                     NOT NULL,
       ip               inet                        NOT NULL DEFAULT '0.0.0.0'::inet,
       ts               timestamp(6) with time zone NOT NULL DEFAULT now(),
       token            character varying(255)      NOT NULL,
       token_expiration timestamp(6) with time zone NOT NULL,
       CONSTRAINT user_logins_pkey PRIMARY KEY (id),
       CONSTRAINT user_logins_fk1 FOREIGN KEY (user_id)
       REFERENCES foglamp.users (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_user_logins_fk1
    ON foglamp.user_logins USING btree (user_id);


-- User Password History table
-- Maintains a history of passwords
CREATE TABLE foglamp.user_pwd_history (
       id               integer                     NOT NULL DEFAULT nextval('foglamp.user_pwd_history_id_seq'::regclass),
       user_id          integer                     NOT NULL,
       pwd              character varying(255)      COLLATE pg_catalog."default",
       CONSTRAINT user_pwd_history_pkey PRIMARY KEY (id),
       CONSTRAINT user_pwd_history_fk1 FOREIGN KEY (user_id)
       REFERENCES foglamp.users (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_user_pwd_history_fk1
    ON foglamp.user_pwd_history USING btree (user_id);


-- User Resource Permissions table
-- Association of users with resources and given permissions for each resource.
CREATE TABLE foglamp.user_resource_permissions (
       user_id     integer NOT NULL,
       resource_id integer NOT NULL,
       access      jsonb NOT NULL DEFAULT '{}'::jsonb,
        CONSTRAINT user_resource_permissions_pkey PRIMARY KEY (user_id, resource_id),
        CONSTRAINT user_resource_permissions_fk1 FOREIGN KEY (user_id)
        REFERENCES foglamp.users (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION,
        CONSTRAINT user_resource_permissions_fk2 FOREIGN KEY (resource_id)
        REFERENCES foglamp.resources (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION );

CREATE INDEX fki_user_resource_permissions_fk1
    ON foglamp.user_resource_permissions USING btree (user_id);

CREATE INDEX fki_user_resource_permissions_fk2
    ON foglamp.user_resource_permissions USING btree (resource_id);


-- User Asset Permissions table
-- Association of users with assets
CREATE TABLE foglamp.user_asset_permissions (
       user_id    integer NOT NULL,
       asset_id   integer NOT NULL,
       access     jsonb NOT NULL DEFAULT '{}'::jsonb,
       CONSTRAINT user_asset_permissions_pkey PRIMARY KEY (user_id, asset_id),
       CONSTRAINT user_asset_permissions_fk1 FOREIGN KEY (user_id)
       REFERENCES foglamp.users (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT user_asset_permissions_fk2 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_user_asset_permissions_fk1
    ON foglamp.user_asset_permissions USING btree (user_id);

CREATE INDEX fki_user_asset_permissions_fk2
    ON foglamp.user_asset_permissions USING btree (asset_id);


-- List of scheduled Processes
CREATE TABLE foglamp.scheduled_processes (
             name   character varying(255)  NOT NULL, -- Name of the process
             script jsonb,                            -- Full path of the process
  CONSTRAINT scheduled_processes_pkey PRIMARY KEY ( name ) );


-- List of schedules
CREATE TABLE foglamp.schedules (
             id                uuid                   NOT NULL, -- PK
             process_name      character varying(255) NOT NULL, -- FK process name
             schedule_name     character varying(255) NOT NULL, -- schedule name
             schedule_type     smallint               NOT NULL, -- 1 = startup,  2 = timed
                                                                -- 3 = interval, 4 = manual
             schedule_interval interval,                        -- Repeat interval
             schedule_time     time,                            -- Start time
             schedule_day      smallint,                        -- ISO day 1 = Monday, 7 = Sunday
             exclusive         boolean not null default true,   -- true = Only one task can run
                                                                -- at any given time
             enabled           boolean not null default false,  -- false = A given schedule is disabled by default
  CONSTRAINT schedules_pkey PRIMARY KEY  ( id ),
  CONSTRAINT schedules_fk1  FOREIGN KEY  ( process_name )
  REFERENCES foglamp.scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );


-- List of tasks
CREATE TABLE foglamp.tasks (
             id           uuid                        NOT NULL,               -- PK
             process_name character varying(255)      NOT NULL,               -- Name of the task
             state        smallint                    NOT NULL,               -- 1-Running, 2-Complete, 3-Cancelled, 4-Interrupted
             start_time   timestamp(6) with time zone NOT NULL DEFAULT now(), -- The date and time the task started
             end_time     timestamp(6) with time zone,                        -- The date and time the task ended
             reason       character varying(255),                             -- The reason why the task ended
             pid          integer                     NOT NULL,               -- Linux process id
             exit_code    integer,                                            -- Process exit status code (negative means exited via signal)
  CONSTRAINT tasks_pkey PRIMARY KEY ( id ),
  CONSTRAINT tasks_fk1 FOREIGN KEY  ( process_name )
  REFERENCES foglamp.scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );


-- Tracks types already created into PI Server
CREATE TABLE foglamp.omf_created_objects (
    configuration_key character varying(255)	NOT NULL,            -- FK to foglamp.configuration
    type_id           integer           	    NOT NULL,            -- Identifies the specific PI Server type
    asset_code        character varying(50)   NOT NULL,
    CONSTRAINT omf_created_objects_pkey PRIMARY KEY (configuration_key,type_id, asset_code),
    CONSTRAINT omf_created_objects_fk1 FOREIGN KEY (configuration_key)
    REFERENCES foglamp.configuration (key) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION );


-- Backups information
-- Stores information about executed backups
CREATE TABLE foglamp.backups (
    id         bigint                      NOT NULL DEFAULT nextval('foglamp.backups_id_seq'::regclass),
    file_name  character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default", -- Backup file name, expressed as absolute path
    ts         timestamp(6) with time zone NOT NULL DEFAULT now(),                                              -- Backup creation timestamp
    type       integer           	         NOT NULL,                                                            -- Backup type : 1-Full, 2-Incremental
    status     integer           	         NOT NULL,                                                            -- Backup status :
                                                                                                                --   1-Running
                                                                                                                --   2-Completed
                                                                                                                --   3-Cancelled
                                                                                                                --   4-Interrupted
                                                                                                                --   5-Failed
                                                                                                                --   6-Restored backup
    exit_code  integer,                                                                                         -- Process exit status code
    CONSTRAINT backups_pkey PRIMARY KEY (id) );

-- FogLAMP DB version
CREATE TABLE foglamp.version (id CHAR(10));

-- Create the configuration category_children table
CREATE TABLE foglamp.category_children (
       parent	character varying(255)	NOT NULL,
       child	character varying(255)	NOT NULL,
       CONSTRAINT config_children_pkey PRIMARY KEY (parent, child) );

-- Create the asset_tracker table
CREATE TABLE foglamp.asset_tracker (
       id            integer                NOT NULL DEFAULT nextval('foglamp.asset_tracker_id_seq'::regclass),
       asset         character(50)          NOT NULL,
       event         character varying(50)  NOT NULL,
       service       character varying(255) NOT NULL,
       foglamp       character varying(50)  NOT NULL,
       plugin        character varying(50)  NOT NULL,
       ts            timestamp(6) with time zone NOT NULL DEFAULT now() );

CREATE INDEX asset_tracker_ix1 ON foglamp.asset_tracker USING btree (asset);
CREATE INDEX asset_tracker_ix2 ON foglamp.asset_tracker USING btree (service);


-- Grants to foglamp schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA foglamp TO PUBLIC;



----------------------------------------------------------------------
-- Initialization phase - DML
----------------------------------------------------------------------

-- Roles
DELETE FROM foglamp.roles;
INSERT INTO foglamp.roles ( name, description )
     VALUES ('admin', 'All CRUD privileges'),
            ('user', 'All CRUD operations and self profile management');


-- Users
DELETE FROM foglamp.users;
INSERT INTO foglamp.users ( uname, pwd, role_id, description )
     VALUES ('admin', '3a86096e7a7c123ba0bc3dfb7a1d350541649f1ff1aff1f37e0dc1ee4175b112:3759bf3302f5481e8c9cc9472c6088ac', 1, 'admin user'),
            ('user', '3a86096e7a7c123ba0bc3dfb7a1d350541649f1ff1aff1f37e0dc1ee4175b112:3759bf3302f5481e8c9cc9472c6088ac', 2, 'normal user');

-- User password history
DELETE FROM foglamp.user_pwd_history;


-- User logins
DELETE FROM foglamp.user_logins;


-- Log Codes
DELETE FROM foglamp.log_codes;
INSERT INTO foglamp.log_codes ( code, description )
     VALUES ( 'PURGE', 'Data Purging Process' ),
            ( 'LOGGN', 'Logging Process' ),
            ( 'STRMN', 'Streaming Process' ),
            ( 'SYPRG', 'System Purge' ),
            ( 'START', 'System Startup' ),
            ( 'FSTOP', 'System Shutdown' ),
            ( 'CONCH', 'Configuration Change' ),
            ( 'CONAD', 'Configuration Addition' ),
            ( 'SCHCH', 'Schedule Change' ),
            ( 'SCHAD', 'Schedule Addition' ),
            ( 'SRVRG', 'Service Registered' ),
            ( 'SRVUN', 'Service Unregistered' ),
            ( 'SRVFL', 'Service Fail' ),
            ( 'NHCOM', 'North Process Complete' ),
            ( 'NHDWN', 'North Destination Unavailable' ),
            ( 'NHAVL', 'North Destination Available' ),
            ( 'UPEXC', 'Update Complete' ),
            ( 'BKEXC', 'Backup Complete' );


--
-- Configuration parameters
--
DELETE FROM foglamp.configuration;


-- North plugins

-- North_Readings_to_PI - OMF Translator for readings
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North_Readings_to_PI',
              'OMF North Plugin - C Code',
              ' { "plugin" : { "type" : "string", "value" : "omf", "default" : "omf", "description" : "Module that OMF North Plugin will load" } } '
            );

-- North_Readings_to_HTTP - for readings
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North_Readings_to_HTTP',
              'HTTP North Plugin - C Code',
              ' { "plugin" : { "type" : "string", "value" : "http-north", "default" : "http-north", "description" : "Module that HTTP North Plugin will load" } } '
            );

-- dht11 - South plugin for DHT11 - C
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'dht11',
              'DHT11 South C Plugin',
              ' { "plugin" : { "type" : "string", "value" : "dht11", "default" : "dht11", "description" : "Module that DHT11 South Plugin will load" } } '
            );

-- North_Statistics_to_PI - OMF Translator for statistics
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North_Statistics_to_PI',
              'OMF North Plugin - C Code',
              ' { "plugin" : { "type" : "string", "value" : "omf", "default" : "omf", "description" : "Module that OMF North Plugin will load" } } '
            );

-- North Readings to PI - OMF Translator for readings
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North Readings to PI',
              'OMF North Plugin',
              '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "readings", "value": "readings"}}'
            );

-- North Statistics to PI - OMF Translator for statistics
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North Statistics to PI',
              'OMF North Statistics Plugin',
              '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "statistics", "value": "statistics"}}'
            );

-- North Readings to OCS - OSIsoft Cloud Services plugin for readings
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North Readings to OCS',
              'OCS North Plugin',
              '{"plugin": {"description": "OCS North Plugin", "type": "string", "default": "ocs", "value": "ocs"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "readings", "value": "readings"}}'
            );

-- Statistics
INSERT INTO foglamp.statistics ( key, description, value, previous_value )
     VALUES ( 'READINGS',             'Readings received by FogLAMP', 0, 0 ),
            ( 'BUFFERED',             'Readings currently in the FogLAMP buffer', 0, 0 ),
            ( 'NORTH_READINGS_TO_PI', 'Readings sent to historian', 0, 0 ),
            ( 'NORTH_STATISTICS_TO_PI', 'Statistics sent to historian', 0, 0 ),
            ( 'NORTH_READINGS_TO_HTTP', 'Readings sent to HTTP', 0, 0 ),
            ( 'North Readings to PI', 'Readings sent to the historian', 0, 0 ),
            ( 'North Statistics to PI','Statistics data sent to the historian', 0, 0 ),
            ( 'North Readings to OCS','Readings sent to OCS', 0, 0 ),
            ( 'UNSENT',               'Readings filtered out in the send process', 0, 0 ),
            ( 'PURGED',               'Readings removed from the buffer by the purge process', 0, 0 ),
            ( 'UNSNPURGED',           'Readings that were purged from the buffer before being sent', 0, 0 ),
            ( 'DISCARDED',            'Readings discarded by the South Service before being  placed in the buffer. This may be due to an error in the readings themselves.', 0, 0 );

--
-- Scheduled processes
--
-- Use this to create guids: https://www.uuidgenerator.net/version1 */
-- Weekly repeat for timed schedules: set schedule_interval to 168:00:00

-- Core Tasks
--
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'purge',               '["tasks/purge"]'      );
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'stats collector',     '["tasks/statistics"]' );
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'FogLAMPUpdater',      '["tasks/update"]'     );
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'certificate checker', '["tasks/check_certs"]' );

-- Storage Tasks
--
INSERT INTO foglamp.scheduled_processes (name, script) VALUES ('backup',  '["tasks/backup"]'  );
INSERT INTO foglamp.scheduled_processes (name, script) VALUES ('restore', '["tasks/restore"]' );

-- North Tasks
--
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North Readings to PI',   '["tasks/north"]' );
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North Statistics to PI', '["tasks/north"]' );
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North Readings to OCS',  '["tasks/north"]' );

-- North Tasks - C code
--
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North_Readings_to_PI',   '["tasks/north_c"]' );
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North_Statistics_to_PI', '["tasks/north_c"]' );

-- North Tasks - C code
--
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North_Readings_to_HTTP',   '["tasks/north_c"]' );

-- South Tasks - C code
--
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'dht11',   '["services/south_c"]' );

--
-- Schedules
--
-- Use this to create guids: https://www.uuidgenerator.net/version1 */
-- Weekly repeat for timed schedules: set schedule_interval to 168:00:00
--


-- Core Tasks
--

-- Purge
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( 'cea17db8-6ccc-11e7-907b-a6006ad3dba0', -- id
                'purge',                                -- schedule_name
                'purge',                                -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '01:00:00',                             -- schedule_interval (evey hour)
                true,                                   -- exclusive
                true                                    -- enabled
              );

-- Statistics collection
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '2176eb68-7303-11e7-8cf7-a6006ad3dba0', -- id
                'stats collection',                     -- schedule_name
                'stats collector',                      -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:15',                             -- schedule_interval
                true,                                   -- exclusive
                true                                    -- enabled
              );


-- Check for expired certificates
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '2176eb68-7303-11e7-8cf7-a6107ad3db21', -- id
                'certificate checker',                  -- schedule_name
                'certificate checker',                  -- process_name
                2,                                      -- schedule_type (interval)
                '00:05:00',                             -- schedule_time
                '12:00:00',                             -- schedule_interval
                true,                                   -- exclusive
                true                                    -- enabled
              );

-- Storage Tasks
--

-- Execute a Backup every 1 hour
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( 'd1631422-9ec6-11e7-abc4-cec278b6b50a', -- id
                'backup hourly',                        -- schedule_name
                'backup',                               -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '01:00:00',                             -- schedule_interval
                true,                                   -- exclusive
                false                                   -- disabled
              );

-- On demand Backup
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( 'fac8dae6-d8d1-11e7-9296-cec278b6b50a', -- id
                'backup on demand',                     -- schedule_name
                'backup',                               -- process_name
                4,                                      -- schedule_type (manual)
                NULL,                                   -- schedule_time
                '00:00:00',                             -- schedule_interval
                true,                                   -- exclusive
                true                                    -- enabled
              );

-- On demand Restore
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '8d4d3ca0-de80-11e7-80c1-9a214cf093ae', -- id
                'restore on demand',                    -- schedule_name
                'restore',                              -- process_name
                4,                                      -- schedule_type (manual)
                NULL,                                   -- schedule_time
                '00:00:00',                             -- schedule_interval
                true,                                   -- exclusive
                true                                    -- enabled
              );

--
-- North Tasks
--

-- Readings OMF to PI - C Code
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '1cdf1ef8-7e02-11e8-adc0-fa7ae01bbebc', -- id
                'OMF_to_PI_north_C',                    -- schedule_name
                'North_Readings_to_PI',                 -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                true,                                    -- exclusive
                false                                     -- disabled
              );

-- Readings to HTTP - C Code
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( 'ccdf1ef8-7e02-11e8-adc0-fa7ae01bb3bc', -- id
                'HTTP_North_C',                         -- schedule_name
                'North_Readings_to_HTTP',               -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                true,                                   -- exclusive
                false                                   -- disabled
              );

-- DHT11 sensor south plugin - C Code
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '6b25f4d9-c7f3-4fc8-bd4a-4cf79f7055ca', -- id
                'dht11',                                -- schedule_name
                'dht11',                                -- process_name
                1,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '01:00:00',                             -- schedule_interval (evey hour)
                true,                                   -- exclusive
                false                                   -- disabled
              );

-- Statistics OMF to PI - C Code
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( 'f1e3b377-5acb-4bde-93d5-b6a792f76e07', -- id
                'Stats_OMF_to_PI_north_C',              -- schedule_name
                'North_Statistics_to_PI',               -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                true,                                    -- exclusive
                false                                     -- disabled
              );

-- Readings OMF to PI
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '2b614d26-760f-11e7-b5a5-be2e44b06b34', -- id
                'OMF to PI north',                      -- schedule_name
                'North Readings to PI',                 -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                true,                                   -- exclusive
                false                                   -- disabled
              );

-- Statistics OMF to PI
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '1d7c327e-7dae-11e7-bb31-be2e44b06b34', -- id
                'Stats OMF to PI north',                -- schedule_name
                'North Statistics to PI',               -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                true,                                   -- exclusive
                false                                   -- disabled
              );

-- Readings OMF to OCS
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '5d7fed92-fb9a-11e7-8c3f-9a214cf093ae', -- id
                'OMF to OCS north',                     -- schedule_name
                'North Readings to OCS',                -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                true,                                   -- exclusive
                false                                   -- disabled
              );
