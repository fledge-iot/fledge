#!/bin/bash

curl -sk https://localhost:1995/foglamp/asset | jq -S '.'
