
CREATE TABLE fledge.monitors (
             service       character varying(255) NOT NULL,
             monitor       character varying(80) NOT NULL,
             minimum       integer,
             maximum       integer,
             average       integer,
             samples       integer,
             ts            DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))
);

CREATE INDEX monitors_ix1
    ON monitors(service, monitor);
