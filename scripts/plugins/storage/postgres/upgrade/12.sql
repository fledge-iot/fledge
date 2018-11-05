ALTER TABLE foglamp.streams DROP CONSTRAINT streams_fk1;
DROP TABLE IF EXISTS foglamp.destinations;
DROP INDEX IF EXISTS foglamp.fki_streams_fk1;

-- Drops destination_id field from the table
DROP TABLE IF EXISTS foglamp.streams_old;
ALTER TABLE foglamp.streams RENAME TO streams_old;

ALTER TABLE foglamp.streams_old RENAME CONSTRAINT strerams_pkey TO strerams_pkey_old;

CREATE TABLE foglamp.streams (
       id             integer                     NOT NULL DEFAULT nextval('foglamp.streams_id_seq'::regclass),         -- Sequence ID
       description    character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",  -- A brief description of the stream entry
       properties     jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- A generic set of properties
       object_stream  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Definition of what must be streamed
       object_block   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Definition of how the stream must be organised
       object_filter  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Any filter involved in selecting the data to stream
       active_window  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- The window of operations
       active         boolean                     NOT NULL DEFAULT true,                                                -- When false, all data to this stream stop and are inactive
       last_object    bigint                      NOT NULL DEFAULT 0,                                                   -- The ID of the last object streamed (asset or reading, depending on the object_stream)
       ts             timestamp(6) with time zone NOT NULL DEFAULT now(),                                               -- Creation or last update
       CONSTRAINT strerams_pkey PRIMARY KEY (id));

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
