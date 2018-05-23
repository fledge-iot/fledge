psql -d foglamp << EOF
drop table if exists foglamp.test;

create table foglamp.test (
	id	bigint,
	key	character(5),
	description	character varying(255),
	data	jsonb
);

insert into foglamp.test values (1, 'TEST1',  'A test row', '{ "json" : "test1" }');

delete from foglamp.readings;

create table foglamp.test2 (
	id	bigint,
	key	character(5),
	description	character varying(255),
	data	jsonb,
	ts    timestamp(6) with time zone NOT NULL DEFAULT now()
);

insert into foglamp.test2 values (1, 'TEST1',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:26.622315+01');
insert into foglamp.test2 values (2, 'TEST2',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:27.422315+01');
insert into foglamp.test2 values (3, 'TEST3',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:28.622315+01');
insert into foglamp.test2 values (4, 'TEST4',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:14:29.622315+01');
insert into foglamp.test2 values (5, 'TEST5',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:15:00.622315+01');
insert into foglamp.test2 values (6, 'TEST6',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:15:33.622315+01');
insert into foglamp.test2 values (6, 'TEST7',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 12:16:20.622315+01');
insert into foglamp.test2 values (8, 'TEST8',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 13:14:30.622315+01');
insert into foglamp.test2 values (9, 'TEST9',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-10 14:14:30.622315+01');
insert into foglamp.test2 values (10, 'TEST10',  'A test row', '{ "prop1" : "test1", "obj1" : { "p1" : "v1","p2" : "v2"} }', '2017-10-11 12:14:30.622315+01');

EOF
