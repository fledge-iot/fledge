CREATE TABLE fledge.monitors (
	service		character varying(255) NOT NULL,
	monitor 	character varying(80) NOT NULL,
	minimum		bigint,
	maximum		bigint,
	average		bigint,
	samples		bigint,
	timestamp   timestamp(6) with time zone NOT NULL DEFAULT now());

CREATE INDEX monitors_ix1
    ON fledge.monitors(service, monitor);
