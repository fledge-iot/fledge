.. Fledge Plugins

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. |here BT| raw:: html

   <a href="https://bugs.launchpad.net/snappy/+bug/1674509" target="_blank">here</a>


.. =============================================


Fledge makes extensive use of plugin components to extend the base functionality of the platform. In particular, plugins are used to extend the set of sensors and actuators that Fledge supports, the set of services to which Fledge will push accumulated data gathered from those sensors and the mechanism by which Fledge buffers data internally.

This chapter presents the plugins available for Fledge, how to write and use new plugins to support different sensors, protocols, historians and storage devices. It will guide you through the process and entry points that are required for the various different type of plugin.


Fledge Plugins
===============

In this version of Fledge you have three types of plugins:

- **South Plugins** - They are responsible for communication between Fledge and the sensors and actuators they support. Each instance of a Fledge South microservice will use a plugin for the actual communication to the sensors or actuators that that instance of the South microservice supports.
- **North Plugins** - They are responsible for taking reading data passed to them from the South bound service and doing any necessary conversion to the data and providing the protocol to send that converted data to a north-side task.
- **Storage Plugins** - They sit between the Storage microservice and the physical data storage mechanism that stores the Fledge configuration and readings data. Storage plugins differ from other plugins in that they interface to a storage system which is written in C/C++ rather than Python, however they share the same common attributes and entry points that the Python based plugins must support.


Plugins in this version of Fledge
----------------------------------

This version of Fledge provides the following plugins in the main repository:

+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| Type    | Name       | Initial    | Description                 | Availability               | Notes                                  |
|         |            | |br| Status|                             |                            |                                        |
+=========+============+============+=============================+============================+========================================+
| Storage | SQLite     | Enabled    | SQLite storage |br|         | Ubuntu: x86_64 |br|        |                                        |
|         |            |            | for data and metadata       | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |            |                             | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| Storage | Postgres   | Disabled   | PostgreSQL storage |br|     | Ubuntu: x86_64 |br|        |                                        |
|         |            |            | for data and metadata       | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |            |                             | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| North   | OMF        | Disabled   | OSIsoft Message Format |br| | Ubuntu: x86_64 |br|        | It works with PI Connector |br|        |
|         |            |            | sender to PI Connector |br| | Ubuntu Core: x86, ARM |br| | Relay OMF 1.2.X and 2.2                |
|         |            |            | Relay OMF                   | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+
| North   | OCS        | Disabled   | OSIsoft Message Format |br| | Ubuntu: x86_64 |br|        |                                        |
|         |            |            | sender to the OSIsoft  |br| | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |            | Cloud Service               | Raspbian                   |                                        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+


In addition to the plugins in the main repository, these plugins are also available:

+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| Type  | Name           | Repository                   | Description                           | Availability  | Notes                                  |
+=======+================+==============================+=======================================+===============+========================================+
| South | dht11pi        | fledge-south-dht11          | Wired DHT11 Sensor in polling mode    | Raspbian      |                                        |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| South | envirophat     | fledge-south-envirophat     | Enviro pHAT sensor set                | Raspbian                                               |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| South | openweathermap | fledge-south-openweathermap | Data pull from the OpenWeatherMap API | Ubuntu x86_64 |                                        |
|       |                |                              |                                       | Raspbian      |                                        |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| South | pt100          | fledge-south-pt100          | Wired PT100 temperature sensor        | Raspbian      |                                        |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| South | CoAP           | fledge-south-coap           | CoAP Listener                         | Ubuntu x86_64 |                                        |
|       |                |                              |                                       | Ubuntu Core   |                                        |
|       |                |                              |                                       | Raspbian      |                                        |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| South | CC2650POLL     | fledge-south--cc2650poll    | TI SensorTag CC2650 |br|              | Ubuntu x86_64 | It requires BLE support. |br|          |
|       |                |                              | in polling mode                       | Ubuntu Core   | There are issues with Ubuntu Core |br| |
|       |                |                              |                                       | Raspbian      | on ARM, reported |here BT|             |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| South | CC2650ASYN     | fledge-south-cc2650asyn     | TI SensorTag CC2650 |br|              | Ubuntu x86_64 | It requires BLE support. |br|          |
|       |                |                              | asynchronous |br|                     | Ubuntu Core   | There are issues with Ubuntu Core |br| |
|       |                |                              | (listening) mode                      | Raspbian      | on ARM, reported |here BT|             |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| South | HTTP_SOUTH     | fledge-south-http           | HTTP Listener                         | Ubuntu x86_64 |                                        |
|       |                |                              |                                       | Ubuntu Core   |                                        |
|       |                |                              |                                       | Raspbian      |                                        |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+
| North | HTTP           | fledge-north-http           | HTTP Sender                           | Ubuntu x86_64 |                                        |
|       |                |                              |                                       | Ubuntu Core   |                                        |
|       |                |                              |                                       | Raspbian      |                                        |
+-------+----------------+------------------------------+---------------------------------------+---------------+----------------------------------------+


