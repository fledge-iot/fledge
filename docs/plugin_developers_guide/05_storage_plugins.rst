.. Storage Plugins

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. =============================================


Storage Plugins
===============

Storage plugins are used to interact with the Storage Microservice and provide the persistent storage of information for Fledge. 

The current version of Fledge comes with three storage plugins:

- The **SQLite plugin**: this is the default plugin and it is used for general purpose storage on constrained devices.
- The **SQLite In Memory plugin**: this plugin can be used in conjunction with one of the other storage plugins and will provide an in memory storage system for reading data only. Configuration data is stored using the *SQLite* or *PostgreSQL* plugins.
- The **PostgreSQL plugin**: this plugin can be set on request (or it can be built as a default plugin from source) and it is used for a more significant demand of storage on relatively larger systems.


Data and Metadata
-----------------

Persistency is split in two blocks:

- **Metadata persistency**: it refers to the storage of metadata for Fledge, such as the configuration of the plugins, the scheduling of jobs and tasks and the the storage of statistical information.
- **Data persistency**: it refers to the storage of data collected from sensors and devices by the South microservices. The *SQLite In Memory* plugin is an example of a storage plugin designed to store only the data.

In the current implementation of Fledge, metadata and data use the same Storage plugin by default. Administrators can select different plugins for these two categories of data, with the most common configuration of this type to use the SQLite In Memory storage service for data and SQLite for the metadata. This is set by editing the storage configuration file. Currently there is no interface within Fledge to change the storage configuration.

The storage configuration file is stored in the Fledge data directory as etc/storage.json, the default storage configuration file is

.. code-block:: JSON

  {
    "plugin": {
      "value": "sqlite",
      "description": "The main storage plugin to load"
    },
    "readingPlugin": {
      "value": "",
      "description": "The storage plugin to load for readings data. If blank the main storage plugin is used."
    },
    "threads": {
      "value": "1",
      "description": "The number of threads to run"
    },
    "managedStatus": {
      "value": "false",
      "description": "Control if Fledge should manage the storage provider"
    },
    "port": {
      "value": "0",
      "description": "The port to listen on"
    },
    "managementPort": {
      "value": "0",
      "description": "The management port to listen on."
    }
  }

This sets the storage plugin to use as the *SQLite* plugin and leaves the *readingPlugin* blank. If the *readingPlugin* is blank then readings will be stored via the main plugin, if it is populated then a separate plugin will be used to store the readings. As an example, to store the readings in the *SQLite In Memory* plugin the storage.json file would be

.. code-block:: JSON

  {
    "plugin": {
      "value": "sqlite",
      "description": "The main storage plugin to load"
    },
    "readingPlugin": {
      "value": "sqlitememory",
      "description": "The storage plugin to load for readings data. If blank the main storage plugin is used."
    },
    "threads": {
      "value": "1",
      "description": "The number of threads to run"
    },
    "managedStatus": {
      "value": "false",
      "description": "Control if Fledge should manage the storage provider"
    },
    "port": {
      "value": "0",
      "description": "The port to listen on"
    },
    "managementPort": {
      "value": "0",
      "description": "The management port to listen on."
    }
  }

Fledge must be restarted for changes to the storage.json file to take effect.

In addition to the definition of the plugins to use, the storage.json file also has a number of other configuration options for the storage service.

- **threads**: The number of threads to use to accept incoming REST requests. This is normally set to 1, increasing the number of threads has minimal impact on performance in normal circumstances.

- **managedStatus**: This configuration option allows Fledge to manage the underlying storage system. If, for example you used a database server and you wished Fledge to start and stop that server as part of the Fledge start up and shut down procedure you would set this option to "true".

- **port**: This option can be used to make the storage service listen on a fixed port. This is normally not required, but can be used for diagnostic purposes.

- **managementPort**: As with *port* above this can be used for diagnostic purposes to fix the management API port for the storage service.

Common Elements for Storage Plugins
-----------------------------------

In designing the Storage API and plugins, we have first of all considered that there may be a large number of use cases for data and metadata persistence, therefore we have designed a flexible architecture that poses very few limitations. In practice, this means that developers can build their own Storage plugin and they can rely on anything they want to use as persistent storage. They can use a memory structure, or even a pass-through library, a file, a message queue system, a time series database, a relational database, NoSQL or something else.

After having praised the flexibility of the Storage plugins, let's provide guidelines about the basic functionality they should provide, bearing in mind that such functionality may not be relevant for some use cases.

- **Metadata persistency**: As mentioned before, one of the main reasons to use a Storage plugin is to safely store the configuration of the Fledge components. Since the configuration must survive to a system crash or reboot, it is fair to say that such information should be stored in one or more files or in a database system.
- **Data buffering**: The second most important feature of a Storage plugin is the ability to buffer (or store) data coming from the outside world, typically from the South microservices. In some cases this feature may not be necessary, since administrators may want to send data to other systems as soon as possible, using a North task of microservice. Even in situations where data can be sent up North instantaneously, you should consider these scenarios:

  - Fledge may be installed in areas where the network is unreliable. The North plugins will provide the logic of retrying to gain connectivity and resending data when the connection has been lost in the middle of the transfer operations.
  - North services may rely on the use of networks that provide time windows to operate. 
  - Historians and other systems may work better when data is transferred in blocks instead of a constant streaming.

- **Data purging**: Data may persist for the time needed by any specific use case, but it is pretty common that after a while (it can be seconds or minutes, but also day or months) data is no longer needed in Fledge. For this reason, the Storage plugin is able to purge data. Purging may be by time or by space usage, in conjunction with the fact that data may have been already transferred to other systems.

- **Data backup/restore**: Data, but especially metadata (i.e. configuration), can be backed up and stored safely on other systems. In case of crash and recovery, the same data may be restored into Fledge. Fledge provides a set of generic API to execute backup and restore operations.


