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
-- foglamp_ddl.sql
--
-- PostgreSQL script to create the FogLAMP persistent Layer
--

-- NOTE:
-- This script must be launched with:
-- PGPASSWORD=postgres psql -U postgres -h localhost -f foglamp_ddl.sql postgres


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


----------------------------------------------------------------------
-- SCHEMA CREATION
----------------------------------------------------------------------


-- Dropping objects
DROP SCHEMA IF EXISTS foglamp CASCADE;
DROP DATABASE IF EXISTS foglamp;
DROP TABLESPACE IF EXISTS foglamp;
DROP USER IF EXISTS foglamp;

-- Create the foglamp user
CREATE USER foglamp WITH
  LOGIN
  SUPERUSER
  INHERIT
  CREATEDB
  CREATEROLE
  REPLICATION;

ALTER USER foglamp ENCRYPTED PASSWORD 'foglamp';


-- Create the foglamp tablespace
CREATE TABLESPACE foglamp
  OWNER foglamp
  LOCATION '/var/lib/postgresql/9.6/';


-- Create the foglamp database
CREATE DATABASE foglamp WITH
    OWNER = foglamp
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_GB.UTF-8'
    LC_CTYPE = 'en_GB.UTF-8'
    TABLESPACE = foglamp
    CONNECTION LIMIT = -1;


-- Connect to foglamp
\connect foglamp

-- Create the foglamp schema
CREATE SCHEMA foglamp
    AUTHORIZATION foglamp;


------ SEQUENCES
CREATE SEQUENCE foglamp.log_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

ALTER SEQUENCE foglamp.log_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.asset_message_status_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.asset_message_status_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.asset_messages_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.asset_messages_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.asset_status_changes_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.asset_status_changes_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.asset_status_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.asset_status_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.asset_types_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.asset_types_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.assets_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.assets_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.destinations_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.destinations_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.links_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.links_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.readings_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.readings_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.statistics_history_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.statistics_history_id_seq OWNER TO foglamp;



CREATE SEQUENCE foglamp.resources_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.resources_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.roles_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.roles_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.streams_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.streams_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.user_logins_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.user_logins_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.users_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.users_id_seq OWNER TO foglamp;


----- TABLES

-- Log Codes Table
CREATE TABLE foglamp.log_codes (
       code        character(5)          NOT NULL,   -- The process that logs actions
       description character varying(80) NOT NULL,
       CONSTRAINT log_codes_pkey PRIMARY KEY (code)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE) TABLESPACE foglamp;

ALTER TABLE foglamp.log_codes OWNER to foglamp;
COMMENT ON TABLE foglamp.log_codes IS
'List of tasks that log info into foglamp.log.';


-- Generic Log Table
CREATE TABLE foglamp.log (
       id    bigint                      NOT NULL DEFAULT nextval('foglamp.log_id_seq'::regclass),
       code  character(5)                NOT NULL,                                                -- The process that logged the action
       level smallint                    NOT NULL DEFAULT 0,                                      -- 0 Success - 1 Failure - 2 Warning - 4 Info
       log   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                            -- Generic log structure
       ts    timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT log_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT log_fk1 FOREIGN KEY (code)
       REFERENCES foglamp.log_codes (code) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE) TABLESPACE foglamp;

ALTER TABLE foglamp.log OWNER to foglamp;
COMMENT ON TABLE foglamp.log IS
'General log table for FogLAMP';

-- Index: log_ix1 - For queries by code
CREATE INDEX log_ix1
    ON foglamp.log USING btree (code, ts, level)
    TABLESPACE foglamp;


