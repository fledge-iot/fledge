#!/bin/sh
while true; do
rm -f readings.json
sh makeReadings.sh >readings.json
curl -X POST http://192.168.56.101:8080/storage/reading -d @readings.json
done
