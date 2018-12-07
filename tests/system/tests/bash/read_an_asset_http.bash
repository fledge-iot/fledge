#!/bin/bash

asset_id="${1/\//%2F}"

curl -s http://localhost:8081/foglamp/asset/${asset_id}


