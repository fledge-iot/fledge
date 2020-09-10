.. Fledge Plugins

.. |br| raw:: html

   <br />

.. Images

.. Links
.. |available plugins| raw:: html

   <a href="../fledge_plugins.html">available plugins</a>

.. Links in new tabs

.. |here BT| raw:: html

   <a href="https://bugs.launchpad.net/snappy/+bug/1674509" target="_blank">here</a>


.. =============================================


Fledge makes extensive use of plugin components to extend the base functionality of the platform. In particular, plugins are used to;

  - Extend the set of sensors and actuators that Fledge supports.
  - Extend the set of services to which Fledge will push accumulated data gathered from those sensors.
  - The mechanism by which Fledge buffers data internally.
  - Filter plugins may be used to augment, edit or remove data as it flows through Fledge.
  - Rule plugins extend the rules that may trigger the delivery of notifications at the edge.
  - Notification delivery plugins allow for new delivery mechanisms to be integrated into Fledge.

This chapter presents the plugins that are bundled with Fledge, how to write and use new plugins to support different sensors, protocols, historians and storage devices. It will guide you through the process and entry points that are required for the various different types of plugin.

There are also numerous plugins that are available as separate packages or in separate repositories that may be used with Fledge.


Plugins
=======

In this version of Fledge you have six types of plugins:

- **South Plugins** - They are responsible for communication between Fledge and the sensors and actuators they support. Each instance of a Fledge South microservice will use a plugin for the actual communication to the sensors or actuators that that instance of the South microservice supports.
- **Storage Plugins** - They sit between the Storage microservice and the physical data storage mechanism that stores the Fledge configuration and readings data. Storage plugins differ from other plugins in that they are written exclusively in C/C++, however they share the same common attributes and entry points that the other filter must support.
- **Filter Plugins** - Filter plugins are used to modify data as it flows through Fledge. One or more filter plugins may compose a pipeline which modifies, either, data flowing out from the South ingress tasks into the Fledge Storage system, or out from Fledge storage into the North egress tasks.
- **Notification Rule Plugins** - Notification plugins evaluate data after it has been entered into the Fledge Storage, before it enters the northbound Filter pipeline(s). If the notification evaluates to True, a rule associated with the condition is executed. (Notification rules require installation of the optional notification service.)
- **Notification Delivery Plugins** - These plugins deliver a notification event; events, trigger "reason", and accompanying "message" are specified, and delivered to a given delivery channel (eg., email/sms/...). (Notification rules require installation of the optional notification service.)
- **North Plugins** - These plugins take data, originated by South service(s), optionally transformed by filters, optionally triggering notifications, and export those data to the outside world.

Fledge message contents
=======================
Information flows through fledge in "messages". Messages have a few "tags" which have well defined values. Messages may be extended to contain additional tags appropriate to particular plugins and data flows.

Most messages include:
+------------+-----------------+-------------------------------------------------------------------------------------------------------+
| Tag        | Type            | Description                                                                                           |
+============+=================+============+==========================================================================================+
| asset      | string          | Name under which this stream of data are placeed in Storage                                           |
+------------+-----------------+-------------------------------------------------------------------------------------------------------+
| ts         | string          | Timestamp when this asset was generated                                                               |
+------------+-----------------+-------------------------------------------------------------------------------------------------------+
| id         | string          | unique ID                                                                                             |
+------------+-----------------+-------------------------------------------------------------------------------------------------------+
| readings   | single dict |br|| {"user_ts": timestamp, <name>: <data-value>}  |br|                                                    |
|            |  -or-    |br|   |                                               |br|                                                    |
|            | json            | "data": "[{"user_ts": <timestamp1>; <name>: <data-value1>}, {"user_ts": <timestamp2>, <name>...]"     |
+------------+-----------------+-------------------------------------------------------------------------------------------------------+

Fledge plugin configuration
=======================
Different plugin types (eg., north/south/...) have required configuration entries

