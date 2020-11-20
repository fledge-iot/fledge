--
-- Stores in which database/readings table the specific asset_code is stored
--
CREATE TABLE readings_1.asset_reading_catalogue (
    table_id     INTEGER               PRIMARY KEY AUTOINCREMENT,
    db_id        INTEGER               NOT NULL,
    asset_code   character varying(50) NOT NULL
);

CREATE TABLE readings_1.configuration_readings (
    global_id         INTEGER,                                                  -- Stores the last global Id used +1
                                                                                -- Updated at -1 when Fledge starts
                                                                                -- Updated at the the proper value when Fledge stops
    db_id_Last        INTEGER                                                   -- Latest database available
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


--
-- Force a calculation of the global id at the fledge starts
--
INSERT INTO readings_1.configuration_readings VALUES (-1, 0);

--
-- NULL is used to force the auto generation of the value starting from 1
-- db_is will be properly valued by the shell script
--
INSERT INTO readings_1.asset_reading_catalogue
    SELECT
        NULL,
        1,
        asset_code
    FROM readings.readings
    GROUP BY asset_code
    ORDER BY asset_code;

