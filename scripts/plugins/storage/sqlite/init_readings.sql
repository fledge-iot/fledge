
-- Readings table
-- This tables contains the readings for assets.
-- An asset can be a south with multiple sensor, a single sensor,
-- a software or anything that generates data that is sent to Fledge
CREATE TABLE readings (
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

