Storage Service And Plugins
===========================

The storage component provides a level of abstraction of the database layer used within Fledge. The storage abstract is explicitly not a SQL layer, and the interface it offers to the clients of the storage layer; the device service, API and send process, is very deliberately not a SQL interface to facilitate the replacement of the underlying storage with any no-SQL storage mechanism or even a simple file storage mechanism. Different plugins may be used for the structured and unstructured data that is stored by the storage layer.

The three requirements that have resulted in the plugin architecture and separation of the database access into a microservice within Fledge are:

 - A desire to be able to support different storage mechanisms as the deployment and customer requirements dictate. E.g. SQL, no-SQL, in-memory, backing store (disk, SD card etc.) or simple file based mechanisms.

 - The ability to separate the storage from the south and north services of Fledge and to allow for distribution of Fledge across multiple physical hardware components.

 - To provide flexibility to allow components to be removed from a Fledge deployment, e.g. remove the buffering and have a simple forwarding router implementation of Fledge without storage.

Use of JSON
-----------

There are three distinct reasons that JSON is used within the storage layer, these are;

 - The REST API uses JSON to encode the payloads within each API entry point. This is the preferred payload type for all REST interfaces in Fledge. The option to use XML has been considered and rejected as the vast majority of REST interfaces now use JSON and not XML. JSON is generally more compact and easier to read than XML.

 - The interface between the generic storage layer and the plugin also passes requests and results as JSON. This is partly to make it compatible with the REST payloads and partly to give the plugin implementer flexibility and the ability to push functionality down to the plugin layer to be able to exploit storage system specific features for greatest efficiency.

 - Some of the structures that are persisted are themselves JSON encoded documents. The assumption is that in this case they will remain as JSON all the way to the storage system itself and be persisted as JSON rather than being translated. These JSON structures are transported within the JSON structure of a request (or response) payload and will be sent as objects within that payload although they are not interpreted as anything other than data to be stored by the storage layer.


Requirements
~~~~~~~~~~~~

The storage layer represents the interface to persist data for the Fledge appliance, all persisted data will be read or written via this storage layer. This includes:

 - Configuration data - this is a set of JSON documents indexed by a key.

 - Readings data - the readings coming from the device that have buffered for a period of time.

 - User & credential data - this is username, passwords and certificates related to the users of the Fledge API.

 - Audit trail data - this is a log of significant events during the lifetime of Fledge.

 - Metrics - various modules will hold performance metrics, such as readings in, readings out etc. These will be periodically written by those models as cumulative totals. These will be collected by the statistics gatherer and interval statistics of the values will be written to the persistent storage.

 - Task records - status and history of the tasks that have been scheduled within Fledge.

 - Flexible schemas - the storage layer should be written that the schema, assuming there is a schema based underlying storage mechanism, is not fixed by the storage layer itself, but by the implementation of the storage and the application (Fledge). In particular the set of tables and columns in those tables is not preconfigured in the storage layer component (assuming a schema based underlying data store).

Implementation Language
~~~~~~~~~~~~~~~~~~~~~~~

The core of the Fledge platform has to date been written using Python, for the storage layer however a decision has been taken to implement this in C/C++. There are a number of factors that need to be taken into account as a result of this decision.

 - Library choices made for the Python implementation are no longer valid and a choice has to be made for C/C++.

 - Common code, such as the microservices management API can not be reused and a C/C++ implementation is required.

The storage service differs from the other services within Fledge as it only supports plugins compiled to shared objects that have the prescribed C interface. The plugin's code itself may be in other languages, but it must compile to a C compatible shared object using the C calling conventions.

Language Choice Reasons
#######################

Initially it was envisaged that the entire Fledge product would be written in Python, after the initial demo implementation issues were starting to surface regarding the validity of this choice for implementation of a product such as Fledge. These issues are;

 - Scalability - Python is essentially a single threaded language due to the Global Interpreter Lock (GIL) which only allows a single Python statement to be executing at any one time.

 - Portability - As we started working more with OSIsoft and with ARM it became clear that the option to port Fledge or some of its components to embedded hardware was going to become more of a requirement for us. In particular the ARM mbed platform is one that has been discussed. Python is not available on this platform or numerous other embedded platforms.

If Python was not to be the language in which to implement in future then it was decided that the storage layer, as something that has yet to be started, might be best implemented in a different way. Since the design is based on micro-services with REST API’s between them, then it is possible to mix and match the implementation of different components amongst different languages.

The storage layer is a separate micro-service and not directly linked to any Python code, linkage is only via a REST API. Therefore the storage layer can implement a threading model that best suits it and is not tied to the Python threading model in use in other microservices.

The choice of C/C++ is based on what is commonly available on all the platforms on which we now envisage Fledge might need to run in the foreseeable future and on the experience available within the team.

Library Choice
##############

One of the key libraries that will need to be chosen for C/C++ is the JSON library since there is no native support for this in the language. There are numerous libraries that exist for this purpose, for example, rapidjson, Jansson and many more. Some investigation is required to find the most suitable. The factors to be considered in the choice of library are, in order of importance;

 - Functionality - clearly any library chosen must offer the feature we need.

 - Footprint - Footprint is a major concern for Fledge as we wish to run in constrained devices with the likelihood that in future the device we want to run on may become even smaller than we are considering today.

 - Thread safety - It is assumed that for reasons of scalability and the nature of a REST interface that multiple threads will be employed in the implementation, so hence thread safety is a major concern when choosing a library.

 - Performance - Any library chosen should be reasonably performant at the job it does in order to be considered. We need to avoid choosing libraries that are slow or bloated as part of our drive to run on highly constrained hardware.

