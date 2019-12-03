psql -d fledge << EOF
delete from fledge.test;
drop table fledge.test;
delete from fledge.test2;
drop table fledge.test2;
EOF
