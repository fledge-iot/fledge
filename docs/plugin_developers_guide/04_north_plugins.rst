.. North Plugins

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. =============================================


North Plugins
=============

North plugins are used in North tasks and micro services to extract data buffered in Fledge and send it Northbound, i.e. to a server or a service in the Cloud or in an Enterprise data center. North plugins may be written in Python or C/C++, a number of different north plugins are available as examples that may be used when creating new plugins.

A north plugin has a limited number of entry points that it much support, these entry points are the same for both Python and C/C++ north plugins.

.. list-table::
    :header-rows: 1

    * - Entry Point
      - Description
    * - plugin_info
      - Return information about the plugin including the configuration for the plugin. This is the same as plugin_info in all other types of plugin and is part of the standard plugin interface.
    * - plugin_init
      - Also part of the standard plugin interface. This call is passed the request configuration of the plugin and should be used to do any initialization of the plugin.
    * - plugin_send
      - This entry point is the north plugin specific entry point that is used to send data from Fledge. This will be called repeatedly with blocks of readings.
    * - plugin_shutdown
      - Part of the standard plugin interface, this will be called when the plugin is no longer required and will be the final call to the plugin.
    * - plugin_register
      - Register the callback function used for control writes and operations.

The life cycle of a plugin is very similar regardless of if it is written in Python or C/C++, the *plugin_info* call is made first to determine data about the plugin. The plugin is then initialized by calling the *plugin_init* entry point. The *plugin_send* entry point will be called multiple times to send the actual data and finally the *plugin_shutdown* entry point will be called.

In the following sections each of these calls will be described in detail and samples given in both C/C++ and Python.

Python Plugins
--------------

Python plugins are loaded dynamically and executed either within a task, known as the *sending_task* or *north* task. This code is implemented in C++ and embedded a Python interpreter that is used to run the Python plugin.

The plugin_info call
~~~~~~~~~~~~~~~~~~~~

The *plugin_info* call is the first call that will be made to a plugin and is called only once. It is part of the standard plugin interface that is implemented by north, south, filter, notification rule and notification delivery plugins. No arguments are passed to this call and it should return a *plugin information structure* as a Python dict.

A typical implementation for a simple north plugin simply returns a DICT as follows

.. code-block:: python

    def plugin_info():
        """ Used only once when call will be made to a plugin.

            Args:
            Returns:
                Information about the plugin including the configuration for the plugin
        """
        return {
            'name': 'http',
            'version': '1.9.1',
            'type': 'north',
            'interface': '1.0',
            'config': _DEFAULT_CONFIG
        }


The items in the structure returned by *plugin_info* are

.. list-table::
    :header-rows: 1

    * - Name
      - Description
    * - name
      - The name of the plugin
    * - version
      - The version of the plugin. Typically this is the same as the version of Fledge it is designed to work with but is not constrained to be the same.
    * - type
      - The type of the plugin, in this case the type will always be *north*
    * - interface
      - The version of the plugin interface that the plugin supports. In this case the version if 1.0
    * - config
      - The DICT that defines the configuration that the plugin has as default.

In the case above *_DEFAULT_CONFIG* is another Python DICT that contains the defaults for the plugin configuration and will be covered in the Configuration section.


Configuration
#############

Configuration within Fledge is represented in a JSON structure that defines a name, value, default, type and a number of other optional parameters. The configuration process works by the plugins having a default configuration that they return from the plugin_init call. The Fledge configuration code will then combine this with a copy of that configuration that it holds. On the first time a service is created, with no previously held configuration, the configuration manager will take the default values and make those the actual values. The user may then update these to set non-default values. In subsequent executions of the plugin these values will be combined with the defaults to create the in use configuration that is passed to the *plugin_init* entry point. The mechanism is designed to allow initial execution of a plugin, but also to allow upgrade of a plugin to create new configuration items for the plugins whilst preserving previous configuration values set by the user.

