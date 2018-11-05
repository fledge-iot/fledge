.. Storage Plugins

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. =============================================


Storage Plugins
===============

Storage plugins are used to interact with the Storage Microservice and provide the persistent storage of information for FogLAMP. 

The current version of FogLAMP comes with two storage plugins:

- The **SQLite plugin**: this is the default plugin and it is used for general purpose storage on constrained devices.
- The **PostgreSQL plugin**: this plugin can be set on request (or it can be built as a default plugin from source) and it is used for a more significant demand of storage on relatively larger systems.


Data and Metadata
-----------------

Persistency is split in two blocks:

- **Metadata persistency**: it refers to the storage of metadata for FogLAMP, such as the configuration of the plugins, the scheduling of jobs and tasks and the the storage of statistical information.
- **Data persistency**: it refers to the storage of data collected from sensors and devices by the South microservices.

In the current implementation of FogLAMP, metadata and data use the same Storage plugin. In future implementations, administrators will be able to select different plugins.


Common Elements for Storage Plugins
-----------------------------------

In designing the Storage API and plugins, we have first of all considered that there may be a large number of use cases for data and metadata persistence, therefore we have designed a flexible architecture that poses very few limitations. In practice, this means that developers can build their own Storage plugin and they can rely on anything they want to use as persistent storage. They can use a memory structure, or even a pass-through library, a file, a message queue system, a time series database, a relational database, NoSQL or something else.

After having praised the flexibility of the Storage plugins, let's provide guidelines about the basic functionality they should provide, bearing in mind that such functionality may not be relevant for some use cases.

- **Metadata persistency**: As mentioned before, one of the main reasons to use a Storage plugin is to safely store the configuration of the FogLAMP components. Since the configuration must survive to a system crash or reboot, it is fair to say that such information should be stored in one or more files or in a database system.
- **Data buffering**: The second most important feature of a Storage plugin is the ability to buffer (or store) data coming from the outside world, tipically from the South microservices. In some cases this feature may not be necessary, since administrators may want to send data to other systems as soon as possible, using a North task of microservice. Even in situations where data can be sent up North instantaneously, you should consider these scenarios:

  - FogLAMP may be installed in areas where the network is unreliable. The North plugins will provide the logic of retrying to gain connectivity and resending data when the connection has been lost in the middle of the transfer operations.
  - North services may rely on the use of networks that provide time windows to operate. 
  - Historians and other systems may work better when data is transferred in blocks instead of a constant streaming.

- **Data purging**: Data may persist for the time needed by any specific use case, but it is pretty common that after a while (it can be seconds or minutes, but also day or months) data is no longer needed in FogLAMP. For this reason, the Storage plugin is able to purge data. Purging may be by time or by space usage, in conjuction with the fact that data may have been already transferred to other systems.

- **Data backup/restore**: Data, but especially metadata (i.e. configuration), can be backed up and stored safely on other systems. In case of crash and recovery, the same data may be restored into FogLAMP. FogLAMP provides a set of generic API to execute backup and restore operations.


