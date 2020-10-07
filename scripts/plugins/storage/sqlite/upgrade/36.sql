-- Create packages table

DROP TABLE IF EXISTS fledge.packages;

CREATE TABLE fledge.packages (
             id                uuid                   NOT NULL, -- PK
             name              character varying(255) NOT NULL, -- Package name
             action            character varying(10) NOT NULL, -- APT actions:
                                                                -- list
                                                                -- install
                                                                -- purge
                                                                -- update
             status            INTEGER                NOT NULL, -- exit code
                                                                -- -1       - in-progress
                                                                --  0       - success
                                                                -- Non-Zero - failed
             log_file_uri      character varying(255) NOT NULL, -- Package Log file relative path
  CONSTRAINT packages_pkey PRIMARY KEY  ( id ) );
