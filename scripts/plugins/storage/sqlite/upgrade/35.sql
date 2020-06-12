
-- Upgrade - copy all the content of the fledge.readings table into readings.readings

CREATE TABLE readings.readings (
    id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
    asset_code character varying(50)       NOT NULL,                         -- The provided asset code. Not necessarily located in the
                                                                             -- assets table.
    reading    JSON                        NOT NULL DEFAULT '{}',            -- The json object received
    user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),      -- UTC time
    ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))       -- UTC time
);

INSERT INTO readings.readings SELECT * FROM fledge.readings;

CREATE INDEX readings.fki_readings_fk1
    ON readings  (asset_code, user_ts desc);

CREATE INDEX readings.readings_ix2
    ON readings (asset_code);

CREATE INDEX readings.readings_ix3
    ON readings (user_ts);


DROP TABLE fledge.readings;


