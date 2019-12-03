#!/bin/sh

echo "Starting Fledge Core on port ${fledge_core_port} ..."
./build/fledge-core $fledge_core_port &

sleep 2

echo "Starting Fledge Storage Service, registering to Fledge Core"
$FLEDGE_ROOT/services/storage --address=127.0.0.1 --port=$fledge_core_port

sleep 2

