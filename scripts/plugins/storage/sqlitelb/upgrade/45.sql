-- Create Control service support table

DROP TABLE IF EXISTS fledge.control_script;
DROP TABLE IF EXISTS fledge.control_acl;

-- Script management for control dispatch service
CREATE TABLE fledge.control_script (
             name          character varying(255)        NOT NULL,
             steps         JSON                          NOT NULL DEFAULT '{}',
             acl           character varying(255),
             CONSTRAINT    control_script_pkey           PRIMARY KEY (name) );

-- Access Control List Management for control dispatch service
CREATE TABLE fledge.control_acl (
             name          character varying(255)        NOT NULL,
             service       JSON                          NOT NULL DEFAULT '{}',
             url           JSON                          NOT NULL DEFAULT '{}',
             CONSTRAINT    control_acl_pkey              PRIMARY KEY (name) );

