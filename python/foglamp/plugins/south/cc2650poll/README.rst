***********************************************
FogLAMP South SensorTag CC2650 Poll mode Plugin
***********************************************

This directory contains a plugin that pulls readings from SensorTag
CC2650 South device over Bluetooth connection. The readings are fetched for
Temperature, Presssure, Humidity and Motion Sensors.

To connect, the sensor needs to be on in discoverable mode and its MAC
address properly recorded in the Configuration.

For a single SensorTag CC2650 South device, use only one mode - either poll or
async, at a time. For this you will need to remove the relevant schedule from
schedules table.

The polling is done at fixed intervals which is configurable via "pollInterval"
configuration item.

The plugin initialisation is done with a timeout period which can be configured
via "connectionTimeout" configuration item.

The plugin shutdown method executes the remaining tasks, Ingest tasks to be
precise, before shutting down. It waits for a fixed time, configured via
"shutdownThreshold' configuration item before calling timeout.

Known issues:
=============
Since the plugin runs in a separate process and its shutdown is controlled by the
central FogLAMP server, pressing CTRL-C does not terminate the process properly.
