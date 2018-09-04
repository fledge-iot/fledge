CREATE TABLE foglamp.destinations (
    id            INTEGER                     PRIMARY KEY AUTOINCREMENT,                  -- Sequence ID
    type          smallint                    NOT NULL DEFAULT 1,                         -- Enum : 1: OMF, 2: Elasticsearch
    description   character varying(255)      NOT NULL DEFAULT '',                        -- A brief description of the destination entry
    properties    JSON                        NOT NULL DEFAULT '{ "streaming" : "all" }', -- A generic set of properties
    active_window JSON                        NOT NULL DEFAULT '[ "always" ]',            -- The window of operations
    active        boolean                     NOT NULL DEFAULT 't',                       -- When false, all streams to this destination stop and are inactive
    ts            DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')));         -- Creation or last update

INSERT INTO foglamp.destinations ( id, description )
       VALUES (0, 'none' );

-- Add the constraint to the the table
BEGIN TRANSACTION;
DROP TABLE IF EXISTS foglamp.streams_old;
ALTER TABLE foglamp.streams RENAME TO streams_old;

CREATE TABLE foglamp.streams (
    id            INTEGER                      PRIMARY KEY AUTOINCREMENT,         -- Sequence ID
    destination_id integer                     NOT NULL,                          -- FK to foglamp.destinations
    description    character varying(255)      NOT NULL DEFAULT '',               -- A brief description of the stream entry
    properties     JSON                        NOT NULL DEFAULT '{}',             -- A generic set of properties
    object_stream  JSON                        NOT NULL DEFAULT '{}',             -- Definition of what must be streamed
    object_block   JSON                        NOT NULL DEFAULT '{}',             -- Definition of how the stream must be organised
    object_filter  JSON                        NOT NULL DEFAULT '{}',             -- Any filter involved in selecting the data to stream
    active_window  JSON                        NOT NULL DEFAULT '{}',             -- The window of operations
    active         boolean                     NOT NULL DEFAULT 't',              -- When false, all data to this stream stop and are inactive
    last_object    bigint                      NOT NULL DEFAULT 0,                -- The ID of the last object streamed (asset or reading, depending on the object_stream)
    ts             DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')), -- Creation or last update
    CONSTRAINT streams_fk1 FOREIGN KEY (destination_id)
    REFERENCES destinations (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION );

INSERT INTO foglamp.streams
        SELECT
            id,
            0,
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

CREATE INDEX fki_streams_fk1 ON streams (destination_id);
