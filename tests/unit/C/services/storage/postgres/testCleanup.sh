psql -d foglamp << EOF
delete from foglamp.test;
drop table foglamp.test;
delete from foglamp.test2;
drop table foglamp.test2;
EOF
