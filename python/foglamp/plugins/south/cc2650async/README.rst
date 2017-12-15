************************************************
FogLAMP South SensorTag CC2650 Async mode Plugin
************************************************

This directory contains a plugin that receives readings from SensorTag
CC2650 device over Bluetooth connection. The readings are received for
Temperature, Presssure, Humidity and Motion Sensors.

To connect, the sensor needs to be on in discoverable mode and its MAC
address properly recorded in the Configuration.

For a single SensorTag CC2650 device, use only one mode - either poll or
async, at a time. For this you will need to remove the relevant schedule from
schedules table.

In testing mode, set debug_cnt to a desired count of records. Currently it
has been set to 50. For production, it needs to be set to 0.

The plugin initialisation is done with a timeout period which can be configured
via "connectionTimeout" configuration item.

The plugin shutdown method executes the remaining tasks, Ingest tasks to be
precise, before shutting down. It waits for a fixed time, configured via
"shutdownThreshold' configuration item before calling timeout.

Known issues:
=============
Since the plugin runs in a separate process and its shutdown is controlled by the
central FogLAMP server, pressing CTRL-C does not terminate the process properly.

