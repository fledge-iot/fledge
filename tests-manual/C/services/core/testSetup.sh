#!/bin/sh

echo "Starting FogLAMP Core on port ${foglamp_core_port} ..."
./build/foglamp-core $foglamp_core_port &

sleep 2

echo "Starting FogLAMP Storage Service, registering to FogLAMP Core"
$FOGLAMP_ROOT/services/storage --address=127.0.0.1 --port=$foglamp_core_port

sleep 2