The choice of the JSON library is also something to be considered; since JSON objects are passed across the plugin interface, choosing a C++ library would limit both the microservice and the plugins to use C++. It may be preferable to use a C based library and thus have the flexibility to have a C or C++ implementation for either the service itself or for the plugin.

Another key library choice, in order to support the REST interface, is an HTTP library capable of being used to support the REST interface development and able to support custom header fields and HTTPS. Once again these are numerous, libmicrohttpd, Simple-Web-Server, Proxygen. A choice must be made here also using the same criteria outlined above.

Thread safety is likely to be important also as it is assumed the storage layer will be multi-threaded and almost certainly utilise asynchronous I/O operations.

Classes of Data Stored
----------------------

There are two classes of data that Fledge needs to store:

  - Internally generated data

  - Data that emanates from sensors

The first of these are essentially Fledges configuration, state and lookup data it needs to function. The pattern of access to this data is the classic create, retrieve, update and delete operations that are common to most databases. Access is random by nature and usually via some form of indexes and keys.

The second class of data that is stored, and the one which is the primary function of Fledge to store, is the data that it receives from sensors. Here the pattern of access is very different; 

 - New data is always appended to the stored data

 - No updates are supported on this data

 - Data is predominately read in sequential blocks (main use case)

 - Random access is rare and confined to display and analytics within the user interface or by clients of the public API

 - Deletion of data is done based solely on age and entries will not be removed other than in chronological order.

Given the difference in the nature of the two classes of data and the possibility that this will result in different storage implementations for the two, the interface is split between these two classes of data. This allows;

 - Different plugins to be used for each type, perhaps a SQL database for the internal data storage and a specialised time series database or document store for the sensor readings.

 - A single plugin can choose to only implement a subset of the plugin API, e.g. the common data access methods or the readings methods. Or both.

 - Plugins can choose where and how they store the readings to optimize the implementation. E.g. a SQL data can store the JSON in a table or a series of tables if preferred.

 - The plugins are not forced to store the JSON data in a particular way. For example, a SQL database does not have to use JSON data types in a single column if it does not support them.

These two classes of data are referred to in this documentation as “common data access” and “readings data”.

Common Data Access Methods
--------------------------

Most of these types of data can be accessed by the classic create, update, retrieve and delete methods and consist of data in JSON format with an associated key and timestamp. In this case a simple create with a key and JSON value, an update with the same key and value, a retrieve with an optional key (which returns an array of JSON objects) and a delete with the key is all that is required. Configuration, metrics, task records, audit trail and user data all fall into this category. Readings however do not and have to be treated differently.

Readings Data Access
--------------------

Readings work differently from other data, both in the way they are created, retrieved and removed. There is no update functionality required for readings currently, in particular there is no method to update readings data.

The other difference with readings data from the other data that is managed by the storage layer is related to the volume and use of the data. Readings data is by far the largest volume of data that is managed by Fledge, and has a somewhat different lifecycle and use. The data streams in from external devices, lives within the storage layer for a period of time and is then removed. It may also be retrieved by other processes during the period of time in lives within the buffer.

Another characteristic of the readings data is the ability to trigger processing based on the arrival of new data. This could be from a process that blocks, waiting for data to arrive or as an optimisation when a process wishes to process the new data as it arrives and not retrieve it explicitly from the storage layer. In this later case the storage data would still be buffered in the storage layer using the usual rules for storage and purging of that data.

Reading Creation
~~~~~~~~~~~~~~~~

Readings come from the device component of Fledge and are a time series stream of JSON documents. They should be appended to the storage device with unique keys and a timestamp. The appending of readings can be considered as a queuing mechanism into the storage layer.

Managing Blocked Retrievals
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Various components, most notably the sending process and north service, read blocks of readings from the storage layer. These components may request a notification when new readings are available, for example the sending process may request a new block of data when there are no more blocks available. This will be registered with the storage layer and the storage layer will notify the sending process that new data is available and that a subsequent call will return a new block of data.

This is an advantage feature that may be omitted from the first version. It is intended to allow a process that is fetching and processing readings data to have an efficient way to know that new data is available to be processed. One scenario would be a sending process that has sent all of the readings that are available; it wishes to be informed when new readings are available to it for sending. Rather than poll the storage layer requesting new readings, it may request the storage layer to call it when a number of readings are available beyond the id that process last fetched.

Bypassing Database Storage
~~~~~~~~~~~~~~~~~~~~~~~~~~

One potential optimisation which the storage layer should be built to allow as a future optimization is to architect the storage layer such that a publish/subscribe mechanism could be used to allow the data that flows into the storage layer and be directed to both the storage plugin itself and also send it to other services such as the sending process.

Reading Retrieval
~~~~~~~~~~~~~~~~~

Readings may be retrieved via one of two mechanism

 - By the sending process that will request readings within a time window

 - From the API layer for analysis within the edge device or an external entity that is retrieving the data via the Fledge user REST API.

The sending process and north service may require large volumes of data to be sent, in order to reduce the memory footprint required and to improve reliability, the sending module will require the readings in controllable “chunks”, therefore it will request readings between two timestamps in blocks of x readings and then request each block sequentially. It is the responsibility of the sending process to ensure that it requests blocks of a reasonable size. Since the REST interface is by definition stateless the storage layer does not need to maintain any information about previous fetches of data.

