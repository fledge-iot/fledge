#!/bin/sh

 port=`curl -sX GET http://localhost:8081/fledge/service | cut -d ',' -f5 | cut -d ':' -f2`

 curl -X POST http://localhost:"$port"/storage/schema -d @PostStorageSchema.json

 curl -X POST http://localhost:"$port"/storage/schema/test1/table/table1 -d @PostTable.json

 curl -X PUT http://localhost:"$port"/storage/schema/test1/table/table1/query -d @PutQuery.json

 curl -X PUT http://localhost:"$port"/storage/schema/test1/table/table1 -d @PutTable.json

 curl -X GET http://localhost:"$port"/storage/schema/test1/table/table1 -d @GetTable.json

 curl -X PUT http://localhost:"$port"/storage/schema/test1/table/table1 -d @PutTableExpression.json

 curl -X DELETE http://localhost:"$port"/storage/schema/test1/table/table1 -d @DeleteRows.json