A sample default configuration of http north python based plugin is shown below.

.. code-block:: json

    {
    	"plugin": {
    		"description": "HTTP North Plugin",
    		"type": "string",
    		"default": "http_north",
    		"readonly": "true"
    	},
    	"url": {
    		"description": "Destination URL",
    		"type": "string",
    		"default": "http://localhost:6683/sensor-reading",
    		"order": "1",
    		"displayName": "URL"
    	},
    	"source": {
    		"description": "Source of data to be sent on the stream. May be either readings or statistics.",
    		"type": "enumeration",
    		"default": "readings",
    		"options": ["readings", "statistics"],
    		"order": "2",
    		"displayName": "Source"
    	},
    	"verifySSL": {
    		"description": "Verify SSL certificate",
    		"type": "boolean",
    		"default": "false",
    		"order": "3",
    		"displayName": "Verify SSL"
    	}
    }

Items marked as *"readonly" :"true"* will not be presented to the user. The *displayName* and *order* properties are only used by the user interface to display the configuration item. The description, type and default are used by the API to verify the input and also set the initial values when a new configuration item is created.

Rules can also be given to the user interface to define the validity of configuration items based upon the values of others, or example

.. code-block:: json

    {
        "applyFilter": {
            "description": "Should filter be applied before processing data",
            "type": "boolean",
            "default": "false",
            "order": "4",
            "displayName": "Apply Filter"
        },
        "filterRule": {
            "description": "JQ formatted filter to apply (only applicable if applyFilter is True)",
            "type": "string",
            "default": ".[]",
            "order": "5",
            "displayName": "Filter Rule",
            "validity": "applyFilter == \"true\""
        }
    }

This will only allow entry to the *filterRule* configuration item if the *applyFilter* item has been set to true.

The plugin_init call
~~~~~~~~~~~~~~~~~~~~

The *plugin_init* call will be invoked after the *plugin_info* call has been called to obtain the information regarding the plugin. This call is designed to allow the plugin to do any initialization that is required and also creates the handle will is used in all subsequent calls to identify the instance of the plugin.

The *plugin_init* is passed a Python DICT as the only argument, this DICT contains the modified configuration for the plugin that is created by taking the default plugin configuration returned by *plugin_info* and adding to that the values the user has configured previously. This is the working configuration that the plugin should use.

The typical implementation of the *plugin_init* call will create an instance of a Python class which is the main body of the plugin. An object will then be returned which is the handle that will be passed into subsequent calls. This handle in a simple plugin, is commonly a Python DICT that is the configuration of the plugin, however any values may be returned. The caller treats the handle as opaque data that it stores and passed to further calls to the plugin, it will never look inside that object or have any expectations as to what is stored within that object.

The *fledge-north-http* plugin implementation of *plugin_init* is shown below as an example

.. code-block:: python

    def plugin_init(data):
        """ Used for initialization of a plugin.

        Args:
            data - Plugin configuration
        Returns:
            Dictionary of a Plugin configuration
        """
        global http_north, config
        http_north = HttpNorthPlugin()
        config = data
        return config

In this case the plugin creates an object that implements the functionality and stores that object in a global variable. This can be done as only one instance of the north plugin exists within a single process. It is however perhaps better practice to return the instance of the class in the handle rather than use a global variable. Using a global is not recommended for filter plugins as multiple instances of a filter may exist within a single process. In this case the plugin uses the configuration as the handle it returns. 

The plugin_send call
~~~~~~~~~~~~~~~~~~~~

The *plugin_send* call is the main entry point of a north plugin, it is used to send set of readings north to the destination system. It is responsible for both the communication to that system and the translation of the internal representation of the reading data to the representation required by the external system.

The communication performed by the *plugin_send* routine should use the Python 3 asynchronous I/O primitives, the definition of the *plugin_send* entry point must also use the *async* keyword.

The *plugin_send* entry point is passed 3 arguments, the plugin handle, the data to send and a stream_id.

