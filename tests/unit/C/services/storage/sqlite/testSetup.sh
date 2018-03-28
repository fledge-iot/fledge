sqlite3 ${DEFAULT_SQLITE_DB_FILE} << EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'foglamp';

drop table if exists foglamp.test;

create table foglamp.test (
	id	bigint,
	key	character(5),
	description	character varying(255),
	data    JSON	
);

--drop table if exists foglamp.readings;
drop table if exists foglamp.test2;

insert into foglamp.test values (1, 'TEST1',  'A test row', '{ "json" : "test1" }');

-- Readings table
-- This tables contains the readings for assets.
-- An asset can be a south with multiple sensor, a single sensor,
-- a software or anything that generates data that is sent to FogLAMP
CREATE TABLE IF NOT EXISTS foglamp.readings (
    id         INTEGER                PRIMARY KEY AUTOINCREMENT,
    asset_code character varying(50)       NOT NULL,               -- The provided asset code. Not necessarily located in the
                                                                   -- assets table.
    read_key   uuid                        UNIQUE,                 -- An optional unique key used to avoid double-loading.
    reading    JSON                        NOT NULL DEFAULT '{}',  -- The json object received
    user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),
    ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))
);

-- CREATE INDEX fki_readings_fk1
--    ON readings (asset_code);

-- CREATE INDEX readings_ix1
--    ON readings (read_key);

delete from foglamp.readings;
delete from foglamp.configuration;

CREATE TABLE IF NOT EXISTS foglamp.configuration (
       key         character varying(255)      NOT NULL, -- Primary key
       description character varying(255)      NOT NULL,                              -- Description, in plain text
       value       JSON                       NOT NULL DEFAULT '{}',          -- JSON object containing the configuration values
       ts          DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),          -- Timestamp, updated at every change
       CONSTRAINT configuration_pkey PRIMARY KEY (key) );

create table foglamp.test2 (
	id	bigint,
	key	char(5),
	description	character varying(255),
	data	json,
	ts	DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))
);

insert into foglamp.test2 values (1, 'TEST1',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:26.622315+01:00');
insert into foglamp.test2 values (2, 'TEST2',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:27.422315+01:00');
insert into foglamp.test2 values (3, 'TEST3',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:28.622315+01:00');
insert into foglamp.test2 values (4, 'TEST4',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:29.622315+01:00');
insert into foglamp.test2 values (5, 'TEST5',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:15:00.622315+01:00');
insert into foglamp.test2 values (6, 'TEST6',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:15:33.622315+01:00');
insert into foglamp.test2 values (6, 'TEST7',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:16:20.622315+01:00');
insert into foglamp.test2 values (8, 'TEST8',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 13:14:30.622315+01:00');
insert into foglamp.test2 values (9, 'TEST9',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 14:14:30.622315+01:00');
insert into foglamp.tyyest2 values (10, 'TEST10',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-11 12:14:30.622315+01');

EOF
