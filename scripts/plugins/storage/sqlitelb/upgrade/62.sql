
CREATE TABLE fledge.monitors (
	service		character varying(255) NOT NULL, 
	monitor 	character varying(80) NOT NULL,
	minimum		integer,
	maximum		integer,
	average		integer,
	samples		integer,
	timestamp    	DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW'))
);

CREATE INDEX monitor_ix1
    ON fledge.monitors(service, monitor);
