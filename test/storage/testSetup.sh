psql << EOF
drop table if exists foglamp.test;

create table foglamp.test (
	id	bigint,
	key	character(5),
	description	character varying(255),
	data	jsonb
);

insert into foglamp.test values (1, 'TEST1',  'A test row', '{ "json" : "test1" }');

delete from readings;
EOF