The API access to data  will be similar, except it will have a limitation on the number of readings, it will request ordered readings between timestamps and ask for readings between the n-th and m-th reading. E.g. Return readings between 21:00 on 10th June 2017 and 21:00 on the 11th June limited to the 100th and 150th reading in that time. The API layer will enforce a maximum number of readings that can be returned in order to make sure result sets are small.

Reading Removal
~~~~~~~~~~~~~~~

The reading removal is done via the purge process, this process will request readings before a given time to be removed from the storage device based on the timestamp of each reading. Introducing the storage layer and removing the pure SQL interface will alter the nature of the purge process and essentially move the logic of the purge process into the storage layer.

Storage Plugin
--------------

One of the requirements that drives the desire to have a storage layer is to isolate the other services and users of the storage layer from the technology that provides that storage. The upper level of the storage service offers a consistent API to the client of the storage service and provides the common infrastructure to communicate with the other services within Fledge, whilst the lower layer provides the interface to the storage technology that will actually store the data. Since we have a desire to be able to switch between different storage layers this lower layer will use a plugin mechanism that will allow a common storage service to dynamically load one or more storage plugins.

The ability to use multiple plugins within a single storage layer would allow a different plugin to be used for each class of data, see Classes of Data Stored. This would give the flexibility to store Fledges internal data in generic database whilst storing the readings data in something that was tailored specifically to time series or JSON data. There is no requirement to have multiple plugins in any specific deployment, however if the option is to be made available the code that is initially developed should be aware of this future requirement and be implemented appropriately. It is envisaged that the first version will have a single plugin for both classes of data. The incremental effort for supporting more than one plugin is virtually zero, hence the inclusion here. 

Entry Points
~~~~~~~~~~~~

The storage plugin exposes a number of entry points in a similar way to the Python plugins used for the translator interface and the device interface. In the C/C++ environment the mechanism is slightly different from that of Python. A plugin is a shared library that is included with the installation or may be installed later into a known location. The library is use by use the dlopen() C library function and each entry point is retrieved using the dlsym() call.

The plugin interface is modeled as a set of C functions rather than as a C++ class in order to give the plugin writer the flexibility to implement the plugin in C or C++ as desired.

.. list-table::
        :widths: 30 70
        :header-rows: 1

        * - Entry Point
          - Summary
        * - plugin_info
          - Return information about the plugin.
        * - plugin_init
          - Initialise the plugin.
        * - plugin_common_insert
          - Insert a row into a data set (table).
        * - plugin_common_retrieve
          - Retrieve a result set from a table.
        * - plugin_common_update
          - Update data in a data set.
        * - plugin_common_delete
          - Delete data from a data set.
        * - plugin_reading_append
          - Append one or more readings or the readings table.
        * - plugin_reading_fetch
          - Retrieve a block of readings from the readings table.
        * - plugin_reading_retrieve
          - Generic retrieve to retrieve data from the readings table based on query parameters.
        * - plugin_reading_purge
          - Purge readings from the readings table.
        * - plugin_release
          - Release a result set previously returned by the plugin to the plugin, so that it may be freed.
        * - plugin_last_error
          - Return information on the last error that occurred within the plugin.
        * - plugin_shutdown
          - Called prior to the device service being shut down.


Plugin Error Handling
~~~~~~~~~~~~~~~~~~~~~

Errors that occur within the plugin must be propagated to the generic storage layer with sufficient information to allow the generic layer to report those errors and take appropriate remedial action. The interface to the plugin has been deliberately chosen not to use C++ classes or interfaces so that plugin implementers are not forced to implement plugins in C++.  Therefore the error propagation mechanism can not be C++ exceptions and a much simpler, language agnostic approach must be taken. To that end errors will be indicated by the return status of each call into the interface and a specific plugin entry point will be used to retrieve more details on errors that occur.

Plugin API Header File
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  #ifndef _PLUGIN_API
  #define _PLUGIN_API

  typedef struct {
          char         *name;
          char         *version;
          unsigned int options;
          char         *type;
          char         *interface;
          char         *config;
  } PLUGIN_INFORMATION;

  typedef struct {
          char         *message;
          char         *entryPoint;
          boolean      retryable;
  } PLUGIN_ERROR;

  typedef void * PLUGIN_HANDLE;

  /**
   * Plugin options bitmask values
   */
  #define SP_COMMON       0x0001
  #define SP_READINGS     0x0002

  /**
   * Plugin types
   */
  #define PLUGIN_TYPE_STORAGE     "storage"

  /**
   * Readings purge flags
   */
  #define PLUGIN_PURGE_UNSENT     0x0001

  extern PLUGIN_INFORMATION *plugin_info();
  extern PLUGIN_HANDLE plugin_init();
  extern boolean plugin_common_insert(PLUGIN_HANDLE handle, char *table, JSON *data);
  extern JSON *plugin_common_retrieve(PLUGIN_HANDLE handle, char *table, JSON *query);
  extern boolean plugin_common_update(PLUGIN_HANDLE handle, char *table, JSON *data);
  extern boolean plugin_common_delete(PLUGIN_HANDLE handle, char *table, JSON *condition);
  extern boolean plugin_reading_append(PLUGIN_HANDLE handle, JSON *reading);
  extern JSON *plugin_reading_fetch(PLUGIN_HANDLE handle, unsigned long id, unsigned int blksize);
  extern JSON *plugin_reading_retrieve(PLUGIN_HANDLE handle, JSON *condition);
  extern unsigned int plugin_reading_purge(PLUGIN_HANDLE handle, unsigned long age, unsigned int flags, unsigned long sent);
  extern plugin_release(PLUGIN_HANDLE handle, JSON *results);
  extern PLUGIN_ERROR *plugin_last_error(PLUGIN_HANDLE);
  extern boolean plugin_shutdown(PLUGIN_HANDLE handle)
  #endif


