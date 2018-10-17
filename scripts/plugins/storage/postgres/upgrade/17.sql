-- Create plugin_data table
-- Persist plugin data in the storage
CREATE TABLE IF NOT EXISTS foglamp.plugin_data (
        key     character varying(255)    NOT NULL,
        data    JSON                      NOT NULL DEFAULT '{}',
        CONSTRAINT plugin_data_pkey PRIMARY KEY (key) );
