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


CREATE SEQUENCE foglamp.clean_rules_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.clean_rules_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.cloud_send_rules_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.cloud_send_rules_id_seq OWNER TO foglamp;


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


CREATE SEQUENCE foglamp.stream_log_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.stream_log_id_seq OWNER TO foglamp;


CREATE SEQUENCE foglamp.stream_status_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
ALTER SEQUENCE foglamp.stream_status_id_seq OWNER TO foglamp;


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
    asset_code character varying(50),                                                                     -- Link with the assets table. If the value is NULL, the asset is not defined.
    read_key   uuid                        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid, -- A unique key used to avoid double-loading. Default with 0s is used when it is ignored.
    reading    jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                  -- The json object received
    user_ts    timestamp(6) with time zone NOT NULL DEFAULT now(),                                        -- The user timestamp extracted by the received message
    ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
    CONSTRAINT readings_pkey PRIMARY KEY (id)
         USING INDEX TABLESPACE foglamp,
    CONSTRAINT readings_fk1 FOREIGN KEY (asset_code)
    REFERENCES foglamp.assets (code) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION)
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
       id          integer                     NOT NULL DEFAULT nextval('foglamp.destinations_id_seq'::regclass),
       description character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
       properties  jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       address     inet                        NOT NULL DEFAULT '0.0.0.0'::inet,
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),
        CONSTRAINT destination_pkey PRIMARY KEY (id)
             USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.destinations OWNER to foglamp;
COMMENT ON TABLE foglamp.destinations IS
'Multiple destinations are allowed, for example multiple PI servers.';


