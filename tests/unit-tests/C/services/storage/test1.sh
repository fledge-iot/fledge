curl -X PUT http://192.168.56.101:8080/storage/table/configuration/query -d @payload1.json
curl -X GET http://192.168.56.101:8080/storage/table/configuration?key=COAP_CONF
curl -X GET http://192.168.56.101:8080/storage/table/configuration
curl -X POST http://192.168.56.101:8080/storage/table/statistics_history -d @payload2.json
curl -X GET http://192.168.56.101:8080/storage/table/statistics_history?key=Mark
curl -X PUT http://192.168.56.101:8080/storage/table/statistics_history -d @payload3.json
curl -X GET http://192.168.56.101:8080/storage/table/log?code=LOGGN
curl -X PUT http://192.168.56.101:8080/storage/table/log -d @payload4.json
curl -X GET http://192.168.56.101:8080/storage/reading?id=1&count=1000
curl -X PUT http://192.168.56.101:8080/storage/reading/query -d @payload5.json
curl -X POST http://192.168.56.101:8080/storage/reading -d @payload6.json
curl -X PUT http://192.168.56.101:8080/storage/table/statistics_history/query -d @payload7.json
curl -X PUT http://192.168.56.101:8080/storage/table/statistics_history/query -d @payload8.json
curl -X PUT http://192.168.56.101:8080/storage/table/statistics_history/query -d @payload9.json
