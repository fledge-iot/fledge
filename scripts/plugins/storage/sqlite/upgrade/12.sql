DROP TABLE IF EXISTS foglamp.destinations;
DROP INDEX IF EXISTS foglamp.fki_streams_fk1;

-- Drops destination_id field from the table
BEGIN TRANSACTION;
DROP TABLE IF EXISTS foglamp.streams_old;
ALTER TABLE foglamp.streams RENAME TO streams_old;

CREATE TABLE foglamp.streams (
    id            INTEGER                      PRIMARY KEY AUTOINCREMENT,         -- Sequence ID
    description    character varying(255)      NOT NULL DEFAULT '',               -- A brief description of the stream entry
    properties     JSON                        NOT NULL DEFAULT '{}',             -- A generic set of properties
    object_stream  JSON                        NOT NULL DEFAULT '{}',             -- Definition of what must be streamed
    object_block   JSON                        NOT NULL DEFAULT '{}',             -- Definition of how the stream must be organised
    object_filter  JSON                        NOT NULL DEFAULT '{}',             -- Any filter involved in selecting the data to stream
    active_window  JSON                        NOT NULL DEFAULT '{}',             -- The window of operations
    active         boolean                     NOT NULL DEFAULT 't',              -- When false, all data to this stream stop and are inactive
    last_object    bigint                      NOT NULL DEFAULT 0,                -- The ID of the last object streamed (asset or reading, depending on the object_stream)
    ts             DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime'))); -- Creation or last update

INSERT INTO foglamp.streams
        SELECT
            id,
            description,
            properties,
            object_stream,
            object_block,
            object_filter,
            active_window,
            active,
            last_object,
            ts
        FROM foglamp.streams_old;

DROP TABLE foglamp.streams_old;
COMMIT;
