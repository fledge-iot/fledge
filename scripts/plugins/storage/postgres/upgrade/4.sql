-- Create the configuration category_children table
CREATE TABLE foglamp.category_children (
       parent	character varying(255)	NOT NULL,
       child	character varying(255)	NOT NULL,
       CONSTRAINT config_children_pkey PRIMARY KEY (parent, child) );