Installing New Plugins
----------------------

As a general rule and unless the documentation states otherwise, plugins should be installed in two ways:

- When the plugin is available as **source code**, it should be installed when **Fledge is not running**. |br| This is the recommended method because you may want to manually move the plugin code into the right location where Fledge is installed, add pre-requisites and execute the REST commands necessary to start the plugin.
- When the plugin is available as **package**, it should be installed when **Fledge is running**. |br| This is the required method because the package executed pre and post-installation tasks that require Fledge to run. 

In general, Fledge must be restarted when a new plugin has been installed.

For example, this is the command to use to install the *OpenWeather* South plugin:

.. code-block:: console

  $ sudo systemctl status fledge.service
  ● fledge.service - LSB: Fledge
     Loaded: loaded (/etc/init.d/fledge; bad; vendor preset: enabled)
     Active: active (running) since Wed 2018-05-16 01:32:25 BST; 4min 1s ago
       Docs: man:systemd-sysv-generator(8)
     CGroup: /system.slice/fledge.service
             ├─13741 python3 -m fledge.services.core
             └─13746 /usr/local/fledge/services/storage --address=0.0.0.0 --port=40138

  May 16 01:36:09 ubuntu python3[13741]: Fledge[13741] INFO: scheduler: fledge.services.core.scheduler.scheduler: Process started: Schedule 'stats collection' process 'stats coll
                                         ['tasks/statistics', '--port=40138', '--address=127.0.0.1', '--name=stats collector']
  ...
  Fledge v1.3.1 running.
  Fledge Uptime:  266 seconds.
  Fledge records: 0 read, 0 sent, 0 purged.
  Fledge does not require authentication.
  === Fledge services:
  fledge.services.core
  === Fledge tasks:
  $
  $ sudo cp fledge-south-openweathermap-1.2-x86_64.deb /var/cache/apt/archives/.
  $ sudo apt install /var/cache/apt/archives/fledge-south-openweathermap-1.2-x86_64.deb
  Reading package lists... Done
  Building dependency tree
  Reading state information... Done
  Note, selecting 'fledge-south-openweathermap' instead of '/var/cache/apt/archives/fledge-south-openweathermap-1.2-x86_64.deb'
  The following packages were automatically installed and are no longer required:
    linux-headers-4.4.0-109 linux-headers-4.4.0-109-generic linux-headers-4.4.0-119 linux-headers-4.4.0-119-generic linux-headers-4.4.0-121 linux-headers-4.4.0-121-generic
    linux-image-4.4.0-109-generic linux-image-4.4.0-119-generic linux-image-4.4.0-121-generic linux-image-extra-4.4.0-109-generic linux-image-extra-4.4.0-119-generic
    linux-image-extra-4.4.0-121-generic
  Use 'sudo apt autoremove' to remove them.
  The following NEW packages will be installed
    fledge-south-openweathermap
  0 to upgrade, 1 to newly install, 0 to remove and 0 not to upgrade.
  Need to get 0 B/3,404 B of archives.
  After this operation, 0 B of additional disk space will be used.
  Selecting previously unselected package fledge-south-openweathermap.
  (Reading database ... 211747 files and directories currently installed.)
  Preparing to unpack .../fledge-south-openweathermap-1.2-x86_64.deb ...
  Unpacking fledge-south-openweathermap (1.2) ...
  Setting up fledge-south-openweathermap (1.2) ...
  openweathermap plugin installed.
  $
  $ fledge status
  Fledge v1.3.1 running.
  Fledge Uptime:  271 seconds.
  Fledge records: 36 read, 0 sent, 0 purged.
  Fledge does not require authentication.
  === Fledge services:
  fledge.services.core
  fledge.services.south --port=42066 --address=127.0.0.1 --name=openweathermap
  === Fledge tasks:
  $
