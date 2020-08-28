
sqlite3 ${DEFAULT_SQLITE_DB_READINGS_FILE} << EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_READINGS_FILE}' AS 'readings_1';

--drop table if exists readings_1.readings;

-- Readings table
-- This tables contains the readings for assets.
-- An asset can be a south with multiple sensor, a single sensor,
-- a software or anything that generates data that is sent to Fledge
CREATE TABLE IF NOT EXISTS readings_1.readings_1 (
    id         INTEGER                PRIMARY KEY AUTOINCREMENT,
    reading    JSON                        NOT NULL DEFAULT '{}',  -- The json object received
    user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')), -- UTC time
    ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW'))  -- UTC time
);

-- CREATE INDEX fki_readings_fk1
--    ON readings (asset_code);

delete from readings_1.readings;

CREATE TABLE readings_1.asset_reading_catalogue (
    table_id     INTEGER               PRIMARY KEY AUTOINCREMENT,
    db_id        INTEGER               NOT NULL,
    asset_code   character varying(50) NOT NULL
);

CREATE TABLE readings_1.configuration_readings (
    global_id         INTEGER
);




EOF


sqlite3 ${DEFAULT_SQLITE_DB_FILE} << EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge';

drop table if exists fledge.test;

create table fledge.test (
	id	bigint,
	key	character(5),
	description	character varying(255),
	data    JSON	
);

drop table if exists fledge.test2;

insert into fledge.test values (1, 'TEST1',  'A test row', '{ "json" : "test1" }');
delete from fledge.configuration;

CREATE TABLE IF NOT EXISTS fledge.configuration (
       key         character varying(255)      NOT NULL, -- Primary key
       display_name character varying(255)     NOT NULL, -- Display Name
       description character varying(255)      NOT NULL, -- Description, in plain text
       value       JSON                       NOT NULL DEFAULT '{}',          -- JSON object containing the configuration values
       ts          DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')),          -- Timestamp, updated at every change
       CONSTRAINT configuration_pkey PRIMARY KEY (key) );

create table fledge.test2 (
	id	bigint,
	key	char(5),
	description	character varying(255),
	data	json,
	ts	DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime'))
);

insert into fledge.test2 values (1, 'TEST1',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:26.622315');
insert into fledge.test2 values (2, 'TEST2',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:27.422315+00:00');
insert into fledge.test2 values (3, 'TEST3',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:28.622315+01:00');
insert into fledge.test2 values (4, 'TEST4',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:29.622315+01:00');
insert into fledge.test2 values (5, 'TEST5',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:15:00.622315+01:00');
insert into fledge.test2 values (6, 'TEST6',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:15:33.622315+01:00');
insert into fledge.test2 values (6, 'TEST7',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:16:20.622315+01:00');
insert into fledge.test2 values (8, 'TEST8',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 13:14:30.622315+08:00');
insert into fledge.test2 values (9, 'TEST9',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 14:14:30.622315-07:00');
insert into fledge.tyyest2 values (10, 'TEST10',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-11 12:14:30.622315+01');

EOF
