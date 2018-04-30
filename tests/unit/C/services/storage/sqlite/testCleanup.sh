sqlite3 ${DEFAULT_SQLITE_DB_FILE} << EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'foglamp';
delete from foglamp.test;
drop table foglamp.test;
delete from foglamp.test2;
drop table foglamp.test2;
EOF
