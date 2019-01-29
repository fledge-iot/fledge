CREATE TABLE new_readings (
    id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
    asset_code character varying(50)       NOT NULL,                         -- The provided asset code.  Not necessarily located in the
                                                                             -- assets table.
    read_key   uuid                        UNIQUE,                           -- An optional unique key us ed to avoid double-loading.
    reading    JSON                        NOT NULL DEFAULT '{}',            -- The json object received
    user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),      -- UTC time
    ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))       -- UTC time
);

insert into new_readings select * from readings;

drop index fki_readings_fk1;
drop index readings_ix1;
drop index readings_ix2;
drop index readings_ix3;
drop table readings;

alter table new_readings rename to readings;

CREATE INDEX fki_readings_fk1
    ON readings (asset_code, user_ts desc);

CREATE INDEX readings_ix1
    ON readings (read_key);

CREATE INDEX readings_ix2
    ON readings (asset_code);

CREATE INDEX readings_ix3
    ON readings (user_ts);
