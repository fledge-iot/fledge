-- FogLAMP expects to have foglamp.readings.user_ts in a precise fixed format
-- the upgrade updates the contents of the foglamp.readings table
-- to the handled format

-- Backup readings data
DROP TABLE IF EXISTS foglamp.readings_backup;

CREATE TABLE foglamp.readings_backup (
    id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
    asset_code character varying(50)       NOT NULL,                         -- The provided asset code. Not necessarily located in the
                                                                             -- assets table.
    read_key   uuid                        UNIQUE,                           -- An optional unique key used to avoid double-loading.
    reading    JSON                        NOT NULL DEFAULT '{}',            -- The json object received
    user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),      -- UTC time
    ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW'))       -- UTC time
);

INSERT INTO foglamp.readings_backup
          (id, asset_code, read_key, reading, user_ts, ts)
    SELECT id, asset_code, read_key, reading, user_ts, ts FROM foglamp.readings;

-- Apply user_ts changes
UPDATE foglamp.readings
  SET user_ts =
    CASE instr(user_ts,'.') -- Checks for the presence of sub-seconds
        WHEN 0  THEN
            user_ts || ".000000+00:00"
        ELSE
            -- Handles microseconds
            substr(user_ts,1, instr(user_ts,'.') -1 ) ||
            CASE -- Check for the presence of the timezone
                max (
                    instr(substr(user_ts,instr(user_ts,'.')+1,99),'+') -1,
                    instr(substr(user_ts,instr(user_ts,'.')+1,99),'-') -1
                )
                WHEN -1 THEN
                    -- No timezone
                    substr (
                        substr(user_ts,instr(user_ts,'.'),99) || "000000", 1, 7)
                    || "+00:00"
                ELSE
                    -- yes timezone - extract up to the timezone
                    substr (
                        "." || substr(user_ts, instr(user_ts, '.') + 1,
                                    max (
                                          instr(substr(user_ts,instr(user_ts,'.')+1,99),'+') -1,
                                          instr(substr(user_ts,instr(user_ts,'.')+1,99),'-') -1
                                      )
                        )
                        || "000000", 1, 7)
                    -- Handles timezone
                    ||  substr( substr(user_ts, instr(user_ts, '.') + 1),
                                max (
                                   instr(substr(user_ts,instr(user_ts,'.')+1,99),'+'),
                                   instr(substr(user_ts,instr(user_ts,'.')+1,99),'-')
                                )
                            ,99)
        END
    END;