.. code-block:: python

   async def plugin_send(handle, payload, stream_id):

The handle is the opaque data returned by the call to *plugin_init* and may be used by the plugin to store data between invocations. The *payload* is a set of readings that should be sent, see below for more details on payload handling. The stream_id is an integer that uniquely identifies the connection from this Fledge instance to the destination system. This id can be used if the plugin needs to have a unique identifier but in most cases can be ignored.

The *plugin_send* call returns three values, a boolean that indicates if any data has been sent, the object id of the last reading sent and the number of readings sent.

The code below is the *plugin_send* entry point for the http north plugin.

.. code-block:: python

    async def plugin_send(handle, payload, stream_id):
        """ Used to send the readings block from north to the configured destination.

        Args:
            handle - An object which is returned by plugin_init
            payload - A List of readings block
            stream_id - An Integer that uniquely identifies the connection from Fledge instance to the destination system
        Returns:
            Tuple which consists of
            - A Boolean that indicates if any data has been sent
            - The object id of the last reading which has been sent
            - Total number of readings which has been sent to the configured destination
        """
        try:
            is_data_sent, new_last_object_id, num_sent = await http_north.send_payloads(payload)
        except asyncio.CancelledError:
            pass
        else:
            return is_data_sent, new_last_object_id, num_sent

The plugin_shutdown call
~~~~~~~~~~~~~~~~~~~~~~~~

The *plugin_shutdown* call is the final entry that is required for Python north plugin, it is called by the north service or task just prior to the task terminating or in a north service if the configuration is allowed, see reconfiguration below. The *plugin_shutdown* call is passed the plugin handle and should perform any cleanup required by the plugin.

.. code-block:: python

   def plugin_shutdown(handle):
       """ Used when plugin is no longer required and will be final call to shutdown the plugin. It should do any necessary cleanup if required.

       Args:
            handle - Plugin handle which is returned by plugin_init
       Returns:
       """

The call should not return any data. Once called the handle should no longer be regarded as valid and no further calls will be made to the plugin using this handle.

Reconfiguration
~~~~~~~~~~~~~~~

Unlike other plugins within Fledge the north plugins do not have a reconfiguration entry point, this is due to the original nature of the north implementation in Fledge which used short lived tasks in order to send data out the north. Each new execution created a new task with new configuration, it was therefore felt that reconfiguration added a complexity to the north plugins that could be avoided.

Since the introduction of the feature that allows the north to be run as an always on service however this has become an issue. It is resolved by closing down the plugin, calling *plugin_shutdown* and then restarting by called *plugin_init* to pass new configuration and retrieve a new plugin handle with that new configuration.

Payload Handling
~~~~~~~~~~~~~~~~

The payload that is passed to the *plugin_send* routine is a Python list of readings, each reading is encoded as a Python DICT. The properties of the reading dict are;

.. list-table::
    :header-rows: 1

    * - Key
      - Description
    * - id
      - The ID of the reading. Each reading is given an integer id that is an increasing value, it is these id values that are used to track how much data is sent via north plugin. One of the returns form the *plugin_send* routine is the id of the last reading that was successfully sent.
    * - asset_code
      - The asset code of the reading. Typical a south service will generate reading for one or more asset codes. These asset codes are used to identify the source of the data. Multiple asset codes may appear in a single block of readings passed to the *plugin_send* routine.
    * - reading
      - A nested Python DICT that stores the actual data points associated to the reading. These reading DICT's will contain a key/value pair for each data point within the asset. The value of this pair is the value of the data point and may be numeric, string, an array, or a nested object.
    * - ts
      - The timestamp when the reading was first seen by the system.
    * - user_ts
      - The timestamp of the data in the reading. This may be the same as *ts* above or in some cases may be a timestamp that has been received from the source of the data itself. This timestamp is the one that should be considered the most accurately represents the timestamp of the data.