Plugin Support
~~~~~~~~~~~~~~

A storage plugin may support either or both of the two data access methods; common data access methods and readings access methods. The storage service can use the mechanism to have one plugin for the common data access methods, and hence a storage system for the general tables and configuration information. It then may load a second plugin in order to support the storage and retrieval of readings.

Plugin Information
~~~~~~~~~~~~~~~~~~

The plugin information entry point, plugin_info() allows the device service to retrieve information from the plugin.  This information comes back as a C structure (PLUGIN_INFORMATION). The PLUGIN_INFORMATION will include a number of fields with information that will be used by the storage service.

.. list-table::
        :header-rows: 1
        :widths: 20 60 20

        * - Property
          - Description
          - Example
        * - name
          - A printable name that can be used to identify the plugin.
          - Postgres Plugin
        * - version
          - A version number of the plugin, again used for diagnostics and status reporting
          - 1.0.2
        * - options
          - A bitmask of options that describes the level of support offered by this plugin.
            Currently two options are available; SP_COMMON and SP_READINGS. Each of these bits represents support for the set of common data access methods and the readings access method. See Plugin Support for details.
          - SP_COMMON|SP_READINGS
        * - type
          - The type of the plugin, this is used to distinguish a storage API plugin from any other type of plugin in Fledge. This should always be the string “storage”.
          - storage
        * - interface
          - The interface version that the plugin implements. Currently the version is 1.0.
          - 1.0


This is the first call that will be made to the plugin after it has been loaded, it is designed to give the loader enough information to know how to interact with the plugin and to allow it to confirm the plugin is of the correct type.

Plugin Initialisation
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern PLUGIN_HANDLE plugin_init();

Called after the plugin has been loaded and the plugin information has been successfully retrieved. This will only be called once and should perform the initialisation necessary for the sensor communication. 

The plugin initialisation call returns a handle, of type void \*, which will be used in future calls to the plugin. This may be used to hold instance or state information that would be needed for any future calls. The handle should be used in preference to global variables within the plugin.

If the initialisation fails the routine should raise an exception. After this exception is raised the plugin will not be used further.

Plugin Common Insert
~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern boolean plugin_common_insert(PLUGIN_HANDLE handle, char *table, JSON *data);

Insert data that is represented by the JSON structure that is passed into the call to the specified table.

The handle is the value returned by the call to plugin_init().

The table is the name of the table, or data set, into which the data is to be inserted.

The data is a JSON document with a number of property name/value pairs. For example, if the plugin is storing the data in a SQL database; the names are the column names in an equivalent SQL database and the values are the values to write to that column. Plugins for non-SQL, such as document databases may choose to store the data as it is represented in the JSON document or in a very different structure. Note that the value may be of different types, represented by JSON type and may be JSON objects themselves. The plugin should do whatever conversation is needed for the particular storage layer based on the JSON type.

The return value of this call is a boolean that represents success or value of the insert.

Plugin Common Retrieve
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern JSON *plugin_common_retrieve(PLUGIN_HANDLE handle, char *table, JSON *query);

Retrieve a data set from a named table.

The handle is the value returned by the call to plugin_init().

The table is the name of the table, or data set, from which the data is to be retrieved.

The query is a JSON document that encodes the predicates for the query, the where condition in the case of a SQL layer. See Encoding Query Predicates in JSON for details of how this JSON is encoded.

The return value is the result set of the query encoded as a JSON structure. This encoding takes the form of an array of JSON object, one per row in the result set. Each object represents a row encoded as name/value pair properties. In addition a property count is included that returns the number of rows in the result set.

An query that returns two rows with columns named “c1”, “c2” and “c3” would be represented as

.. code-block:: JSON

  {
    "count" : 2,
    "rows"  : [ 
                {  
                   "c1" : 1,
                   "c2" : 5,
                   "c3" : 9
                },
                {  
                   "c1" : 8,
                   "c2" : 2,
                   "c3" : 15
                }
              ]
  }

The pointer return to the caller must be released when the caller has finished with the result set. This is done by calling the plugin_release() call with the plugin_handle and the pointer returned from this call.

Plugin Common Update
~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern boolean plugin_common_update(PLUGIN_HANDLE handle, char *table, JSON *data);


Update the contents of a set of rows in the given table.

The handle is the value returned by the call to plugin_init().

The table is the name of the table, or data set, into which the data is to be updated.

The data item is a JSON document that encodes but the values to set in the table and the condition used to select the data. The object contains two properties, a condition, the value of which is a JSON encoded where clause as defined in Encoding Query Predicates in JSON and a values object. The values object is a set of name/value pairs where the name matches column names within the data and the value defines the value to set for that column.

The following JSON example 

.. code-block:: JSON

  {
    "condition" : { 
                    "column"    : "c1",
                    "condition" : "=",
                    "value"     : 15
                  },
    "values"    : {
                    "c2" : 20,
                    "c3" : "Updated"
                  }
  }


