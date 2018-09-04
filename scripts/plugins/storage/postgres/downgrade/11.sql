CREATE SEQUENCE foglamp.destinations_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE foglamp.destinations (
       id            integer                     NOT NULL DEFAULT nextval('foglamp.destinations_id_seq'::regclass),   -- Sequence ID
       type          smallint                    NOT NULL DEFAULT 1,                                                  -- Enum : 1: OMF, 2: Elasticsearch
       description   character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default", -- A brief description of the destination entry
       properties    jsonb                       NOT NULL DEFAULT '{ "streaming" : "all" }'::jsonb,                   -- A generic set of properties
       active_window jsonb                       NOT NULL DEFAULT '[ "always" ]'::jsonb,                              -- The window of operations
       active        boolean                     NOT NULL DEFAULT true,                                               -- When false, all streams to this destination stop and are inactive
       ts            timestamp(6) with time zone NOT NULL DEFAULT now(),                                              -- Creation or last update
       CONSTRAINT destination_pkey PRIMARY KEY (id) );

INSERT INTO foglamp.destinations ( id, description )
       VALUES (0, 'none' );

-- Add the constraint to the the table
BEGIN TRANSACTION;
DROP TABLE IF EXISTS foglamp.streams_old;
ALTER TABLE foglamp.streams RENAME TO streams_old;

ALTER TABLE foglamp.streams_old RENAME CONSTRAINT strerams_pkey TO strerams_pkey_old;

CREATE TABLE foglamp.streams (
       id             integer                     NOT NULL DEFAULT nextval('foglamp.streams_id_seq'::regclass),         -- Sequence ID
       destination_id integer                     NOT NULL ,                                                            -- FK to foglamp.destinations
       description    character varying(255)      NOT NULL DEFAULT ''::character varying COLLATE pg_catalog."default",  -- A brief description of the stream entry
       properties     jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- A generic set of properties
       object_stream  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Definition of what must be streamed
       object_block   jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Definition of how the stream must be organised
       object_filter  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- Any filter involved in selecting the data to stream
       active_window  jsonb                       NOT NULL DEFAULT '{}'::jsonb,                                         -- The window of operations
       active         boolean                     NOT NULL DEFAULT true,                                                -- When false, all data to this stream stop and are inactive
       last_object    bigint                      NOT NULL DEFAULT 0,                                                   -- The ID of the last object streamed (asset or reading, depending on the object_stream)
       ts             timestamp(6) with time zone NOT NULL DEFAULT now(),                                               -- Creation or last update
       CONSTRAINT strerams_pkey PRIMARY KEY (id),
       CONSTRAINT streams_fk1 FOREIGN KEY (destination_id)
       REFERENCES foglamp.destinations (id) MATCH SIMPLE
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

CREATE INDEX fki_streams_fk1 ON foglamp.streams USING btree (destination_id);