A sample payload is shown below.

.. code-block:: python

    [{'reading': {'sinusoid': 0.0}, 'asset_code': 'sinusoid', 'id': 1, 'ts': '2021-09-27 06:55:52.692000+00:00', 'user_ts': '2021-09-27 06:55:49.947058+00:00'},
    {'reading': {'sinusoid': 0.104528463}, 'asset_code': 'sinusoid', 'id': 2, 'ts': '2021-09-27 06:55:52.692000+00:00', 'user_ts': '2021-09-27 06:55:50.947110+00:00'}]


C/C++ Plugins
-------------

The flow of a C/C++ plugin is very similar to that of a Python plugin, the entry points vary slightly compared to Python, mostly for language reasons.

The plugin_info entry point
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *plugin_info* is again the first entry point that will be called, in the case a C/C++ plugin it will return a pointer to a PLUGIN_INFORMATION structure, this structure contains the same elements there are seen in the Python DICT that is returned by Python plugins.

.. code-block:: C

    static PLUGIN_INFORMATION info = {
            PLUGIN_NAME,                    // Name
            VERSION,                        // Version
            0,                              // Flags
            PLUGIN_TYPE_NORTH,              // Type
            "1.0.0",                        // Interface version
            default_config                  // Configuration
    }

It should be noted that the *PLUGIN_INFORMATION* structure instance is declared as static. All global variables declared with a C/C++ plugin should be declared as static as the mechanism for loading the plugins will share global variables between plugins. Using true global variables can create unexpected interactions between plugins.
    
The items are

.. list-table::
    :header-rows: 1
    
    * - Name
      - Description
    * - name
      - The name of the plugin.
    * - version
      - The version of the plugin expressed as a string. This usually but not always matches the current version of Fledge.
    * - flags
      - A bitmap of flags that give extra information about the plugin.
    * - interface
      - The interface version, currently north plugins are at interface version 1.0.0.
    * - config
      - The default configuration for the plugin. In C/C++ plugins this is returned as a string containing the JSON structure.

A number of flags are supported by the plugins, however a small subset are supported in north plugins, this subset consists of

.. list-table::
   :header-rows: 1

   * - Name
     - Description
   * - SP_PERSIST_DATA
     - The plugin persists data and uses the data persistence API extensions.
   * - SP_BUILTIN
     - The plugin is builtin with the Fledge core package. This should not be used for any user added plugins.

A typical implementation of the *plugin_info* entry would merely return the *PLUGIN_INFORMATION* structure for the plugin.

.. code-block:: C

    PLUGIN_INFORMATION *plugin_info()
    {
        return &info;
    }

More complex implementations may tailor the content of the information returned based upon some criteria determined at run time. An example of such a scenario might be to tailor the default configuration based upon some element of discovery that occurs at run time. For example if the plugin is designed to send data to another service the *plugin_info* entry point could perform some service discovery and update a set of options for an enumerated type in the default configuration. This would allow the user interface to give the user a selection list of all the service instances that it found when the plugin was run.

The plugin_init entry point
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *plugin_init* entry point is called once the configuration of the plugin has been constructed by combining the default configuration with any stored configuration that the user has set for the plugin. The configuration is passed as a pointer to a C++ object of class ConfigCategory. This object may then be used to extract data from the configuration.

The *plugin_init* call should be used to initialize the plugin itself and to extract the configuration for the *ConfigCategory* instance and store within the instance of the plugin. Details regarding the use of the *ConfigCategory* class can be found in the C++ Support Class section of the Plugin Developers Guide. Typically the north plugin will create an instance of a class that implements the functionality required, store the configuration in that class and return a pointer to that instance as the handle for the plugin. This will ensure that subsequent calls can access that class instance and the associated state, since all future calls will be passed the handle as an argument.

The following is perhaps the most generic form of the *plugin_init* call. 

