##--------------------------------------------------------------------
## Copyright (c) 2017 DB Software, Inc.
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

##
## foglamp.sql
##
## PostgreSQL script to create the FogLAMP persistent Layer
##


# Create the foglamp user
DROP USER IF EXISTS foglamp;

CREATE USER foglamp WITH
  LOGIN
  SUPERUSER
  INHERIT
  CREATEDB
  CREATEROLE
  REPLICATION;


# Create the foglamp tablespace
DROP TABLESPACE IF EXITS foglamp;

CREATE TABLESPACE foglamp
  OWNER foglamp
  LOCATION '/var/lib/postgresql/9.6/main';


# Create the foglamp database
DROP DATABASE IF EXISTS foglamp;

CREATE DATABASE foglamp WITH
    OWNER = foglamp
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_GB.UTF-8'
    LC_CTYPE = 'en_GB.UTF-8'
    TABLESPACE = foglamp
    CONNECTION LIMIT = -1;


# Create the foglamp schema
DROP SCHEMA IF EXISTS foglamp;

CREATE SCHEMA foglamp
    AUTHORIZATION foglamp;


# Configuration table
DROP TABLE IF EXISTS foglamp.configuration;

CREATE TABLE foglamp.configuration (
       key   character(5) COLLATE pg_catalog."default" NOT NULL,
       value jsonb                                     NOT NULL,
       ts    timestamp without time zone DEFAULT now() NOT NULL,
       CONSTRAINT configuration_pkey PRIMARY KEY (key)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.configuration OWNER to foglamp;

COMMENT ON TABLE foglamp.configuration IS
'The configuration in JSON format.
- The PK is a 5 CHAR code (standard is to keep it UPPERCASE and filled with _
- Values is a jsonb column
- ts is set by default with now().';


# Configuration changes
DROP TABLE IF EXISTS foglamp.configuration_changes;

CREATE TABLE foglamp.configuration_changes (
       key                 character(5) COLLATE pg_catalog."default" NOT NULL,
       configuration_ts    timestamp without time zone               NOT NULL,
       configuration_value jsonb                                     NOT NULL,
       ts                  timestamp without time zone NOT NULL DEFAULT now(),
       CONSTRAINT configuration_changes_pkey PRIMARY KEY (key, configuration_ts)
            USING INDEX TABLESPACE foglamp )
  WITH ( OIDS = FALSE ) TABLESPACE foglamp;

ALTER TABLE foglamp.configuration_changes OWNER to foglamp;

COMMENT ON TABLE foglamp.configuration_changes IS
'When a configuration changes, this table is used to store the previous configuration.
- The configuration key is stored in the key column
- The configuration timestamp is stored in the configuration_ts column
- The old value is stored in the configuration_value column';