would map to a SQL update statement

.. code-block:: SQL

  UPDATE <table> SET c2 = 20, c3 = "Updated" where c1 = 15;

Plugin Common Delete
~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern boolean plugin_common_delete(PLUGIN_HANDLE handle, char *table, JSON *condition);


Update the contents of a set of rows in the given table.

The handle is the value returned by the call to plugin_init().

The table is the name of the table, or data set, into which the data is to be removed.
The condition JSON element defines the condition clause which will select the rows of data to be removed. This condition object follows the same JSON encoding scheme defined in the section Encoding Query Predicates in JSON. A condition object containing

.. code-block:: JSON

  {
      "column"    : "c1",
      "condition" : "=",
      "value"     : 15
  }

would delete all rows where the value of c1 is 15.

Plugin Reading Append
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern boolean plugin_reading_append(PLUGIN_HANDLE handle, JSON *reading);

The handle is the value returned by the call to plugin_init().

The reading JSON object is an array of one or more readings objects that should be appended to the readings storage device. 

The return status indicates if the readings have been successfully appended to the storage device or not.

Plugin Reading Fetch
~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern JSON *plugin_reading_fetch(PLUGIN_HANDLE handle, unsigned long id, unsigned int blksize);

Fetch a block of readings, starting from a given id and return them as a JSON object.

This call will be used by the sending process to retrieve readings that have been buffered and send them to the historian. The process of sending readings will read a set of consecutive readings from the database and send them as a block rather than send all readings in a single transaction with the historian. This allows the sending process to rate limit the send and also to provide improved error recovery in the case of transmission failure.

The handle is the value returned by the call to plugin_init().

The id passed in is the id of the first record to return in the block.

The blksize is the maximum number of records to return in the block. If there are no sufficient readings to return a complete block of readings then a smaller number of readings will be returned. If no reading can be returned then a NULL pointer is returned. This call will not block waiting for new readings.

Plugin Reading Retrieve
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern JSON *plugin_reading_retrieve(PLUGIN_HANDLE handle, JSON *condition);

Return a set of readings as a JSON object based on a query to select those readings.

The handle is the value returned by the call to plugin_init().

The condition is a JSON encoded query using the same mechanisms as defined in the section Encoding Query Predicates in JSON. In this case it is expected that the JSON condition would include not just selection criteria but also grouping and aggregation options.

Plugin Reading Purge
~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern unsigned int plugin_reading_purge(PLUGIN_HANDLE handle, unsigned long age, unsigned int flags, unsigned long sent);

The removal of readings data based on the age of the data with an optional limit to prevent purging of data that has not been sent out of the Fledge device for external storage/processing.

The handle is the value returned by the call to plugin_init().

The age defines the maximum age of data that is to be retained

The flags define if the sent or unsent status of data should be considered or not. If the flags specify that unsent data should not be purged then the value of the sent parameter is used to determine what data has not been sent and readings with an id greater than the sent id will not be purged.

Plugin Release
~~~~~~~~~~~~~~

.. code-block:: C

  extern boolean plugin_release(PLUGIN_HANDLE handle, JSON *json)

This call is used by the storage service to release a result set or other JSON object that has been returned previously from the plugin to the storage service. JSON structures should only be released to the plugin when the storage service has finished with them as the plugin will most likely free the memory resources associated with the JSON structure.

Plugin Error Retrieval
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: C

  extern PLUGIN_ERROR *plugin_last_error(PLUGIN_HANDLE)

Return more details on the last error that occurred within this instance of a plugin. The returned pointer points to a static area of memory that will be overwritten when the next error occurs within the plugin. There is no requirement for the caller to free any memory returned.

Plugin Shutdown
~~~~~~~~~~~~~~~

.. code-block:: C

  extern boolean plugin_shutdown(PLUGIN_HANDLE handle)

Shutdown the plugin, this is called with the plugin handle returned from plugin_init and is the last operation that will be performed on the plugin. It is designed to allow the plugin to complete any outstanding operations it may have, close connections to storage layers and generally release resources.

Once this call has completed the plugin handle that was previously given out by the plugin should be considered to be invalid and any future calls using that handle should fail.

Encoding Query Predicates in JSON
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One particular issue with a storage layer API is how to encode the query predicates in a JSON structure that are as expression as the SQL predicates whilst not making the JSON document too complex whilst still maintaining the flexibility to be able to implement storage plugins that are not based on SQL databases. In traditional REST API’s the HTTP GET operation should be used to retrieve data, however the GET operation does not strictly support body content and therefore any modifiers or queries have to be encoded in the URL. Encoding complex query predicates in a URL quickly becomes an issue, therefore this API layer will not take this approach, it will allow simple predicates in the URL, but will use JSON documents and PUT operations to encode more complex predicates in the body of the PUT operation.

The same JSON encoding will be used in the storage layer to the plugin interface for all retrieval operations.

The predicates will be encoded in a JSON object that contains a where clause, other optional properties may be added to control aggregation, grouping and sorting of the selected data.

The where object contains a column name, operation and value to match, it may also optionally contain an and property and an or property. The values of the and and or property, if they exist, are themselves where objects.

As an example the following JSON object

.. code-block:: JSON

  {
    "where"  : {
                 "column"    : "c1",
                 "condition" : "=",
                 "value"     : "mine",
                 "and"       : {
                                 "column"    : "c2",
                                 "condition" : "<",
                                 "value"     : 20
                               }
               }
  }

