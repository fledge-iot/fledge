.. FogLAMP Plugins

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. |here BT| raw:: html

   <a href="https://bugs.launchpad.net/snappy/+bug/1674509" target="_blank">here</a>


.. =============================================


FogLAMP makes extensive use of plugin components to extend the base functionality of the platform. In particular, plugins are used to extend the set of sensors and actuators that FogLAMP supports, the set of services to which FogLAMP will push accumulated data gathered from those sensors and the mechanism by which FogLAMP buffers data internally.

This chapter presents the plugins available in FogLAMP, how to write and use new plugins to support different sensors, protocols, historians and storage devices. It will guide you through the process and entry points that are required for the various different type of plugin.


FogLAMP Plugins
===============

In this version of FogLAMP you have three types of plugins:

- **South Plugins** - They are responsible for communication between FogLAMP and the sensors and actuators they support. Each instance of a FogLAMP South microservice will use a plugin for the actual communication to the sensors or actuators that that instance of the South microservice supports.
- **North Plugins** - They are responsible for taking reading data passed to them from the South bound task and doing any necessary conversion to the data and providing the protocol to send that converted data to a north-side service.
- **Storage Plugins** - They sit between the Storage microservice and the physical data storage mechanism that stores the FogLAMP configuration and readings data. Storage plugins differ from other plugins in that they interface to a storage system which is written in C/C++ rather than Python, however they share the same common attributes and entry points that the Python based plugins must support.


Plugins in this version of FogLAMP
----------------------------------

This version of FogLAMP provides the following plugins in the main repository:

+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| Type    | Name       | Initial    | Description                 | Availability               | Notes                                  |
|         |            | |br| Status|                             |                            |                                        |
+=========+============+============+=============================+============================+========================================+
| Storage | SQLite     | Enabled    | SQLite storage |br|         | Ubuntu: x86 |br|           |                                        |
|         |            |            | for data and metadata       | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |            |                             | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| Storage | Postgres   | Disabled   | PostgreSQL storage |br|     | Ubuntu: x86 |br|           |                                        |
|         |            |            | for data and metadata       | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |            |                             | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | COAP       | Enabled    | CoAP Listener               | Ubuntu: x86 |br|           |                                        |
|         |            |            |                             | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |            |                             | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | CC2650POLL | Disabled   | TI SensorTag CC2650 |br|    | Ubuntu: x86 |br|           | It requires BLE support. |br|          |
|         |            |            | in polling mode             | Ubuntu Core: x86, ARM |br| | There are issues with Ubuntu Core |br| |
|         |            |            |                             | Raspbian                   | on ARM, reported |here BT|             |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | CC2650ASYN | Disabled   | TI SensorTag CC2650 |br|    | Ubuntu: x86 |br|           | It requires BLE support. |br|          |
|         |            |            | asynchronous |br|           | Ubuntu Core: x86, ARM |br| | There are issues with Ubuntu Core |br| |
|         |            |            | (listening) mode            | Raspbian                   | on ARM, reported |here BT|.            |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | HTTP_SOUTH | Enabled    | HTTP Listener               | Ubuntu: x86  |br|          |                                        |
|         |            |            |                             | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |            |                             | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| North   | OMF        | Disabled   | OSIsoft Message Format |br| | Ubuntu: x86 |br|           | It works with PI Connector |br|        |
|         |            |            | sender to PI Connector |br| | Ubuntu Core: x86, ARM |br| | Relay OMF 1.2.X and 2.2                |
|         |            |            | Relay OMF                   | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| North   | OCS        | Disabled   | OSIsoft Message Format |br| | Ubuntu: x86 |br|           |                                        |
|         |            |            | sender to the OSIsoft  |br| | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |            | Cloud Service               | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+


In addition to the plugins in the main repository, these plugins are also available:

+-------+-------------+---------------------------+---------------------------------------+--------------+
| Type  | Name        | Repository                | Description                           | Availability |
+=======+=============+===========================+=======================================+==============+
| South | dht11pi     | foglamp-south-dht11       | Wired DHT11 Sensor in polling mode    | Respbian     |
+-------+-------------+---------------------------+---------------------------------------+--------------+
| South | envirophat  | foglamp-south-envirophat  | Enviro pHAT sensor set                | Raspbian     |
+-------+-------------+---------------------------+---------------------------------------+--------------+
| South | openweather | foglamp-south-openweather | Data pull from the OpenWeatherMap API | Raspbian     |
+-------+-------------+---------------------------+---------------------------------------+--------------+
| South | pt100       | foglamp-south-pt100       | Wired PT100 temperature sensor        | Raspbian     |
+-------+-------------+---------------------------+---------------------------------------+--------------+

|br|

