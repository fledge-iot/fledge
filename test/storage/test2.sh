#!/bin/sh
while true; do
rm -f readings.json
sh makeReadings.sh >readings.json
curl -X POST http://localhost:8080/storage/reading -d @readings.json
done
