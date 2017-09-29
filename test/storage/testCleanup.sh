psql << EOF
delete from foglamp.test;
drop table foglamp.test;
EOF