Required configuration entries include:
+------------------------+--------------------------+----------------------------------------------------------------------------------------------+
| Entry                  | Required by              | Description                                                                                  |
+========================+==========================+==============================================================================================+
| plugin                 | all                      | description: "<Describe plugin>" |br|                                                        |
|                        |                          | type: "string" |br|                                                                          |
|                        |                          | name: "<plugin name>" |br|                                                                   |
|                        |                          | readonly: "true"      |br|                                                                   |
+------------------------+--------------------------+----------------------------------------------------------------------------------------------+
| enable                 | filter                   | description: "<Describe plugin being enabled>" |br|                                          |
|                        | |br| notification        | type: "boolean"                                |br|                                          |
|                        | |br|notification delivery| default: "false"                               |br|                                          |
|                        |                          | displayName: "<name for UI display>"           |br|                                          |
|                        |                          | order: "<order of display in UI>"                                                            |
+------------------------+--------------------------+----------------------------------------------------------------------------------------------+
| asset                  | south                    | description: "<name of asset being monitored>" |br|                                          |
|                        | |br| notification        | type: "string"                                 |br|                                          |
|                        |                          | default: ""                                    |br|                                          |
|                        |                          | displayName: "<name for UI display>"           |br|                                          |
|                        |                          | mandatory: "true"                              |br|                                          |
|                        |                          | order: "<order of display in UI>"                                                            |
+------------------------+--------------------------+----------------------------------------------------------------------------------------------+
| source                 | north                    | description: "<Describe resource being forwarded>" |br|                                      |
|                        |                          | type: "enumeration"                                |br|                                      |
|                        |                          | options: ["readings", "statistics"]                |br|                                      |
|                        |                          | default: "readings"                                |br|                                      |
|                        |                          | displayName: "<name for UI display>"               |br|                                      |
|                        |                          | order: "<order of display in UI>"                                                            |
+------------------------+--------------------------+----------------------------------------------------------------------------------------------+
| applyFilter            | north                    | description: "<Describe plugin being enabled>"     |br|                                      |
|                        |                          | type: "boolean"                                    |br|                                      |
|                        |                          | default: "false"                                   |br|                                      |
|                        |                          | displayName: "<name for UI display>"               |br|                                      |
|                        |                          | order: "<order of display in UI>"                                                            |
+------------------------+--------------------------+----------------------------------------------------------------------------------------------+
| filterRule             | north                    | description: "<describe JQ north filter rule>"     |br|                                      |
|                        |                          | type: "string"                                     |br|                                      |
|                        |                          | default: "[]"                                      |br|                                      |
|                        |                          | displayName: "<name for UI display>"               |br|                                      |
|                        |                          | order: "<order of display in UI>"                                                            |
+------------------------+--------------------------+----------------------------------------------------------------------------------------------+

Fledge plugin methods
=======================
Different plugin types (eg., north/south/...) have common and distinct APIs they must export.

Required APIs include:
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| Entry                  | Required by     | Description                                                                                           |
+========================+=================+============+==========================================================================================+
| plugin_info            | all             | Returns the info needed to load the plugin (interface spec, type, etc.)                               |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_init            | all             | Takes the config values; one time initialization; returns opaque handle for this instance             |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_shutdown        | all             | Destroys plugin and related state                                                                     |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_reconfigure     | all             | Replaces existing configuration with new values; may need to call shutdown/init                       |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_ingest          | filter          | Provides data which is modified, then sent on to ingest callback                                      |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_eval            | notification    | Takes JSON asset document to eval; Returns True if should "notify"                                    |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_triggers        | notification    | Returns JSON asset document describing what notification triggers have fired                          |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_reason          | notification    | Takes JSON asset document describing why notifications have fired                                     |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_deliver         | notification    | Takes name/notification/trigger/message strings to be sent to notification target                     |
|                        | |br| delivery   |                                                                                                       |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_send            | north           | Provides data,input_ref to be sent to North plugin target                                             |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_start           | south           | Initiates async "pumping" of data (typically threaded)                                                |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+
| plugin_register_ingest | south           | Registers callback and ingest "ref" which receive new data as available                               |
+------------------------+-----------------+-------------------------------------------------------------------------------------------------------+




Existing plugins and plugin extensions
======================================
Fledge comes pre-loaded with a number of plugins. Additional plugins may be loaded from the standard Fledge collection, from third pary collections, or from code developed by users.


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
|         |            |            | sender to PI Connector |br| | Ubuntu Core: x86, ARM |br| | Relay OMF 1.2.X and 2.2. The plugin    |
|         |            |            | Relay OMF                   | Raspbian                   | also works against EDS and OCS.        |
+---------+------------+------------+-----------------------------+----------------------------+----------------------------------------+


In addition to the plugins in the main repository, there are many other plugins available in separate repositories, a list of the |available plugins| is maintained within this document.


Installing New Plugins
----------------------

As a general rule and unless the documentation states otherwise, plugins should be installed in two ways:

- When the plugin is available as **package**, it should be installed when **Fledge is running**. |br| This is the required method because the package executed pre and post-installation tasks that require Fledge to run. 
- When the plugin is available as **source code**, it should be installed when **Fledge is either running or not**. |br| You will want to manually move the plugin code into the right location where Fledge is installed, add pre-requisites and execute the REST commands necessary to start the plugin **after** you have started Fledge if it is not running when you start this process.

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

You may also install new plugins directly from within the Fledge GUI, however you will need to have setup your Linux machine to include the Fledge package repository in the list of repositories the Linux package manager searches for new packages.