-- Asset status
CREATE TABLE foglamp.asset_status (
       id          integer                NOT NULL DEFAULT nextval('foglamp.asset_status_id_seq'::regclass),
       descriprion character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
        CONSTRAINT asset_status_pkey PRIMARY KEY (id)
             USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.asset_status OWNER to foglamp;
COMMENT ON TABLE foglamp.asset_status IS
'List of status an asset can have.';


-- Asset Types
CREATE TABLE foglamp.asset_types (
       id          integer                NOT NULL DEFAULT nextval('foglamp.asset_types_id_seq'::regclass),
       description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default", 
        CONSTRAINT asset_types_pkey PRIMARY KEY (id)
             USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.asset_types OWNER to foglamp;
COMMENT ON TABLE foglamp.asset_types IS
'Type of asset (for example device, sensor etc.)';


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
       properties   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                        -- A generic JSON structure. Some elements (for example "labels") may be used in the rule to send messages to the devices or data to the cloud
       has_readings boolean                     NOT NULL DEFAULT false,                                              -- A boolean column, when TRUE, it means that the asset may have rows in the readings table
       ts           timestamp(6) with time zone NOT NULL DEFAULT now(),
         CONSTRAINT assets_pkey PRIMARY KEY (id)
              USING INDEX TABLESPACE foglamp,
         CONSTRAINT assets_fk1 FOREIGN KEY (status_id)
         REFERENCES foglamp.asset_status (id) MATCH SIMPLE
                 ON UPDATE NO ACTION
                 ON DELETE NO ACTION,
         CONSTRAINT assets_fk2 FOREIGN KEY (type_id)
         REFERENCES foglamp.asset_types (id) MATCH SIMPLE
                 ON UPDATE NO ACTION
                 ON DELETE NO ACTION )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.assets OWNER to foglamp;
COMMENT ON TABLE foglamp.assets IS
'The assets table.';

-- Index: fki_assets_fk1
CREATE INDEX fki_assets_fk1
    ON foglamp.assets USING btree (status_id)
    TABLESPACE foglamp;

-- Index: fki_assets_fk2
CREATE INDEX fki_assets_fk2
    ON foglamp.assets USING btree (type_id)
    TABLESPACE foglamp;

-- Index: assets_ix1
CREATE UNIQUE INDEX assets_ix1
    ON foglamp.assets USING btree (code)
    TABLESPACE foglamp;


-- Asset Status Changes
CREATE TABLE foglamp.asset_status_changes (
       id         bigint                      NOT NULL DEFAULT nextval('foglamp.asset_status_changes_id_seq'::regclass),
       asset_id   integer                     NOT NULL,
       status_id  integer                     NOT NULL,
       log        jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       start_ts   timestamp(6) with time zone NOT NULL,
       ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_status_changes_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT asset_status_changes_fk1 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT asset_status_changes_fk2 FOREIGN KEY (status_id)
       REFERENCES foglamp.asset_status (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.asset_status_changes OWNER to foglamp;
COMMENT ON TABLE foglamp.asset_status_changes IS
'When an asset changes its status, the previous status is added here.
start_ts contains the value of ts of the row in the asset table.';

CREATE INDEX fki_asset_status_changes_fk1
    ON foglamp.asset_status_changes USING btree (asset_id)
    TABLESPACE foglamp;

CREATE INDEX fki_asset_status_changes_fk2
    ON foglamp.asset_status_changes USING btree (status_id)
    TABLESPACE foglamp;


-- Links table
CREATE TABLE foglamp.links (
       id         integer                     NOT NULL DEFAULT nextval('foglamp.links_id_seq'::regclass),
       asset_id   integer                     NOT NULL,
       properties jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT links_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT links_fk1 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.links OWNER to foglamp;
COMMENT ON TABLE foglamp.links IS
'Links among assets in 1:M relationships.';

CREATE INDEX fki_links_fk1
    ON foglamp.links USING btree (asset_id)
    TABLESPACE foglamp;


-- Assets Linked table
CREATE TABLE foglamp.asset_links (
       link_id  integer                     NOT NULL,
       asset_id integer                     NOT NULL,
       ts       timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_links_pkey PRIMARY KEY (link_id, asset_id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT asset_link_fk2 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT asset_links_fk1 FOREIGN KEY (link_id)
       REFERENCES foglamp.links (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.asset_links OWNER to foglamp;
COMMENT ON TABLE foglamp.asset_links IS
'In links, relationship between an asset and other assets';

CREATE INDEX fki_asset_link_fk2
    ON foglamp.asset_links USING btree (asset_id)
    TABLESPACE foglamp;

CREATE INDEX fki_asset_links_fk1
    ON foglamp.asset_links USING btree (link_id)
    TABLESPACE foglamp;


-- Asset Message Status table
CREATE TABLE foglamp.asset_message_status (
       id          integer                NOT NULL DEFAULT nextval('foglamp.asset_message_status_id_seq'::regclass),
       description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
        CONSTRAINT asset_message_status_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.asset_message_status OWNER to foglamp;
COMMENT ON TABLE foglamp.asset_message_status IS
'Status of the messages to send to a device';


-- Asset Messages table
CREATE TABLE foglamp.asset_messages (
       id        bigint                      NOT NULL DEFAULT nextval('foglamp.asset_messages_id_seq'::regclass),
       asset_id  integer                     NOT NULL,
       status_id integer                     NOT NULL,
       message   jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       ts        timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT asset_messages_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT asset_messages_fk1 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT asset_messages_fk2 FOREIGN KEY (status_id)
       REFERENCES foglamp.asset_message_status (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.asset_messages OWNER to foglamp;
COMMENT ON TABLE foglamp.asset_messages IS
'Messages directed to the devices.';

CREATE INDEX fki_asset_messages_fk1
    ON foglamp.asset_messages USING btree (asset_id)
    TABLESPACE foglamp;

CREATE INDEX fki_asset_messages_fk2
    ON foglamp.asset_messages USING btree (status_id)
    TABLESPACE foglamp;


-- Readings table
-- This tables contains the readings for assets.
-- An asset can be a device with multiple sensor, a single sensor,
-- a software or anything that generates data that is sent to FogLAMP
CREATE TABLE foglamp.readings (
    id         bigint                      NOT NULL DEFAULT nextval('foglamp.readings_id_seq'::regclass),
    asset_code character varying(50)       NOT NULL,                      -- The provided asset code. Not necessarily located in the
                                                                          -- assets table.
    read_key   uuid                        UNIQUE,                        -- An optional unique key used to avoid double-loading.
    reading    jsonb                       NOT NULL DEFAULT '{}'::jsonb,  -- The json object received
    user_ts    timestamp(6) with time zone NOT NULL DEFAULT now(),        -- The user timestamp extracted by the received message
    ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
    CONSTRAINT readings_pkey PRIMARY KEY (id)
         USING INDEX TABLESPACE foglamp
--  , CONSTRAINT readings_fk1 FOREIGN KEY (asset_code)
--  REFERENCES foglamp.assets (code) MATCH SIMPLE
--          ON UPDATE NO ACTION
--          ON DELETE NO ACTION
  )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.readings OWNER to foglamp;
COMMENT ON TABLE foglamp.readings IS
'Readings from sensors and devices.';

CREATE INDEX fki_readings_fk1
    ON foglamp.readings USING btree (asset_code)
    TABLESPACE foglamp;

CREATE INDEX readings_ix1
    ON foglamp.readings USING btree (read_key)
    TABLESPACE foglamp;


-- Destinations table
CREATE TABLE foglamp.destinations (
       id            integer                     NOT NULL DEFAULT nextval('foglamp.destinations_id_seq'::regclass),   -- Sequence ID
       type          smallint                    NOT NULL DEFAULT 1,                                                  -- Enum : 1: OMF, 2: Elasticsearch
       description   character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default", -- A brief description of the destination entry
       properties    jsonb                       NOT NULL DEFAULT '{ "streaming" : "all" }'::jsonb,                   -- A generic set of properties
       active_window jsonb                       NOT NULL DEFAULT '[ "always" ]'::jsonb,                              -- The window of operations
       active        boolean                     NOT NULL DEFAULT true,                                               -- When false, all streams to this destination stop and are inactive
       ts            timestamp(6) with time zone NOT NULL DEFAULT now(),                                              -- Creation or last update
       CONSTRAINT destination_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.destinations OWNER to foglamp;
COMMENT ON TABLE foglamp.destinations IS
'Multiple destinations are allowed, for example multiple PI servers.';


-- Streams table
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
       CONSTRAINT strerams_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT streams_fk1 FOREIGN KEY (destination_id)
       REFERENCES foglamp.destinations (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.streams OWNER to foglamp;
COMMENT ON TABLE foglamp.streams IS
'List of the streams to the Cloud.';

CREATE INDEX fki_streams_fk1
    ON foglamp.streams USING btree (destination_id)
    TABLESPACE foglamp;


-- Configuration table
-- The configuration in JSON format.
-- The PK is a 10 CHAR code (standard is to keep it UPPERCASE and usually filled with _
-- Values is a jsonb column
-- ts is set by default with now().
CREATE TABLE foglamp.configuration (
       key         character(10)               NOT NULL COLLATE pg_catalog."default", -- Primary key, the rules are: 1. All uppercase, 2. All characters are filled.
       description character varying(255)      NOT NULL,                              -- Description, in plan text
       value       jsonb                       NOT NULL DEFAULT '{}'::jsonb,          -- JSON object containing the configuration values
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                -- Timestamp, updated at every change
       CONSTRAINT configuration_pkey PRIMARY KEY (key)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.configuration OWNER to foglamp;


-- Configuration changes
-- This table has the same structure of foglamp.configuration, plus the timestamp that identifies the time it has changed
-- The table is used to keep track of the changes in the "value" column
CREATE TABLE foglamp.configuration_changes (
       key                 character(10)               NOT NULL COLLATE pg_catalog."default",
       configuration_ts    timestamp(6) with time zone NOT NULL,
       configuration_value jsonb                       NOT NULL,
       ts                  timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT configuration_changes_pkey PRIMARY KEY (key, configuration_ts)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.configuration_changes OWNER to foglamp;


-- Statistics table
-- The table is used to keep track of the statistics for FogLAMP
CREATE TABLE foglamp.statistics (
       key         character(10)               NOT NULL COLLATE pg_catalog."default", -- Primary key, all uppercase
       description character varying(255)      NOT NULL,                              -- Description, in plan text
       value       bigint                      NOT NULL DEFAULT 0,                    -- Integer value, the statistics
       previous_value       bigint             NOT NULL DEFAULT 0,                    -- Integer value, the prev stat to be updated by metrics collector
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                -- Timestamp, updated at every change
       CONSTRAINT statistics_pkey PRIMARY KEY (key)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.statistics OWNER to foglamp;


-- Statistics history
-- Keeps history of the statistics in foglamp.statistics
-- The table is updated at startup
CREATE TABLE foglamp.statistics_history (
       id          bigint                      NOT NULL DEFAULT nextval('foglamp.statistics_history_id_seq'::regclass), 
       key         character(10)               NOT NULL COLLATE pg_catalog."default",                         -- Coumpund primary key, all uppercase
       history_ts  timestamp(6) with time zone NOT NULL,                                                      -- Compound primary key, the highest value of statistics.ts when statistics are copied here.
       value       bigint                      NOT NULL DEFAULT 0,                                            -- Integer value, the statistics
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),                                        -- Timestamp, updated at every change
       CONSTRAINT statistics_history_pkey PRIMARY KEY (key, history_ts)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.statistics_history OWNER to foglamp;


-- Resources table
CREATE TABLE foglamp.resources (
    id          bigint                 NOT NULL DEFAULT nextval('foglamp.resources_id_seq'::regclass),
    code        character(10)          NOT NULL COLLATE pg_catalog."default",
    description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
    CONSTRAINT  resources_pkey PRIMARY KEY (id)
         USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.resources OWNER to foglamp;
COMMENT ON TABLE foglamp.resources IS
'A resource and be anything that is available or can be done in FogLAMP. Examples: 
- Access to assets
- Access to readings
- Access to streams';

CREATE UNIQUE INDEX resource_ix1
    ON foglamp.resources USING btree (code COLLATE pg_catalog."default")
    TABLESPACE foglamp;


-- Roles table
CREATE TABLE foglamp.roles (
    id          integer                NOT NULL DEFAULT nextval('foglamp.roles_id_seq'::regclass),
    name        character varying(25)  NOT NULL COLLATE pg_catalog."default",
    description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
    CONSTRAINT  roles_pkey PRIMARY KEY (id)
        USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE)
  TABLESPACE foglamp;

ALTER TABLE foglamp.roles
    OWNER to foglamp;
COMMENT ON TABLE foglamp.roles
    IS 'Roles are a set of permissions that users inherit.';


CREATE UNIQUE INDEX roles_ix1
    ON foglamp.roles USING btree (name COLLATE pg_catalog."default")
    TABLESPACE foglamp;


-- Roles, Resources and Permssions table
CREATE TABLE foglamp.role_resource_permission (
       role_id     integer NOT NULL,
       resource_id integer NOT NULL,
       access      jsonb   NOT NULL DEFAULT '{}'::jsonb,
       CONSTRAINT role_resource_permission_pkey PRIMARY KEY (role_id, resource_id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT role_resource_permissions_fk1 FOREIGN KEY (role_id)
       REFERENCES foglamp.roles (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT role_resource_permissions_fk2 FOREIGN KEY (resource_id)
       REFERENCES foglamp.resources (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.role_resource_permission OWNER to foglamp;
COMMENT ON TABLE foglamp.role_resource_permission IS
'For each role there are resources associated, with a given permission.';

CREATE INDEX fki_role_resource_permissions_fk1
    ON foglamp.role_resource_permission USING btree (role_id)
    TABLESPACE foglamp;

CREATE INDEX fki_role_resource_permissions_fk2
    ON foglamp.role_resource_permission USING btree (resource_id)
    TABLESPACE foglamp;


-- Roles Assets Permissions table
CREATE TABLE foglamp.role_asset_permissions (
    role_id    integer NOT NULL,
    asset_id   integer NOT NULL,
    access     jsonb   NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT role_asset_permissions_pkey PRIMARY KEY (role_id, asset_id)
         USING INDEX TABLESPACE foglamp,
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
            ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.role_asset_permissions OWNER to foglamp;
COMMENT ON TABLE foglamp.role_asset_permissions IS
'Combination of roles, assets and access';

CREATE INDEX fki_role_asset_permissions_fk1
    ON foglamp.role_asset_permissions USING btree
    (role_id) TABLESPACE foglamp;

CREATE INDEX fki_role_asset_permissions_fk2
    ON foglamp.role_asset_permissions USING btree (asset_id)
    TABLESPACE foglamp;


-- Users table
CREATE TABLE foglamp.users (
       id            integer                NOT NULL DEFAULT nextval('foglamp.users_id_seq'::regclass),
       uid           character varying(80)  NOT NULL COLLATE pg_catalog."default",
       role_id       integer                NOT NULL,
       description   character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
       pwd           character varying(255) COLLATE pg_catalog."default",
       public_key    character varying(255) COLLATE pg_catalog."default",
       access_method smallint               NOT NULL DEFAULT 0,
          CONSTRAINT users_pkey PRIMARY KEY (id)
               USING INDEX TABLESPACE foglamp,
          CONSTRAINT users_fk1 FOREIGN KEY (role_id)
          REFERENCES foglamp.roles (id) MATCH SIMPLE
                  ON UPDATE NO ACTION
                  ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.users OWNER to foglamp;
COMMENT ON TABLE foglamp.users IS
'FogLAMP users table.
Authentication Method:
0 - Disabled
1 - PWD
2 - Public Key';

CREATE INDEX fki_users_fk1
    ON foglamp.users USING btree (role_id)
    TABLESPACE foglamp;

CREATE UNIQUE INDEX users_ix1
    ON foglamp.users USING btree (uid COLLATE pg_catalog."default")
    TABLESPACE foglamp;

-- User Login table
CREATE TABLE foglamp.user_logins (
       id      integer                     NOT NULL DEFAULT nextval('foglamp.user_logins_id_seq'::regclass),
       user_id integer                     NOT NULL,
       ip      inet                        NOT NULL,
       ts      timestamp(6) with time zone NOT NULL,
       CONSTRAINT user_logins_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT user_logins_fk1 FOREIGN KEY (user_id)
       REFERENCES foglamp.users (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.user_logins OWNER to foglamp;
COMMENT ON TABLE foglamp.user_logins IS
'List of logins executed by the users.';

CREATE INDEX fki_user_logins_fk1
    ON foglamp.user_logins USING btree (user_id)
    TABLESPACE foglamp;


-- User Resource Permissions table
CREATE TABLE foglamp.user_resource_permissions (
       user_id     integer NOT NULL,
       resource_id integer NOT NULL,
       access      jsonb NOT NULL DEFAULT '{}'::jsonb,
        CONSTRAINT user_resource_permissions_pkey PRIMARY KEY (user_id, resource_id)
             USING INDEX TABLESPACE foglamp,
        CONSTRAINT user_resource_permissions_fk1 FOREIGN KEY (user_id)
        REFERENCES foglamp.users (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION,
        CONSTRAINT user_resource_permissions_fk2 FOREIGN KEY (resource_id)
        REFERENCES foglamp.resources (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.user_resource_permissions OWNER to foglamp;
COMMENT ON TABLE foglamp.user_resource_permissions IS
'Association of users with resources and given permissions for each resource.';

CREATE INDEX fki_user_resource_permissions_fk1
    ON foglamp.user_resource_permissions USING btree (user_id)
    TABLESPACE foglamp;

CREATE INDEX fki_user_resource_permissions_fk2
    ON foglamp.user_resource_permissions USING btree (resource_id)
    TABLESPACE foglamp;


-- User Asset Permissions table
CREATE TABLE foglamp.user_asset_permissions (
       user_id    integer NOT NULL,
       asset_id   integer NOT NULL,
       access     jsonb NOT NULL DEFAULT '{}'::jsonb,
       CONSTRAINT user_asset_permissions_pkey PRIMARY KEY (user_id, asset_id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT user_asset_permissions_fk1 FOREIGN KEY (user_id)
       REFERENCES foglamp.users (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT user_asset_permissions_fk2 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.user_asset_permissions OWNER to foglamp;
COMMENT ON TABLE foglamp.user_asset_permissions IS
'Association of users with assets';

CREATE INDEX fki_user_asset_permissions_fk1
    ON foglamp.user_asset_permissions USING btree (user_id)
    TABLESPACE foglamp;

CREATE INDEX fki_user_asset_permissions_fk2
    ON foglamp.user_asset_permissions USING btree (asset_id)
    TABLESPACE foglamp;


-- List of scheduled Processes
CREATE TABLE foglamp.scheduled_processes (
  name   character varying(20)  NOT NULL, -- Name of the process
  script jsonb, -- Full path of the process
  CONSTRAINT scheduled_processes_pkey PRIMARY KEY (name)
       USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.scheduled_processes OWNER to foglamp;


-- List of schedules
CREATE TABLE foglamp.schedules (
  id                uuid                  NOT NULL, -- PK
  process_name      character varying(20) NOT NULL, -- FK process name
  schedule_name     character varying(20) NOT NULL, -- schedule name
  schedule_type     smallint              NOT NULL, -- 1 = timed, 2 = interval, 3 = manual,
                                                    -- 4 = startup
  schedule_interval interval,                       -- Repeat interval
  schedule_time     time,                           -- Start time
  schedule_day      smallint,                       -- ISO day 1 = Monday, 7 = Sunday
  exclusive         boolean not null default true,  -- true = Only one task can run
                                                    -- at any given time
  CONSTRAINT schedules_pkey PRIMARY KEY (id)
       USING INDEX TABLESPACE foglamp,
  CONSTRAINT schedules_fk1 FOREIGN KEY (process_name)
  REFERENCES foglamp.scheduled_processes (name) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.schedules OWNER to foglamp;


-- List of tasks
CREATE TABLE foglamp.tasks (
  id           uuid                        NOT NULL,               -- PK
  process_name character varying(20)       NOT NULL,               -- Name of the task
  state        smallint                    NOT NULL,               -- 1-Running, 2-Complete, 3-Cancelled, 4-Interrupted
  start_time   timestamp(6) with time zone NOT NULL DEFAULT now(), -- The date and time the task started
  end_time     timestamp(6) with time zone,                        -- The date and time the task ended
  reason       character varying(255),                             -- The reason why the task ended
  pid          int                         NOT NULL,               -- Linux process id
  exit_code    int,                                                -- Process exit status code (negative means exited via signal)
  CONSTRAINT tasks_pkey PRIMARY KEY (id)
       USING INDEX TABLESPACE foglamp,
  CONSTRAINT tasks_fk1 FOREIGN KEY (process_name)
  REFERENCES foglamp.scheduled_processes (name) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.tasks OWNER to foglamp;

