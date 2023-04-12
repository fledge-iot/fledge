-- Create SEQUENCE for control_source
CREATE SEQUENCE fledge.control_source_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

-- Create control_source table
CREATE TABLE fledge.control_source (
             cpsid            integer                     NOT NULL DEFAULT nextval('fledge.control_source_id_seq'::regclass),     -- auto source id
             name             character  varying(40)      NOT NULL                                                          ,     -- source name
             description      character  varying(120)     NOT NULL                                                          ,     -- source description
             CONSTRAINT       control_source_pkey         PRIMARY KEY (cpsid)
            );

-- Create SEQUENCE for control_destination
CREATE SEQUENCE fledge.control_destination_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

-- Create control_destination table
CREATE TABLE fledge.control_destination (
             cpdid            integer                     NOT NULL DEFAULT nextval('fledge.control_destination_id_seq'::regclass),  -- auto destination id
             name             character  varying(40)      NOT NULL                                                               ,  -- destination name
             description      character  varying(120)     NOT NULL                                                               ,  -- destination description
             CONSTRAINT       control_destination_pkey    PRIMARY KEY (cpdid)
            );

-- Create SEQUENCE for control_pipelines
CREATE SEQUENCE fledge.control_pipelines_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

-- Create control_pipelines table
CREATE TABLE fledge.control_pipelines (
             cpid             integer                     NOT NULL DEFAULT nextval('fledge.control_pipelines_id_seq'::regclass),  -- control pipeline id
             name             character  varying(255)     NOT NULL                                                             ,  -- control pipeline name
             stype            integer                                                                                          ,  -- source type id from control_source table
             sname            character  varying(80)                                                                           ,  -- source name from control_source table
             dtype            integer                                                                                          ,  -- destination type id from control_destination table
             dname            character  varying(80)                                                                           ,  -- destination name from control_destination table
             enabled          boolean                     NOT NULL DEFAULT FALSE                                               ,  -- false = A given pipeline is disabled by default
             execution        character  varying(20)      NOT NULL DEFAULT  'shared'                                           ,  -- pipeline will be executed as with shared execution model by default
             CONSTRAINT       control_pipelines_pkey      PRIMARY KEY (cpid)
             );

-- Create SEQUENCE for control_filters
CREATE SEQUENCE fledge.control_filters_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

-- Create control_filters table
CREATE TABLE fledge.control_filters (
             fid              integer                          NOT NULL DEFAULT nextval('fledge.control_filters_id_seq'::regclass),  -- auto filter id
             cpid             integer                          NOT NULL                                                           ,  -- control pipeline id
             forder           integer                          NOT NULL                                                           ,  -- filter order
             fname            character  varying(255)          NOT NULL                                                           ,  -- Name of the filter instance
             CONSTRAINT       control_filters_pkey             PRIMARY KEY (fid)                                                  ,
             CONSTRAINT       control_filters_fk1              FOREIGN KEY (cpid) REFERENCES fledge.control_pipelines (cpid)  MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION
             );

-- Insert predefined entries for Control Source
DELETE FROM fledge.control_source;
INSERT INTO fledge.control_source ( name, description )
     VALUES ('Any', 'Any source.'),
            ('Service', 'A named service in source of the control pipeline.'),
            ('API', 'The control pipeline source is the REST API.'),
            ('Notification', 'The control pipeline originated from a notification.'),
            ('Schedule', 'The control request was triggered by a schedule.'),
            ('Script', 'The control request has come from the named script.');

-- Insert predefined entries for Control Destination
DELETE FROM fledge.control_destination;
INSERT INTO fledge.control_destination ( name, description )
     VALUES ('Service', 'A name of service that is being controlled.'),
            ('Asset', 'A name of asset that is being controlled.'),
            ('Script', 'A name of script that will be executed.'),
            ('Broadcast', 'No name is applied and pipeline will be considered for any control writes or operations to broadcast destinations.');
