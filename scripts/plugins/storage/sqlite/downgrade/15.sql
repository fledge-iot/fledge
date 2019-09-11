CREATE TABLE fledge.configuration_temp (
       key         character varying(255)      NOT NULL,                          -- Primary key
       description character varying(255)      NOT NULL,                          -- Description, in plain text
       value       JSON                        NOT NULL DEFAULT '{}',             -- JSON object containing the configuration values
       ts          DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')), -- Timestamp, updated at every change
       CONSTRAINT configuration_pkey PRIMARY KEY (key) );


INSERT INTO fledge.configuration_temp (key, description, value, ts) SELECT key, description, value, ts FROM fledge.configuration;

DROP TABLE fledge.configuration;

ALTER TABLE fledge.configuration_temp RENAME TO configuration;
