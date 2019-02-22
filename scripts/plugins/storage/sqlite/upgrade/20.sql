-- Create filters table
CREATE TABLE foglamp.filters (
             name        character varying(255)        NOT NULL,
             plugin      character varying(255)        NOT NULL,
       CONSTRAINT filter_pkey PRIMARY KEY( name ) );

-- Create filter_users table
CREATE TABLE foglamp.filter_users (
             name        character varying(255)        NOT NULL,
             user        character varying(255)        NOT NULL);

