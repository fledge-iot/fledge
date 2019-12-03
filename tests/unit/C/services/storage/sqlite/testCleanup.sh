sqlite3 ${DEFAULT_SQLITE_DB_FILE} << EOF
ATTACH DATABASE '${DEFAULT_SQLITE_DB_FILE}' AS 'fledge';
delete from fledge.test;
drop table fledge.test;
delete from fledge.test2;
drop table fledge.test2;
EOF
