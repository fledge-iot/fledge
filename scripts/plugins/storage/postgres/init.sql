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
-- PostgreSQL script to create the Fledge persistent Layer
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
DROP SCHEMA IF EXISTS fledge CASCADE;
DROP DATABASE IF EXISTS fledge;


-- Create the fledge database
CREATE DATABASE fledge WITH
    ENCODING = 'UTF8';

GRANT CONNECT ON DATABASE fledge TO PUBLIC;


-- Connect to fledge database
\connect fledge

----------------------------------------------------------------------
-- SCHEMA CREATION
----------------------------------------------------------------------

-- Create the fledge schema
CREATE SCHEMA fledge;
GRANT USAGE ON SCHEMA fledge TO PUBLIC;

------ SEQUENCES
CREATE SEQUENCE fledge.asset_messages_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.asset_status_changes_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.asset_status_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.asset_types_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.assets_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.links_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.resources_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.roles_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.streams_id_seq
    INCREMENT 1
    START 5
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.user_pwd_history_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.user_logins_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.users_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.backups_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE SEQUENCE fledge.asset_tracker_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

----- TABLES & SEQUENCES

-- Log Codes Table
-- List of tasks that log info into fledge.log.
CREATE TABLE fledge.log_codes (
       code        character(5)          NOT NULL,   -- The process that logs actions
       description character varying(80) NOT NULL,
       CONSTRAINT log_codes_pkey PRIMARY KEY (code) );