-- Streams table
CREATE TABLE foglamp.streams (
       id             integer                     NOT NULL DEFAULT nextval('foglamp.streams_id_seq'::regclass),
       destination_id integer                     NOT NULL,
       description    character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
       properties     jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       filters        jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       reading_id     bigint                      NOT NULL,
       ts             timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT strerams_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT streams_fk1 FOREIGN KEY (destination_id)
       REFERENCES foglamp.destinations (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT streams_fk2 FOREIGN KEY (reading_id)
       REFERENCES foglamp.readings (id) MATCH SIMPLE
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

CREATE INDEX fki_streams_fk2
    ON foglamp.streams USING btree (reading_id)
    TABLESPACE foglamp;


-- Stream Assets table
CREATE TABLE foglamp.stream_assets (
       stream_id  integer NOT NULL,
       asset_id   integer NOT NULL,
       CONSTRAINT stream_assets_pkey PRIMARY KEY (stream_id, asset_id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT stream_assets_fk1 FOREIGN KEY (stream_id)
       REFERENCES foglamp.streams (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION,
       CONSTRAINT stream_asssets_fk2 FOREIGN KEY (asset_id)
       REFERENCES foglamp.assets (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.stream_assets OWNER to foglamp;
COMMENT ON TABLE foglamp.stream_assets IS
'Assets associated to a stream.';

CREATE INDEX fki_stream_asset_fk1
    ON foglamp.stream_assets USING btree (stream_id)
    TABLESPACE foglamp;

CREATE INDEX fki_stream_asssets_fk2
    ON foglamp.stream_assets USING btree (asset_id)
    TABLESPACE foglamp;


-- Strean Status table
CREATE TABLE foglamp.stream_status (
       id          integer                NOT NULL DEFAULT nextval('foglamp.stream_status_id_seq'::regclass),
       description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
       CONSTRAINT  stream_status_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.stream_status OWNER to foglamp;
COMMENT ON TABLE foglamp.stream_status IS
'Status of the streams.';


-- Stream Logs table
CREATE TABLE foglamp.stream_log (
    id         bigint                      NOT NULL DEFAULT nextval('foglamp.stream_log_id_seq'::regclass),
    stream_id  integer                     NOT NULL,
    status_id  integer                     NOT NULL,
    reading_id bigint                      NOT NULL,
    log        jsonb                       NOT NULL DEFAULT '{}'::jsonb,
    ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
    CONSTRAINT stream_log_pkey PRIMARY KEY (id)
         USING INDEX TABLESPACE foglamp,
    CONSTRAINT stream_log_fk1 FOREIGN KEY (status_id)
    REFERENCES foglamp.stream_status (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
    CONSTRAINT stream_log_fk2 FOREIGN KEY (stream_id)
    REFERENCES foglamp.streams (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
    CONSTRAINT stream_log_fk3 FOREIGN KEY (reading_id)
    REFERENCES foglamp.readings (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.stream_log OWNER to foglamp;
COMMENT ON TABLE foglamp.stream_log IS
'Information received from the destination regarding streams.';

CREATE INDEX fki_stream_log_fk1
    ON foglamp.stream_log USING btree (status_id)
    TABLESPACE foglamp;

CREATE INDEX fki_stream_log_fk2
    ON foglamp.stream_log USING btree (stream_id)
    TABLESPACE foglamp;

CREATE INDEX fki_stream_log_fk3
    ON foglamp.stream_log USING btree (reading_id)
    TABLESPACE foglamp;


-- Configuration table
CREATE TABLE foglamp.configuration (
       key   character(5)                NOT NULL COLLATE pg_catalog."default",
       value jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       ts    timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT configuration_pkey PRIMARY KEY (key)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.configuration OWNER to foglamp;
COMMENT ON TABLE foglamp.configuration IS
'The configuration in JSON format.
- The PK is a 5 CHAR code (standard is to keep it UPPERCASE and filled with _
- Values is a jsonb column
- ts is set by default with now().';


-- Configuration changes
CREATE TABLE foglamp.configuration_changes (
       key                 character(5)                NOT NULL COLLATE pg_catalog."default",
       configuration_ts    timestamp(6) with time zone NOT NULL,
       configuration_value jsonb                       NOT NULL,
       ts                  timestamp(6) with time zone NOT NULL DEFAULT now(),
                CONSTRAINT configuration_changes_pkey PRIMARY KEY (key, configuration_ts)
                     USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.configuration_changes OWNER to foglamp;
COMMENT ON TABLE foglamp.configuration_changes IS
'When a configuration changes, this table is used to store the previous configuration.
- The configuration key is stored in the key column
- The configuration timestamp is stored in the configuration_ts column
- The old value is stored in the configuration_value column';


-- Clean table
CREATE TABLE foglamp.clean_rules (
       id         integer                     NOT NULL DEFAULT nextval('foglamp.clean_rules_id_seq'::regclass),
       type       character(3)                NOT NULL COLLATE pg_catalog."default",                            -- DES (destination) | STR (stream) | PAS (parent asset) | ASS (asset)
       object_id  bigint,                                                                                       -- Since the rule may not refer to a specific object, this column can be NULL
       rule       jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                     -- With Type (sent|age|label|batch) and related values
       rule_check jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                     -- With Type (always|interval|instant)
       status     smallint                    NOT NULL DEFAULT 0,                                               -- 0:inactive 1:active 2:completed
       ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT clean_rules_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.clean_rules OWNER to foglamp;
COMMENT ON TABLE foglamp.clean_rules IS
'Rules defined to clean (purge) the data.';


-- Send data to the cloud table
CREATE TABLE foglamp.cloud_send_rules (
       id         integer                     NOT NULL DEFAULT nextval('foglamp.cloud_send_rules_id_seq'::regclass),
       stream_id  integer                     NOT NULL,
       rule       jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       rule_check jsonb                       NOT NULL DEFAULT '{}'::jsonb,
       ts         timestamp(6) with time zone NOT NULL DEFAULT now(),
       CONSTRAINT cloud_send_rules_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
       CONSTRAINT cloud_send_rules_fk1 FOREIGN KEY (stream_id)
       REFERENCES foglamp.streams (id) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

ALTER TABLE foglamp.cloud_send_rules OWNER to foglamp;
COMMENT ON TABLE foglamp.cloud_send_rules IS
'Rules defined to send data to the Cloud.';

CREATE INDEX fki_cloud_send_rules_fk1
    ON foglamp.cloud_send_rules USING btree (stream_id)
    TABLESPACE foglamp;


-- Resources table
CREATE TABLE foglamp.resources (
    id          bigint                 NOT NULL DEFAULT nextval('foglamp.resources_id_seq'::regclass),
    code        character(10)          NOT NULL COLLATE pg_catalog."default",
    description character varying(255) NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",
    CONSTRAINT  resources_pkey PRIMARY KEY (id)
         USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE )
  TABLESPACE foglamp;

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