.. code-block:: C

    PLUGIN_HANDLE plugin_init(ConfigCategory *configData)
    {
        return (PLUGIN_HANDLE)(new myNorthPlugin(configData));
    }

In this case it assumes we have a class, *myNorthPlugin* that implements the functionality of the plugin. The constructor takes the *ConfigCategory* pointer as an argument and performs all required initialization from that configuration category.

The plugin_send entry point
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *plugin_send* entry point, as with Python plugins already describe, is the heart of a north plugin. It is called with the plugin handle and a block of readings data to be sent north. Typically the *plugin_send* will extract the object created in the *plugin_init* call from the handle and then call the functionality within that object to perform whatever translation and communication logic is required to send the reading data.

.. code-block:: C

   uint32_t plugin_send(PLUGIN_HANDLE handle, std::vector<Reading *>& readings)
   {
        myNorthPlugin *plugin = (myNorthPlugin *)handle;
        return plugin->send(readings);
   }

The block of readings is sent as a C++ standard template library vector of pointers to instance of the Reading class, also covered above in the section on C++ Support Classes.

The return from the *plugin_send* function should be a count of the number of readings sent by the plugin.

The plugin_shutdown entry point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *plugin_shutdown* entry point is called when the plugin is no longer required. It should do any necessary cleanup required. As with other entry points, it is called with the handle that was returned by *plugin_init*. In the case of our simple plugin that might simple be to delete the C++ object that implements the plugin functionality.

.. code-block:: C

   void plugin_shutdown(PLUGIN_HANDLE handle)
   {
        myNorthPlugin *plugin = (myNorthPlugin *)handle;
        delete plugin;
   }

The plugin_register entry point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *plugin_register* entry point is used to pass two function pointers to the plugin. These functions pointers are the functions that should be called when either a set point write or a set point operation is required. The plugin should store these function pointers for later use.

.. code-block:: C

   void plugin_register(PLUGIN_HANDLE handle, (bool ( *write)(char *name, char *value, ControlDestination destination, ...), int (* operation)(char *operation, int paramCount, char *parameters[], ControlDestination destination, ...))
   {
        myNorthPlugin *plugin = (myNorthPlugin *)handle;
        plugin->setpointCallbacks(write, operation);
   }

This call will only be made if the plugin included the *SP_CONTROL* option in the flags field of the *PLUGIN_INFORMATION* structure.

Set Point Control
-----------------

Fledge supports multiple paths for set point control, one of these paths allows for a north service to be bi-directional, with the north plugin receiving a trigger from the system north of Fledge to perform a set point control. This trigger may be the north plugin polling the system or a protocol response from the north.

Set point control is only available for north services, it is not supported for north tasks and will be ignored.

When the north plugin requires a set point write operation to be performed it calls the *write* callback that was passed to the plugin in the *plugin_register* entry point. This callback takes a number of arguments;

  - The name of the set point to be written.

  - The value to write to the set point. This is expressed as a string always.

  - The destination of the write operation. This is passed using the *ControlDestination* enumerated type. Currently this may be one of

      - **DestinationBroadcast**: send the write operation to all south services that support control.

      - **DestinationAsset**: send the write request to the south service responsible for ingesting the given asset. The asset is passed as the next argument in the *write* call.

      - **DestinationService**: send the write request to the named south service.

For example if the north plugin wishes to write the set point called *speed* with the value *28* in the south service called *Motor Control* it would make a call as follows.

.. code-block:: C

       (*m_write)("speed", "28", DestinationService, "Motor Control");

Assuming the member variable *m_write* was used to store the function pointer of the *write* callback.

If the north plugin requires an operation to be performed, rather than a write, then it should call the *operation* called which was passed to it in the *plugin_register* call. This callback takes a set of arguments;

   - The name of the operation to execute.

   - The number of parameters the operation should be passed.

   - An array of parameters, as strings, to pass to the operation

   - The destination of the operation, this is the same set of destinations as per the write call.
