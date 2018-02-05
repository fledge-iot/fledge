#!/bin/bash

curl -s http://localhost:8081/foglamp/asset | jq -S '.'
