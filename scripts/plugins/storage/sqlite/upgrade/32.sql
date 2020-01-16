--
-- DROP the column: read_key   uuid
--

CREATE TABLE new_readings(
    id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
    asset_code character varying(50)       NOT NULL,                         -- The provided asset code. Not necessarily located in the
                                                                             -- assets TABLE.
    reading    JSON                        NOT NULL DEFAULT '{}',            -- The json object received
    user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),      -- UTC time
    ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))       -- UTC time
);

INSERT INTO new_readings
    SELECT
        id,
        asset_code,
        reading,
        user_ts,
        ts
    FROM readings;

DROP INDEX fki_readings_fk1;
DROP INDEX readings_ix2;
DROP INDEX readings_ix3;

DROP TABLE readings;

ALTER TABLE new_readings rename to readings;

CREATE INDEX fki_readings_fk1
    ON readings (asset_code, user_ts desc);

CREATE INDEX readings_ix2
    ON readings (asset_code);

CREATE INDEX readings_ix3
    ON readings (user_ts);
