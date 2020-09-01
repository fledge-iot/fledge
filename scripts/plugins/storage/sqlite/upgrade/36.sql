--
-- Stores in which database/readings table the specific asset_code is stored
--
CREATE TABLE readings_1.asset_reading_catalogue (
    table_id     INTEGER               PRIMARY KEY AUTOINCREMENT,
    db_id        INTEGER               NOT NULL,
    asset_code   character varying(50) NOT NULL
);

-- Stores the last global Id used +1
-- Updated at -1 when Fledge starts
-- Updated at the the proper value when Fledge stops
CREATE TABLE readings_1.configuration_readings (
    global_id         INTEGER
);

-- Readings table
-- This tables contains the readings for assets.
-- An asset can be a south with multiple sensor, a single sensor,
-- a software or anything that generates data that is sent to Fledge
CREATE TABLE readings_1.readings_1 (
    id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
    reading    JSON                        NOT NULL DEFAULT '{}',            -- The json object received
    user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),      -- UTC time
    ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))       -- UTC time
);

CREATE INDEX readings_1.readings_1_ix3
    ON readings_1 (user_ts);


-- Upgrade - copy all the content of the readings.readings  table into readings_1.readings_1
INSERT INTO readings_1.configuration_readings VALUES (-1);

--// FIXME_I:
--
-- NULL is used to force the auto generation of the value starting from 1
--
INSERT INTO readings_1.asset_reading_catalogue
    SELECT
        NULL,
        1,
        asset_code
    FROM readings.readings
    WHERE asset_code in ('rand_1','rand_2')
    GROUP BY asset_code;

INSERT INTO readings_1.asset_reading_catalogue
    SELECT
        NULL,
        2,
        asset_code
    FROM readings.readings
    WHERE asset_code in ('rand_3')
    GROUP BY asset_code;


-- INSERT INTO readings_1.readings_1
--     SELECT
--         id,
--         reading,
--         user_ts,
--         ts
--     FROM readings.readings;


--// FIXME_I:
--DROP TABLE readings.readings;

