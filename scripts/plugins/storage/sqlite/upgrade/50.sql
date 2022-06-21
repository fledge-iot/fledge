-- The Schema Service table used to hold information about extension schemas
CREATE TABLE fledge.service_schema (
             name          character varying(255)        NOT NULL,
             service       character varying(255)        NOT NULL,
             version       integer                       NOT NULL,
             definition    JSON);