would result in a SQL where clause of the form

.. code-block:: console

  WHERE c1 = “mine” AND c2 < 20

An example of a more complex example, using an and and an or condition, would be

.. code-block:: JSON

  {
	"where" : {
			"column"    : "id",
			"condition" : "<",
			"value"     : "3",
			"or"        : {
				           "column"    : "id",
				           "condition" : ">",
				           "value"     : "7",
				           "and"       : {
					            "column"    : "description",
					            "condition" : "=",
					            "value"     : "A test row"
				               }
			              }
		   }
  }

Which would yield a traditional SQL query of

.. code-block:: console

  WHERE id < 3 OR id > 7 AND description = “A test row”

.. note::

  It is currently not possible to introduce bracketed conditions.

Aggregation
###########

In some cases adding aggregation of the results of a record selection is also required. Within the JSON this is represented using an optional aggregate object.

.. code-block:: console

  "aggregate" : {
                "operation" : "<operation>"
                "column"    : "<column name>"
              }

Valid operations for aggregations are; min, max, avg, sum and count.

As an example the following JSON object

.. code-block:: JSON

  {
    "where"     : {
                     "column"    : "room",
                     "condition" : "=",
                     "value"     : "kitchen"
                  },
    "aggregate" : {
                     "operation" : "avg",
                     "column"    : "temperature"
                  }
  }

Multiple aggregates may be applied, in which case the aggregate property becomes an array of objects rather than a single object.

.. code-block:: JSON

  {
    "where"     : {
                     "column"    : "room",
                     "condition" : "=",
                     "value"     : "kitchen"
                  },
    "aggregate" : [
                    {
                       "operation" : "avg",
                       "column"    : "temperature"
                    },
                    {
                       "operation" : "min",
                       "column"    : "temperature"
                    },
                    {
                       "operation" : "max",
                       "column"    : "temperature"
                    }
		]
  }

The result set JSON that is created for aggregates will have properties with names that are a concatenation of the column and operation. For example, the where clause defined above would result in a response similar to below.

.. code-block:: JSON

  {
     "count": 1,
     "rows" : [
               {
                  "avg_temperature" : 21.8,
                  "min_temperature" : 18.4,
                  "max_temperature" : 22.6
               }
              ]
  }

Alternatively an “alias” property may be added to aggregates to control the naming of the property in the JSON document that is produced.

.. code-block:: JSON

  {
    "where"     : {
                     "column"    : "room",
                     "condition" : "=",
                     "value"     : "kitchen"
                  },
    "aggregate" : [
  {
                       "operation" : "avg",
                       "column"    : "temperature",
                       "alias"     : "Average"
                    },
  {
                       "operation" : "min",
                       "column"    : "temperature",
                       "alias"     : "Minimum"
                    },
  {
                       "operation" : "max",
                       "column"    : "temperature",
                       "alias"     : "Maximum"
                    }
			]
  }

Would result in the following output

.. code-block:: JSON

  {
      "count": 1,
      "rows" : [
                 {
                   "Average" : 21.8,
                   "Minimum" : 18.4,
                   "Maximum" : 22.6
                 }
     ]
  }

When the column that is being aggregated contains a JSON document rather than a simple value then the column property is replaced with a json property and the object defines the properties within the json document in the database field that will be used for aggregation.

The following is an example of a payload that will query the readings data and return aggregations of the JSON property rate from within the column reading. The column reading is a JSON blob within the database.

.. code-block:: JSON

  {
          "where"   : {
                                  "column"    : "asset_code",
                                  "condition" : "=",
                                  "value"     : "MyAsset"
                          },
          "aggregate" : [
                          {
                                  "operation" : "min",
                                  "json"      : {
                                                      "column"     : "reading",
                                                      "properties" : "rate"
                                                  },
                                  "alias"     : "Minimum"
                          },
                          {
                                  "operation" : "max",
                                  "json"      : {
                                                      "column"     : "reading",
                                                      "properties" : "rate"
                                                  },
                                  "alias"     : "Maximum"
                          },
                          {
                                  "operation" : "avg",
                                  "json"      : {
                                                      "column" : "reading",
                                                      "properties" : "rate"
                                                  },
                                  "alias"     : "Average"
                          }
                        ],
          "group" : "asset_code"
  }

Grouping
########

Grouping of records can be achieved by adding a group property to the JSON document, the value of the group property is the column name to group on.

.. code-block:: console

  "group" : "<column name>"

Sorting
#######

Where the output is required to be sorted a sort object may be added to the JSON document. This contains a column to sort on and a direction for the sort “asc” or “desc”.

.. code-block:: console

  "sort"   : {
       "column"    : "c1",
       "direction" : "asc"
     }

It is also possible to apply multiple sort operations, in which case the sort property becomes an ordered array of objects rather than a single object

.. code-block:: console

  "sort"   : [
      {
        "column"    : "c1",
        "direction" : "asc"
      },
      {
        "column"    : "c3",
        "direction" : "asc"
      }
     ]

.. note::

    The direction property is optional and if omitted will default to ascending order.

Limit
#####

A limit property can be included that will limit the number of rows returned to no more than the value of the limit property.

.. code-block:: console

   "limit" : <number>


Creating Time Series Data
#########################

The timebucket mechanism in the storage layer allows data that includes a timestamp value to be extracted in timestamp order, grouped over a fixed period of time.

