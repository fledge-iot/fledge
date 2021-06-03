----------------------------------------------------------------------
-- Copyright (c) 2020 OSIsoft, LLC
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
-- init_readings.sql
--
-- SQLite script to create the Fledge persistent Layer
--

-- NOTE:
--
-- This schema has to be used with Sqlite3 JSON1 extension
--
-- This script must be launched with sqlite3 command line tool:
--  sqlite3 /path/readings.db
--   > ATTACH DATABASE '/path/readings.db' AS 'readings'
--   > .read init_readings.sql
--   > .quit

----------------------------------------------------------------------
-- DDL CONVENTIONS
--
-- Tables:
-- * Names are in plural, terms are separated by _
-- * Columns are, when possible, not null and have a default value.
--
-- Columns:
-- id      : It is commonly the PK of the table, a smallint, integer or bigint.
-- xxx_id  : It usually refers to a FK, where "xxx" is name of the table.
-- code    : Usually an AK, based on fixed length characters.
-- ts      : The timestamp with microsec precision and tz. It is updated at
--           every change.

----------------------------------------------------------------------
-- SCHEMA CREATION
----------------------------------------------------------------------

-- Readings table
-- This tables contains the readings for assets.
-- An asset can be a south with multiple sensor, a single sensor,
-- a software or anything that generates data that is sent to Fledge
CREATE TABLE readings.readings (
    id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
    asset_code character varying(50)       NOT NULL,                         -- The provided asset code. Not necessarily located in the
                                                                             -- assets table.
    reading    JSON                        NOT NULL DEFAULT '{}',            -- The json object received
    user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),      -- UTC time
    ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))       -- UTC time
);

CREATE INDEX fki_readings_fk1
    ON readings (asset_code, user_ts desc);

CREATE INDEX readings_ix2
    ON readings (asset_code);

CREATE INDEX readings_ix3
    ON readings (user_ts);