-- Generic Log Table
-- General log table for Fledge.
CREATE SEQUENCE fledge.log_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE fledge.log (
       id    bigint                      NOT NULL DEFAULT nextval('fledge.log_id_seq'::regclass),
       code  character(5)                NOT NULL,                                                -- The process that logged the action
       level smallint                    NOT NULL DEFAULT 0,                                      -- 0 Success - 1 Failure - 2 Warning - 4 Info
       log   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                            -- Generic log structure
       ts    timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT log_pkey PRIMARY KEY (id),
       CONSTRAINT log_fk1 FOREIGN KEY (code)
       REFERENCES fledge.log_codes (code) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

ALTER SEQUENCE fledge.log_id_seq OWNED BY fledge.log.id;

-- Index: log_ix1 - For queries by code
CREATE INDEX log_ix1
    ON fledge.log USING btree (code, ts, level);

CREATE INDEX log_ix2
    ON fledge.log(ts);


-- Asset status
-- List of status an asset can have.
CREATE TABLE fledge.asset_status (
       id          integer                NOT NULL DEFAULT nextval('fledge.asset_status_id_seq'::regclass),
       descriprion character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
        CONSTRAINT asset_status_pkey PRIMARY KEY (id) );


-- Asset Types
-- Type of asset (for example south, sensor etc.)
CREATE TABLE fledge.asset_types (
       id          integer                NOT NULL DEFAULT nextval('fledge.asset_types_id_seq'::regclass),
       description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
        CONSTRAINT asset_types_pkey PRIMARY KEY (id) );


-- Assets table
-- This table is used to list the assets used in Fledge
-- Reading do not necessarily have an asset, but whenever possible this
-- table provides information regarding the data collected.
CREATE TABLE fledge.assets (
       id           integer                     NOT NULL DEFAULT nextval('fledge.assets_id_seq'::regclass),         -- The internal PK for assets
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
         REFERENCES fledge.asset_status (id) MATCH SIMPLE
                 ON UPDATE NO ACTION
                 ON DELETE NO ACTION,
         CONSTRAINT assets_fk2 FOREIGN KEY (type_id)
         REFERENCES fledge.asset_types (id) MATCH SIMPLE
                 ON UPDATE NO ACTION
                 ON DELETE NO ACTION );

-- Index: fki_assets_fk1
CREATE INDEX fki_assets_fk1
    ON fledge.assets USING btree (status_id);

-- Index: fki_assets_fk2
CREATE INDEX fki_assets_fk2
    ON fledge.assets USING btree (type_id);

-- Index: assets_ix1
CREATE UNIQUE INDEX assets_ix1
    ON fledge.assets USING btree (code);


-- Asset Status Changes
-- When an asset changes its status, the previous status is added here.
-- tart_ts contains the value of ts of the row in the asset table.
CREATE TABLE fledge.asset_status_changes (
       id         bigint                      NOT NULL DEFAULT nextval('fledge.asset_status_changes_id_seq'::regclass),
       asset_id   integer                     NOT NULL,
       status_id  integer                     NOT NULL,
       log        jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       start_ts   timestamp(6) with time zone NOT NULL,
       ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_status_changes_pkey PRIMARY KEY (id),
       CONSTRAINT asset_status_changes_fk1 FOREIGN KEY (asset_id)
       REFERENCES fledge.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT asset_status_changes_fk2 FOREIGN KEY (status_id)
       REFERENCES fledge.asset_status (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_asset_status_changes_fk1
    ON fledge.asset_status_changes USING btree (asset_id);

CREATE INDEX fki_asset_status_changes_fk2
    ON fledge.asset_status_changes USING btree (status_id);


-- Links table
-- Links among assets in 1:M relationships.
CREATE TABLE fledge.links (
       id         integer                     NOT NULL DEFAULT nextval('fledge.links_id_seq'::regclass),
       asset_id   integer                     NOT NULL,
       properties jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT links_pkey PRIMARY KEY (id),
       CONSTRAINT links_fk1 FOREIGN KEY (asset_id)
       REFERENCES fledge.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_links_fk1
    ON fledge.links USING btree (asset_id);


-- Assets Linked table
-- In links, relationship between an asset and other assets.
CREATE TABLE fledge.asset_links (
       link_id  integer                     NOT NULL,
       asset_id integer                     NOT NULL,
       ts       timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_links_pkey PRIMARY KEY (link_id, asset_id) );

CREATE INDEX fki_asset_links_fk1
    ON fledge.asset_links USING btree (link_id);

CREATE INDEX fki_asset_link_fk2
    ON fledge.asset_links USING btree (asset_id);


-- Asset Message Status table
-- Status of the messages to send South
CREATE SEQUENCE fledge.asset_message_status_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE fledge.asset_message_status (
       id          integer                NOT NULL DEFAULT nextval('fledge.asset_message_status_id_seq'::regclass),
       description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
        CONSTRAINT asset_message_status_pkey PRIMARY KEY (id) );


-- Asset Messages table
-- Messages directed to the south devices.
CREATE TABLE fledge.asset_messages (
       id        bigint                      NOT NULL DEFAULT nextval('fledge.asset_messages_id_seq'::regclass),
       asset_id  integer                     NOT NULL,
       status_id integer                     NOT NULL,
       message   jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       ts        timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_messages_pkey PRIMARY KEY (id),
       CONSTRAINT asset_messages_fk1 FOREIGN KEY (asset_id)
       REFERENCES fledge.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT asset_messages_fk2 FOREIGN KEY (status_id)
       REFERENCES fledge.asset_message_status (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_asset_messages_fk1
    ON fledge.asset_messages USING btree (asset_id);

CREATE INDEX fki_asset_messages_fk2
    ON fledge.asset_messages USING btree (status_id);


-- Readings table
-- This tables contains the readings for assets.
-- An asset can be a south with multiple sensor, a single sensor,
-- a software or anything that generates data that is sent to Fledge
CREATE SEQUENCE fledge.readings_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE fledge.readings (
    id         bigint                      NOT NULL DEFAULT nextval('fledge.readings_id_seq'::regclass),
    asset_code character varying(255)      NOT NULL,                      -- The provided asset code. Not necessarily located in the
                                                                          -- assets table.
    reading    jsonb                       NOT NULL DEFAULT '{}'::jsonb,  -- The json object received
    user_ts    timestamp(6) with time zone NOT NULL DEFAULT now(),        -- The user timestamp extracted by the received message
    ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
    CONSTRAINT readings_pkey PRIMARY KEY (id) );

CREATE INDEX fki_readings_fk1
    ON fledge.readings USING btree (asset_code, user_ts desc);

CREATE INDEX readings_ix2
    ON fledge.readings USING btree (asset_code);

CREATE INDEX readings_ix3
    ON fledge.readings USING btree (user_ts);


-- Streams table
-- List of the streams to the Cloud.
CREATE TABLE fledge.streams (
       id             integer                     NOT NULL DEFAULT nextval('fledge.streams_id_seq'::regclass),         -- Sequence ID
       description    character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",  -- A brief description of the stream entry
       properties     jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- A generic set of properties
       object_stream  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Definition of what must be streamed
       object_block   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Definition of how the stream must be organised
       object_filter  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Any filter involved in selecting the data to stream
       active_window  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- The window of operations
       active         boolean                     NOT NULL DEFAULT true,                                                -- When false, all data to this stream stop and are inactive
       last_object    bigint                      NOT NULL DEFAULT 0,                                                   -- The ID of the last object streamed (asset or reading, depending on the object_stream)
       ts             timestamp(6) with time zone NOT NULL DEFAULT now(),                                               -- Creation or last update
       CONSTRAINT strerams_pkey PRIMARY KEY (id));


-- Configuration table
-- The configuration in JSON format.
-- The PK is also used in the REST API
-- Values is a jsonb column
-- ts is set by default with now().
CREATE TABLE fledge.configuration (
       key         character varying(255)      NOT NULL COLLATE pg_catalog."default", -- Primary key
       display_name character varying(255)     NOT NULL,                              -- Display Name
       description character varying(255)      NOT NULL,                              -- Description, in plain text
       value       jsonb                       NOT NULL DEFAULT '{}'::jsonb,          -- JSON object containing the configuration values
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                -- Timestamp, updated at every change
       CONSTRAINT configuration_pkey PRIMARY KEY (key) );


-- Configuration changes
-- This table has the same structure of fledge.configuration, plus the timestamp that identifies the time it has changed
-- The table is used to keep track of the changes in the "value" column
CREATE TABLE fledge.configuration_changes (
       key                 character varying(255)      NOT NULL COLLATE pg_catalog."default",
       configuration_ts    timestamp(6) with time zone NOT NULL,
       configuration_value jsonb                       NOT NULL,
       ts                  timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT configuration_changes_pkey PRIMARY KEY (key, configuration_ts) );


-- Statistics table
-- The table is used to keep track of the statistics for Fledge
CREATE TABLE fledge.statistics (
       key         character varying(255)      NOT NULL COLLATE pg_catalog."default", -- Primary key, all uppercase
       description character varying(255)      NOT NULL,                              -- Description, in plan text
       value       bigint                      NOT NULL DEFAULT 0,                    -- Integer value, the statistics
       previous_value       bigint             NOT NULL DEFAULT 0,                    -- Integer value, the prev stat to be updated by metrics collector
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                -- Timestamp, updated at every change
       CONSTRAINT statistics_pkey PRIMARY KEY (key) );


-- Statistics history
-- Keeps history of the statistics in fledge.statistics
-- The table is updated at startup
CREATE SEQUENCE fledge.statistics_history_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE fledge.statistics_history (
       id          bigint                      NOT NULL DEFAULT nextval('fledge.statistics_history_id_seq'::regclass),
       key         character varying(255)      NOT NULL COLLATE pg_catalog."default",                         -- Coumpund primary key, all uppercase
       history_ts  timestamp(6) with time zone NOT NULL,                                                      -- Compound primary key, the highest value of statistics.ts when statistics are copied here.
       value       bigint                      NOT NULL DEFAULT 0,                                            -- Integer value, the statistics
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                                        -- Timestamp, updated at every change
       CONSTRAINT statistics_history_pkey PRIMARY KEY (key, history_ts) );

CREATE INDEX statistics_history_ix2
    ON fledge.statistics_history(key);

CREATE INDEX statistics_history_ix3
    ON fledge.statistics_history (history_ts);

-- Contains history of the statistics_history table
-- Data are historicized daily
--
CREATE TABLE fledge.statistics_history_daily (
        year        integer NOT NULL,
        day         timestamp(6) with time zone NOT NULL,
        key         character varying(255)      NOT NULL,
        value       bigint                      NOT NULL DEFAULT 0
);

CREATE INDEX statistics_history_daily_ix1
    ON statistics_history_daily (year);

-- Resources table
-- A resource and be anything that is available or can be done in Fledge. Examples:
-- - Access to assets
-- - Access to readings
-- - Access to streams
CREATE TABLE fledge.resources (
    id          bigint                 NOT NULL DEFAULT nextval('fledge.resources_id_seq'::regclass),
    code        character(10)          NOT NULL COLLATE pg_catalog."default",
    description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
    CONSTRAINT  resources_pkey PRIMARY KEY (id) );

CREATE UNIQUE INDEX resource_ix1
    ON fledge.resources USING btree (code COLLATE pg_catalog."default");


-- Roles table
CREATE TABLE fledge.roles (
    id          integer                NOT NULL DEFAULT nextval('fledge.roles_id_seq'::regclass),
    name        character varying(25)  NOT NULL COLLATE pg_catalog."default",
    description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
    CONSTRAINT  roles_pkey PRIMARY KEY (id) );

CREATE UNIQUE INDEX roles_ix1
    ON fledge.roles USING btree (name COLLATE pg_catalog."default");


-- Roles, Resources and Permssions table
-- For each role there are resources associated, with a given permission.
CREATE TABLE fledge.role_resource_permission (
       role_id     integer NOT NULL,
       resource_id integer NOT NULL,
       access      jsonb   NOT NULL DEFAULT '{}'::jsonb,
       CONSTRAINT role_resource_permission_pkey PRIMARY KEY (role_id, resource_id),
       CONSTRAINT role_resource_permissions_fk1 FOREIGN KEY (role_id)
       REFERENCES fledge.roles (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT role_resource_permissions_fk2 FOREIGN KEY (resource_id)
       REFERENCES fledge.resources (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_role_resource_permissions_fk1
    ON fledge.role_resource_permission USING btree (role_id);

CREATE INDEX fki_role_resource_permissions_fk2
    ON fledge.role_resource_permission USING btree (resource_id);


-- Roles Assets Permissions table
-- Combination of roles, assets and access
CREATE TABLE fledge.role_asset_permissions (
    role_id    integer NOT NULL,
    asset_id   integer NOT NULL,
    access     jsonb   NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT role_asset_permissions_pkey PRIMARY KEY (role_id, asset_id),
    CONSTRAINT role_asset_permissions_fk1 FOREIGN KEY (role_id)
    REFERENCES fledge.roles (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
    CONSTRAINT role_asset_permissions_fk2 FOREIGN KEY (asset_id)
    REFERENCES fledge.assets (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
    CONSTRAINT user_asset_permissions_fk1 FOREIGN KEY (role_id)
    REFERENCES fledge.roles (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION );

CREATE INDEX fki_role_asset_permissions_fk1
    ON fledge.role_asset_permissions USING btree (role_id);

CREATE INDEX fki_role_asset_permissions_fk2
    ON fledge.role_asset_permissions USING btree (asset_id);


-- Users table
-- Fledge users table.
-- Authentication Method:
-- 0 - Disabled
-- 1 - PWD
-- 2 - Public Key
CREATE TABLE fledge.users (
       id                integer                     NOT NULL DEFAULT nextval('fledge.users_id_seq'::regclass),
       uname             character varying(80)       NOT NULL COLLATE pg_catalog."default",
       real_name         character varying(255) NOT NULL,
       role_id           integer                     NOT NULL,
       description       character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
       pwd               character varying(255)      COLLATE pg_catalog."default",
       public_key        character varying(255)      COLLATE pg_catalog."default",
       enabled           boolean                     NOT NULL DEFAULT TRUE,
       pwd_last_changed  timestamp(6) with time zone NOT NULL DEFAULT now(),
       access_method     character varying(5) CHECK( access_method IN ('any','pwd','cert') )  NOT NULL DEFAULT 'any',
          CONSTRAINT users_pkey PRIMARY KEY (id),
          CONSTRAINT users_fk1 FOREIGN KEY (role_id)
          REFERENCES fledge.roles (id) MATCH SIMPLE
                  ON UPDATE NO ACTION
                  ON DELETE NO ACTION );

CREATE INDEX fki_users_fk1
    ON fledge.users USING btree (role_id);

CREATE UNIQUE INDEX users_ix1
    ON fledge.users USING btree (uname COLLATE pg_catalog."default");

-- User Login table
-- List of logins executed by the users.
CREATE TABLE fledge.user_logins (
       id               integer                     NOT NULL DEFAULT nextval('fledge.user_logins_id_seq'::regclass),
       user_id          integer                     NOT NULL,
       ip               inet                        NOT NULL DEFAULT '0.0.0.0'::inet,
       ts               timestamp(6) with time zone NOT NULL DEFAULT now(),
       token            character varying(255)      NOT NULL,
       token_expiration timestamp(6) with time zone NOT NULL,
       CONSTRAINT user_logins_pkey PRIMARY KEY (id),
       CONSTRAINT user_logins_fk1 FOREIGN KEY (user_id)
       REFERENCES fledge.users (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_user_logins_fk1
    ON fledge.user_logins USING btree (user_id);


-- User Password History table
-- Maintains a history of passwords
CREATE TABLE fledge.user_pwd_history (
       id               integer                     NOT NULL DEFAULT nextval('fledge.user_pwd_history_id_seq'::regclass),
       user_id          integer                     NOT NULL,
       pwd              character varying(255)      COLLATE pg_catalog."default",
       CONSTRAINT user_pwd_history_pkey PRIMARY KEY (id),
       CONSTRAINT user_pwd_history_fk1 FOREIGN KEY (user_id)
       REFERENCES fledge.users (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_user_pwd_history_fk1
    ON fledge.user_pwd_history USING btree (user_id);


-- User Resource Permissions table
-- Association of users with resources and given permissions for each resource.
CREATE TABLE fledge.user_resource_permissions (
       user_id     integer NOT NULL,
       resource_id integer NOT NULL,
       access      jsonb NOT NULL DEFAULT '{}'::jsonb,
        CONSTRAINT user_resource_permissions_pkey PRIMARY KEY (user_id, resource_id),
        CONSTRAINT user_resource_permissions_fk1 FOREIGN KEY (user_id)
        REFERENCES fledge.users (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION,
        CONSTRAINT user_resource_permissions_fk2 FOREIGN KEY (resource_id)
        REFERENCES fledge.resources (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION );

CREATE INDEX fki_user_resource_permissions_fk1
    ON fledge.user_resource_permissions USING btree (user_id);

CREATE INDEX fki_user_resource_permissions_fk2
    ON fledge.user_resource_permissions USING btree (resource_id);


-- User Asset Permissions table
-- Association of users with assets
CREATE TABLE fledge.user_asset_permissions (
       user_id    integer NOT NULL,
       asset_id   integer NOT NULL,
       access     jsonb NOT NULL DEFAULT '{}'::jsonb,
       CONSTRAINT user_asset_permissions_pkey PRIMARY KEY (user_id, asset_id),
       CONSTRAINT user_asset_permissions_fk1 FOREIGN KEY (user_id)
       REFERENCES fledge.users (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT user_asset_permissions_fk2 FOREIGN KEY (asset_id)
       REFERENCES fledge.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

CREATE INDEX fki_user_asset_permissions_fk1
    ON fledge.user_asset_permissions USING btree (user_id);

CREATE INDEX fki_user_asset_permissions_fk2
    ON fledge.user_asset_permissions USING btree (asset_id);


-- List of scheduled Processes
CREATE TABLE fledge.scheduled_processes (
             name   character varying(255)  NOT NULL, -- Name of the process
             script jsonb,                            -- Full path of the process
  CONSTRAINT scheduled_processes_pkey PRIMARY KEY ( name ) );


-- List of schedules
CREATE TABLE fledge.schedules (
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
  REFERENCES fledge.scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );


-- List of tasks
CREATE TABLE fledge.tasks (
             id           uuid                        NOT NULL,               -- PK
             schedule_name character varying(255),                            -- Name of the task
             schedule_id  uuid                        NOT NULL,               -- Link between schedule & task table
             process_name character varying(255)      NOT NULL,               -- Name of the task's process
             state        smallint                    NOT NULL,               -- 1-Running, 2-Complete, 3-Cancelled, 4-Interrupted
             start_time   timestamp(6) with time zone NOT NULL DEFAULT now(), -- The date and time the task started
             end_time     timestamp(6) with time zone,                        -- The date and time the task ended
             reason       character varying(255),                             -- The reason why the task ended
             pid          integer                     NOT NULL,               -- Linux process id
             exit_code    integer,                                            -- Process exit status code (negative means exited via signal)
  CONSTRAINT tasks_pkey PRIMARY KEY ( id ),
  CONSTRAINT tasks_fk1 FOREIGN KEY  ( process_name )
  REFERENCES fledge.scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );

CREATE INDEX tasks_ix1
   ON fledge.tasks(schedule_name, start_time);


-- Tracks types already created into PI Server
CREATE TABLE fledge.omf_created_objects (
    configuration_key character varying(255)	NOT NULL,            -- FK to fledge.configuration
    type_id           integer           	    NOT NULL,            -- Identifies the specific PI Server type
    asset_code        character varying(255)   NOT NULL,
    CONSTRAINT omf_created_objects_pkey PRIMARY KEY (configuration_key,type_id, asset_code),
    CONSTRAINT omf_created_objects_fk1 FOREIGN KEY (configuration_key)
    REFERENCES fledge.configuration (key) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION );


-- Backups information
-- Stores information about executed backups
CREATE TABLE fledge.backups (
    id         bigint                      NOT NULL DEFAULT nextval('fledge.backups_id_seq'::regclass),
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

-- Fledge DB version
CREATE TABLE fledge.version (id CHAR(10));

-- Create the configuration category_children table
CREATE TABLE fledge.category_children (
       parent	character varying(255)	NOT NULL,
       child	character varying(255)	NOT NULL,
       CONSTRAINT config_children_pkey PRIMARY KEY (parent, child) );

-- Create the asset_tracker table
CREATE TABLE fledge.asset_tracker (
       id            integer                NOT NULL DEFAULT nextval('fledge.asset_tracker_id_seq'::regclass),
       asset         character(255)         NOT NULL,
       event         character varying(50)  NOT NULL,
       service       character varying(255) NOT NULL,
       fledge       character varying(50)  NOT NULL,
       plugin        character varying(50)  NOT NULL,
       ts            timestamp(6) with time zone NOT NULL DEFAULT now() );

CREATE INDEX asset_tracker_ix1 ON fledge.asset_tracker USING btree (asset);
CREATE INDEX asset_tracker_ix2 ON fledge.asset_tracker USING btree (service);

-- Create plugin_data table
-- Persist plugin data in the storage
CREATE TABLE fledge.plugin_data (
	key     character varying(255)    NOT NULL,
	data    jsonb                     NOT NULL DEFAULT '{}'::jsonb,
	CONSTRAINT plugin_data_pkey PRIMARY KEY (key) );

-- Create packages table
CREATE TABLE fledge.packages (
             id                uuid                   NOT NULL, -- PK
             name              character varying(255) NOT NULL, -- Package name
             action            character varying(10)  NOT NULL, -- APT actions:
                                                                -- list
                                                                -- install
                                                                -- purge
                                                                -- update
             status            INTEGER                NOT NULL, -- exit code
                                                                -- -1       - in-progress
                                                                --  0       - success
                                                                -- Non-Zero - failed
             log_file_uri      character varying(255) NOT NULL, -- Package Log file relative path
  CONSTRAINT packages_pkey PRIMARY KEY  ( id ) );

-- Create filters table
CREATE TABLE fledge.filters (
             name        character varying(255)        NOT NULL,
             plugin      character varying(255)        NOT NULL,
       CONSTRAINT filter_pkey PRIMARY KEY( name ) );

-- Create filter_users table
CREATE TABLE fledge.filter_users (
             name        character varying(255)        NOT NULL,
             "user"      character varying(255)        NOT NULL);

-- Grants to fledge schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA fledge TO PUBLIC;



----------------------------------------------------------------------
-- Initialization phase - DML
----------------------------------------------------------------------

-- Roles
DELETE FROM fledge.roles;
INSERT INTO fledge.roles ( name, description )
     VALUES ('admin', 'All CRUD privileges'),
            ('user', 'All CRUD operations and self profile management');


-- Users
DELETE FROM fledge.users;
INSERT INTO fledge.users ( uname, real_name, pwd, role_id, description )
     VALUES ('admin', 'Admin user', '39b16499c9311734c595e735cffb5d76ddffb2ebf8cf4313ee869525a9fa2c20:f400c843413d4c81abcba8f571e6ddb6', 1, 'admin user'),
            ('user', 'Normal user', '39b16499c9311734c595e735cffb5d76ddffb2ebf8cf4313ee869525a9fa2c20:f400c843413d4c81abcba8f571e6ddb6', 2, 'normal user');

-- User password history
DELETE FROM fledge.user_pwd_history;


-- User logins
DELETE FROM fledge.user_logins;


-- Log Codes
DELETE FROM fledge.log_codes;
INSERT INTO fledge.log_codes ( code, description )
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
            ( 'BKEXC', 'Backup Complete' ),
            ( 'NTFDL', 'Notification Deleted' ),
            ( 'NTFAD', 'Notification Added' ),
            ( 'NTFSN', 'Notification Sent' ),
            ( 'NTFCL', 'Notification Cleared' ),
            ( 'NTFST', 'Notification Server Startup' ),
            ( 'NTFSD', 'Notification Server Shutdown' ),
            ( 'PKGIN', 'Package installation' ),
            ( 'PKGUP', 'Package updated' ),
            ( 'PKGRM', 'Package purged' );

--
-- Configuration parameters
--
DELETE FROM fledge.configuration;

-- Statistics
INSERT INTO fledge.statistics ( key, description, value, previous_value )
     VALUES ( 'READINGS',             'Readings received by Fledge', 0, 0 ),
            ( 'BUFFERED',             'Readings currently in the Fledge buffer', 0, 0 ),
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
INSERT INTO fledge.scheduled_processes ( name, script ) VALUES ( 'purge',               '["tasks/purge"]'       );
INSERT INTO fledge.scheduled_processes ( name, script ) VALUES ( 'purge_system',        '["tasks/purge_system"]');
INSERT INTO fledge.scheduled_processes ( name, script ) VALUES ( 'stats collector',     '["tasks/statistics"]'  );
INSERT INTO fledge.scheduled_processes ( name, script ) VALUES ( 'FledgeUpdater',       '["tasks/update"]'      );
INSERT INTO fledge.scheduled_processes ( name, script ) VALUES ( 'certificate checker', '["tasks/check_certs"]' );

-- Storage Tasks
--
INSERT INTO fledge.scheduled_processes (name, script) VALUES ('backup',  '["tasks/backup"]'  );
INSERT INTO fledge.scheduled_processes (name, script) VALUES ('restore', '["tasks/restore"]' );

-- South, Notification, North Tasks
--
INSERT INTO fledge.scheduled_processes (name, script)   VALUES ( 'south_c',        '["services/south_c"]'        );
INSERT INTO fledge.scheduled_processes (name, script)   VALUES ( 'notification_c', '["services/notification_c"]' );
INSERT INTO fledge.scheduled_processes (name, script)   VALUES ( 'north_c',        '["tasks/north_c"]'           );
INSERT INTO fledge.scheduled_processes (name, script)   VALUES ( 'north',          '["tasks/north"]'             );
INSERT INTO fledge.scheduled_processes (name, script)   VALUES ( 'north_C',        '["services/north_C"]'        );
INSERT INTO fledge.scheduled_processes (name, script)   VALUES ( 'dispatcher_c',   '["services/dispatcher_c"]'   );

--
-- Schedules
--
-- Use this to create guids: https://www.uuidgenerator.net/version1 */
-- Weekly repeat for timed schedules: set schedule_interval to 168:00:00
--


-- Core Tasks
--

-- Purge
INSERT INTO fledge.schedules ( id, schedule_name, process_name, schedule_type,
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

--
-- Purge System
--
-- Purge old information from the fledge database
INSERT INTO fledge.schedules ( id, schedule_name, process_name, schedule_type,
                               schedule_time, schedule_interval, exclusive, enabled )
VALUES ( 'd37265f0-c83a-11eb-b8bc-0242ac130003', -- id
         'purge_system',                         -- schedule_name
         'purge_system',                         -- process_name
         3,                                      -- schedule_type (interval)
         NULL,                                   -- schedule_time
         '23:50:00',                             -- schedule_interval (evey 24 hours)
         'true',                                 -- exclusive
         'true'                                  -- enabled
       );


-- Statistics collection
INSERT INTO fledge.schedules ( id, schedule_name, process_name, schedule_type,
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
INSERT INTO fledge.schedules ( id, schedule_name, process_name, schedule_type,
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
INSERT INTO fledge.schedules ( id, schedule_name, process_name, schedule_type,
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
INSERT INTO fledge.schedules ( id, schedule_name, process_name, schedule_type,
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
INSERT INTO fledge.schedules ( id, schedule_name, process_name, schedule_type,
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