The time bucket directive allows a timestamp column to be defined, the size of each time bucket, in seconds, an optional date format for the timestamp written in the results and an optional alias for the timestamp property that is written.

.. code-block:: console

	"timebucket" :  {
			   "timestamp" : "user_ts",
			   "size"      : "5",
			   "format"    : "DD-MM-YYYY HH24:MI:SS",
			   "alias"     : "bucket"
			}

If no size element is present then the default time bucket size is 1 second.

This produces a grouping of data results, therefore it is expected to be used in conjunction with aggregates to extract data results. The following example is the complete payload that would be used to extract assets from the readings interface

.. code-block:: JSON

  {
	"where" : {
				"column"    : "asset_code",
				"condition" : "=",
				"value"     : "MyAsset"
			},
	"aggregate" : [
			{
				"operation" : "min",
				"json"      : {
						    "column"     : "reading",
						    "properties" : "rate"
					        },
				"alias"     : "Minimum"
			},
			{
				"operation" : "max",
				"json"      : {
						    "column"     : "reading",
						    "properties" : "rate"
					        },
				"alias"     : "Maximum"
			},
			{
				"operation" : "avg",
				"json"      : {
						    "column"     : "reading",
						    "properties" : "rate"
					        },
				"alias"      : "Average"
			}
		      ],
	"timebucket" :  {
			   "timestamp" : "user_ts",
			   "size"      : "30",
			   "format"    : "DD-MM-YYYY HH24:MI:SS",
			   "alias"     : "Time"
			}
  }

In this case the payload would be sent in a PUT request to the URL /storage/reading/query and the returned values would contain the reading data for the asset called MyAsset which has a sensor value rate in the JSON payload it returns. The data would be aggregated in 30 second time buckets and the return values would be in the JSON format shown below.

.. code-block:: JSON

  {
   "count":2,
   "Rows":[
            {
              "Minimum"    : 2,
              "Maximum"    : 96,
              "Average"    : 47.9523809523809,
              "asset_code" : "MyAsset",
              "Time"       : "11-10-20177 15:10:50"
             },
             {
               "Minimum"    : 1,
               "Maximum"    : 98,
               "Average"    : 53.7721518987342,
               "asset_code" : "MyAsset",
               "Time"       : "11-10-20177 15:11:20"
             }
           ]
  }

Joining Tables
##############

Joins can be created between tables using the join object. The JSON object contains a table name, a column to join on in the table of the query itself and an optional column in the joined table. It also allows a query to be added that may define a where condition to select columns in the joined table and a returns object to define which rows should be used from that table and how to name them.

The following example joins the table called attributes to the table given in the URL of the request. It uses a column called parent_id in the attributes table to join to the column id in the table given in the request. If the column name in both tables is the same then there is no need to give the column field in the table object, the column name can be given in the on field instead.

.. code-block:: JSON

  {
        "join" : {
                "table"  : {
                                "name" : "attributes",
                		"column" : "parent_id"
                },
                "on"     : "id",	
                "query"  : {    
                                "where" : { 
                                        "column"    : "name",
                                        "condition" : "=",
                                        "value"     : "MyName"
                                        
                                        }, 
                                "return" : [
                                        "parent_id",
                                        {       
                                                "column" : "name",
                                                "alias"  : "attribute_name"
                                        },
                                        {
                                                "column" : "value",
                                                "alias"  : "attribute_value"
                                        }
                                        ]
                        }
        }
  }

Assuming no additional where conditions or return constraints on the main table query, this would yields SQL of the form

.. code-block:: SQL

  select t1.*, t2.parent_id, t2.name as "attribute_name", t2.value as "attribute_value"  from parent t1, attributes t2 where t1.id = t2.parent_id and t2.name = "MyName";

Joins may be nested, allowing more than two tables to be joined. Assume again we have a parent table that contains items and an attributes table that contains attributes of those items. We wish to return the items that have an attribute called MyName and a colour. We need to join the attributes table twice to get the requests we require. The JSON payload would be as follows

.. code-block:: JSON

  {
        "join" : {
                "table"  : {
                                "name" : "attributes",
                                "column" : "parent_id"
                        },      
                "on"     : "id",
                "query"  : {    
                                "where" : { 
                                        "column"    : "name",
                                        "condition" : "=",
                                        "value"     : "MyName"
                                        
                                        }, 
                                "return" : [
                                        "parent_id",
                                        {
                                                "column" : "value",
                                                "alias"  : "my_name"
                                        }
                                        ]
                                "join" : {
                                                "table" : {
                                                "name" : "attributes",
                                                        "column" : "parent_id"
                                                },
                                                "on"     : "id",
                                                "query"  : {
                                                         "where" : {
                                                                "column"    : "name",
                                                                "condition" : "=",
                                                                "value"     : "colour"

                                                                },
                                                          "return" : [
                                                                 "parent_id",
                                                                {       
                                                                         "column" : "value",
                                                                         "alias"  : "colour"
                                                                }       
                                                           ]
                                                }
                                        }
                        }
        }
  }

And the resultant SQL query would be

.. code-block:: SQL

  select t1.*, t2.parent_id, t2.value as "my_name", t3.value as "colour"  from parent t1, attributes t2, attributes t3 where t1.id = t2.parent_id and t2.name = "MyName" and t1.id = t3.parent_id and t3.name = "colour";
 
JSON Predicate Schema
#####################

The following is the JSON schema definition for the predicate encoding.

.. code-block:: JSON

  {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "definitions": {},
    "id": "http://example.com/example.json",
    "properties": {
      "group": {
        "id": "/properties/group",
        "type": "string"
      },
      "sort": {
        "id": "/properties/sort",
        "properties": {
          "column": {
            "id": "/properties/sort/properties/column",
            "type": "string"
          },
          "direction": {
            "id": "/properties/sort/properties/direction",
            "type": "string"
          }
        },
        "type": "object"
      },
      "aggregate": {
        "id": "/properties/aggregate",
        "properties": {
          "column": {
            "id": "/properties/aggregate/properties/column",
            "type": "string"
          },
          "operation": {
            "id": "/properties/sort/properties/operation",
            "type": "string"
          }
        },
        "type": "object"
      },
    "properties": {
      "limit": {
        "id": "/properties/limit",
        "type": "number"
      }
      "where": {
        "id": "/properties/where",
        "properties": {
          "and": {
            "id": "/properties/where/properties/and",
            "properties": {
              "column": {
                "id": "/properties/where/properties/and/properties/column",
                "type": "string"
              },
              "condition": {
                "id": "/properties/where/properties/and/properties/condition",
                "type": "string"
              },
              "value": {
                "id": "/properties/where/properties/and/properties/value",
                "type": "string"
              }
            },
            "type": "object"
          },
          "column": {
            "id": "/properties/where/properties/column",
            "type": "string"
          },
          "condition": {
            "id": "/properties/where/properties/condition",
            "type": "string"
          },
          "or": {
            "id": "/properties/where/properties/or",
            "properties": {
              "column": {
                "id": "/properties/where/properties/or/properties/column",
                "type": "string"
              },
              "condition": {
                "id": "/properties/where/properties/or/properties/condition",
                "type": "string"
              },
              "value": {
                "id": "/properties/where/properties/or/properties/value",
                "type": "string"
              }
            },
            "type": "object"
          },
          "value": {
            "id": "/properties/where/properties/value",
            "type": "string"
          }
        },
        "type": "object"
      }
    },
    "type": "object"
  }

Controlling Returned Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The common retrieval API and the reading retrieval API can be controlled to return subsets of the data by defining the “columns” to be returned in an optional “return” object in the JSON payload of these entry points.

Returning Limited Set of Columns
################################

An optional “returns” object may be followed by a JSON array that contains the names of the columns to return.

.. code-block:: console

        "return" : [ "column1", "column2", "column3" ]

The array may be simple strings that the columns to return or they may be JSON objects which give the column and and an alias for that column

.. code-block:: console

        "return : [ "column1", {
                                "column" : "column2",
                                "alias"  : "SecondColumn"
                                 }
                    ]


Individual array items may also be mixed as in the example above.

Formatting Columns
##################

When a return object is specified it is also possible to format the returned data, this is particularly applicable to dates. Formatting is done by adding a format property to the column object to be returned. 

.. code-block:: console

	"return" : [ "key", "description", 
			{
			  "column" : "ts",
			  "format" : "DD Mon YYYY",
			  "alias" : "date"
			}
		    ]

The format string may be for dates or numeric values. The content of the string for dates is a template pattern  consisting of a combination of the following.

.. list-table::
        :widths: 20 80
        :header-rows: 1

        * - Pattern
          - Description
        * - HH
          - Hour of the day in 12 hour clock
        * - HH24
          - Hour of the day in 24 hour clock
        * - MI
          - Minute value
        * - SS
          - Seconds value
        * - MS
          - Milliseconds value
        * - US
          - Microseconds value
        * - SSSS
          - Seconds since midnight
        * - YYYY
          - Year as 4 digits
        * - YY
          - Year as 2 digits
        * - Month
          - Full month name
        * - Mon
          - Month name abbreviated to 3 characters
        * - MM
          - Month number
        * - Day
          - Day of the week
        * - Dy
          - Abbreviated data of the week
        * - DDD
          - Day of the year
        * - DD
          - Day of the month
        * - D
          - Day of the week
        * - W
          - Week of the year
        * - am
          - am/pm meridian


Return JSON Document Content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The returns mechanism may also be used to return the properties within a JSON document stored within the database.

.. code-block:: JSON

  {
        "return" : [ 
                        "code", 
                        { 
                                "column" : "ts",
                                "alias"  : "timestamp" 
                        }, 
                        { 
                                "json" : { 
                                                "column"     : "log", 
                                                "properties" : "reason" 
                                         }, 
                                "alias" : "myJson"
                        } 
                   ]    
  }

In the example above a database column called json contains a JSON document with the property reason at the base level of the JSON document. The above statement extracts the JSON properties value and returns it in the result set using the property name myJSON.

To access properties nested more deeply in the JSON document the properties property in the above example can also be an array of JSON property names for each level in the hierarchy. If the column contains a JSON document as below,

.. code-block:: console

  {
        "building" : {
                        "floor" : {     
                                        "room" : {      
                                                        "number" : 432,
                                                        ...
                                                 },
                                 },
                     }
  }

To access the room number a return fragment as shown below would be used.

.. code-block:: JSON

  {       
        "return" : [    
                        {
                                "json" : { 
                                                "column" : "street", 
                                                "properties" : [
                                                        "building",
                                                        "floor",
                                                        "room",
                                                        "number"
                                                                ]
                                         }, 
                                "alias" : "RoomNumber"
                        }
                   ]
  }
 
