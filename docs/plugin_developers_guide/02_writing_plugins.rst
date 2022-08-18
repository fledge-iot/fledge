.. Writing and Using Plugins describes how to implement a plugin for Fledge and how to use it
.. https://docs.google.com/document/d/1IKGXLWbyN6a7vx8UO3uDbq5Df0VvE4oCQIULgZVZbjM

.. |br| raw:: html

   <br />

.. Images

.. Links
.. |C++ Support Classes| raw:: html

   <a href="035_CPP.html">C++ Support Classes</a>

.. Links in new tabs

.. =============================================


Writing and Using Plugins
=========================

A plugin has a small set of external entry points that must exist in order for Fledge to load and execute that plugin. Currently plugins may be written in either Python or C/C++, the set of entry points is the same for both languages. The entry points detailed here will be presented for both languages, a more in depth discussion of writing plugins in C/C++ will then follow.

Common Fledge Plugin API
-------------------------

Every plugin provides at least one common API entry point, the *plugin_info* entry point. It is used to obtain information about a plugin before it is initialized and used. It allows Fledge to determine what type of plugin it is, e.g. a South bound plugin or a North bound plugin, obtain default configuration information for the plugin and determine version information.


Plugin Information
~~~~~~~~~~~~~~~~~~

The information entry point is implemented as a call, *plugin_info*, that takes no arguments. Data is returned from this API call as a JSON document with certain well known properties.

A typical Python implementation of this would simply return a fixed dictionary object that encodes the required properties.

.. code-block:: python

  def plugin_info():
      """ Returns information about the plugin.

      Args:
      Returns:
          dict: plugin information
      Raises:
      """

      return {
          'name': 'DHT11 GPIO',
          'version': '1.0',
          'mode': 'poll',
          'type': 'south',
          'interface': '1.0',
          'config': _DEFAULT_CONFIG
      }

These are the properties returned by the JSON document:

- **name** - A textual name that will be used for reporting purposes for this plugin.
- **version** - This property allows the version of the plugin to be communicated to the plugin loader. This is used for reporting purposes only and has no effect on the way Fledge interacts with the plugin.
- **mode** - A set of options that defines how the plugin operates. Multiple values can be given, the different options are separated from each other using the | symbol.
- **type** - The type of the plugin, used by the plugin loader to determine if the plugin is being used correctly. The type is a simple string and may be *south*, *north*,  *filter*, *rule* or *delivery*.

.. note:: If you browse the Fledge code you may find old plugins with type *device*: this was the type used to indicate a South plugin and it is now deprecated.

- **interface** - This property reports the version of the plugin API to which this plugin was written. It allows Fledge to support upgrades of the API whilst being able to recognise the version that a particular plugin is compliant with. Currently all interfaces are version 1.0.
- **configuration** - This allows the plugin to return a JSON document which contains the default configuration of the plugin.  This is in line with the extensible plugin mechanism of Fledge, each plugin will return a set of configuration items that it wishes to use, this will then be used to extend the set of Fledge configuration items. This structure, a JSON document, includes default values but no actual values for each configuration option. The first time Fledge’s configuration manager sees a category it will register the category and create values for each item using the default value in the configuration document. On subsequent calls the value already in the configuration manager will be used. |br| This mechanism allows the plugin to extend the set of configuration variables whilst giving the user the opportunity to modify the value of these configuration items. It also allow new versions of plugins to add new configuration items whilst retaining the values of previous items. And new items will automatically be assigned the default value for that item. |br| As an example, a plugin that wishes to maintain two configuration variables, say a GPIO pin to use and a polling interval, would return a configuration document that looks as follows:

.. code-block:: console

  {
      'pollInterval': {
          'description': 'The interval between poll calls to the device poll routine expressed in milliseconds.',
          'type': 'integer',
          'default': '1000'
      },
      'gpiopin': {
          'description': 'The GPIO pin into which the DHT11 data pin is connected',
          'type': 'integer',
          'default': '4'
      }
  }


The various values that may appear in the *mode* item are shown in the table below

+---------+---------------------------------------------------------------------------------------+
| Mode    | Description                                                                           |
+=========+=======================================================================================+
| poll    | The plugin is a polled plugin and *plugin_poll* will be called periodically to obtain |
|         | new values.                                                                           |
+---------+---------------------------------------------------------------------------------------+
| async   | The plugin is an asynchronous plugin, *plugin_poll* will not be called and the        |
|         | plugin will be supplied with a callback function that it calls each time it has a     |
|         | new value to pass to the system. The *plugin_register_ingest* entry point will be     |
|         | called to register the callback with the plugin. The *plugin_start* call will be      |
|         | called once to initiate the asynchronous delivery of data.                            |
+---------+---------------------------------------------------------------------------------------+
| none    | This is equivalent to poll.                                                           |
+---------+---------------------------------------------------------------------------------------+
| control | The plugin support a control flow to the device the plugin is connected to. The       |
|         | must supply the control entry points *plugin_write* and *plugin_operation*.           |
+---------+---------------------------------------------------------------------------------------+

|br|

A C/C++ plugin returns the same information as a structure, this structure includes the JSON configuration document as a simple C string.

.. code-block:: C

  #include <plugin_api.h>

  extern "C" {

  /**
   * The plugin information structure
   */
  static PLUGIN_INFORMATION info = {
          "MyPlugin",               // Name
          "1.0.1",                  // Version
          0,    		    // Flags
          PLUGIN_TYPE_SOUTH,        // Type
          "1.0.0",                  // Interface version
          default_config            // Default configuration
  };

  /**
   * Return the information about this plugin
   */
  PLUGIN_INFORMATION *plugin_info()
  {
          return &info;
  }

In the above example the constant *default_config* is a string that contains the JSON configuration document. In order to make the JSON easier to manage a special macro is defined in the *plugin_api.h* header file. This macro is called *QUOTE* and is designed to ease the quoting requirements to create this JSON document.

.. code-block:: C

  const char *default_config = QUOTE({
                "plugin" : {
                        "description" : "My example plugin in C++",
                        "type" : "string",
                        "default" : "MyPlugin",
                        "readonly" : "true"
                        },
                 "asset" : {
                        "description" : "The name of the asset the plugin will produce",
                        "type" : "string",
                        "default" : "MyAsset"
                        }
  });

The *flags* items contains a bitmask of flag values used to pass information regarding the behavior and requirements of the plugin. The flag values currently supported are shown below

+-------------------+---------------------------------------------------------------------------------+
| Flag Name         | Description                                                                     |
+===================+=================================================================================+
| SP_COMMON         | Used exclusively by storage plugins. The plugin supports the common table       |
|                   | access needed to store configuration                                            |
+-------------------+---------------------------------------------------------------------------------+
| SP_READINGS       | Used exclusively by storage plugins. The plugin supports the storage of reading |
|                   | data                                                                            |
+-------------------+---------------------------------------------------------------------------------+
| SP_ASYNC          | The plugin is an asynchronous plugin, *plugin_poll* will not be called and the  |
|                   | plugin will be supplied with a callback function that it calls each time it has |
|                   | a new value to pass to the system. The *plugin_register_ingest* entry point will|
|                   | be called to register the callback with the plugin. The *plugin_start* call will|
|                   | be called once to initiate the asynchronous delivery of data. This applies      |
|                   | only to south plugins.                                                          |
+-------------------+---------------------------------------------------------------------------------+
| SP_PERSIST_DATA   | The plugin wishes to persist data between executions                            |
+-------------------+---------------------------------------------------------------------------------+
| SP_INGEST         | A non-south plugin wishes to ingest new data into the system. Used by           |
|                   | notification plugins                                                            |
+-------------------+---------------------------------------------------------------------------------+
| SP_GET_MANAGEMENT | The plugin requires access to the management API interface for the service      |
+-------------------+---------------------------------------------------------------------------------+
| SP_GET_STORAGE    | The plugin requires access to the storage service                               |
+-------------------+---------------------------------------------------------------------------------+
| SP_DEPRECATED     | The plugin should be considered to be deprecated. New service can not use this  |
|                   | plugin, but existing services may continue to use it                            |
+-------------------+---------------------------------------------------------------------------------+
| SP_BUILTIN        | The plugin is not implemented as an external package but is built into the      |
|                   | system                                                                          |
+-------------------+---------------------------------------------------------------------------------+
| SP_CONTROL        | The plugin implement control features                                           |
+-------------------+---------------------------------------------------------------------------------+

These flag values may be combined by use of the or operator where more than one of the above options is supported.

Plugin Initialization
~~~~~~~~~~~~~~~~~~~~~

The plugin initialization is called after the service that has loaded the plugin has collected the plugin information and resolved the configuration of the plugin but before any other calls will be made to the plugin. The initialization routine is called with the resolved configuration of the plugin, this includes values as opposed to the defaults that were returned in the *plugin_info* call.

This call is used by the plugin to do any initialization or state creation it needs to do. The call returns a handle which will be passed into each subsequent call of the plugin. The handle allows the plugin to have state information that is maintained and passed to it whilst allowing for multiple instances of the same plugin to be loaded by a service if desired. It is equivalent to a this or self pointer for the plugin, although the plugin is not defined as a class.

In Python a simple example of a sensor that reads a GPIO pin for data, we might choose to use that configured GPIO pin as the handle we pass to other calls. 

.. code-block:: python

  def plugin_init(config):
      """ Initialise the plugin.
   
      Args:
          config: JSON configuration document for the device configuration category
      Returns:
          handle: JSON object to be used in future calls to the plugin
      Raises:
      """
   
      handle = config['gpiopin']['value']
      return handle

A C/C++ plugin should return a value in a *void* pointer that can then be dereferenced in subsequent calls.  A typical C++ implementation might create an instance of a class and use that instance as the handle for the plugin.

.. code-block:: C
  
  /**
   * Initialise the plugin, called to get the plugin handle
   */
  PLUGIN_HANDLE plugin_init(ConfigCategory *config)
  {
  MyPluginClass *plugin = new MyPluginClass();

          plugin->configure(config);

          return (PLUGIN_HANDLE)plugin;
  }

It should also be observed in the above C/C++ example the *plugin_init* call is passed a pointer to a *ConfigCategory* class that encapsulates the JSON configuration category for the plugin. Details of the ConfigCategory class are available in the section |C++ Support Classes|.

|br|


Plugin Shutdown
~~~~~~~~~~~~~~~

The plugin shutdown method is called as part of the shutdown sequence of the service that loaded the plugin. It gives the plugin the opportunity to do any cleanup operations before terminating. As with all calls it is passed the handle of our plugin instance. Plugins can not prevent the shutdown and do not have to implement any actions. In our simple sensor example there is nothing to do in order to shutdown the plugin.
      
A C/C++ plugin might use this *plugin_shutdown* call to delete the plugin class instance it created in the corresponding *plugin_init* call.

.. code-block:: C

  /**
   * Shutdown the plugin
   */
  void plugin_shutdown(PLUGIN_HANDLE *handle)
  {
  MyPluginClass *plugin = (MyPluginClass *)handle;

          delete plugin;
  }


|br|


Plugin Reconfigure
~~~~~~~~~~~~~~~~~~

The plugin reconfigure method is called whenever the configuration of the plugin is changed. It allows for the dynamic reconfiguration of the plugin whilst it is running. The method is called with the handle of the plugin and the updated configuration document. The plugin should take whatever action it needs to and return a new or updated copy of the handle that will be passed to future calls.

The plugin reconfigure method is shared between most but not all plugin types. In particular it does not exist for the shorted lived plugins that are created to perform a single operation and then terminated. These are the north plugins and the notification delivery plugins.

Using a simple Python example of our sensor reading a GPIO pin, we extract the new pin number from the new configuration data and return that as the new handle for the plugin instance.

.. code-block:: python

  def plugin_reconfigure(handle, new_config):
      """ Reconfigures the plugin, it should be called when the configuration of the plugin is changed during the
          operation of the device service.
          The new configuration category should be passed.

      Args:
          handle: handle returned by the plugin initialisation call
          new_config: JSON object representing the new configuration category for the category
      Returns:
          new_handle: new handle to be used in the future calls
      Raises:
      """

      new_handle = new_config['gpiopin']['value']
      return new_handle


In C/C++ the *plugin_reconfigure* method is very similar, note however that the *plugin_reconfigure* call is passed the JSON configuration category as a string and not a *ConfigCategory*, it is easy to parse and create the C++ class however, a name for the category must be given however.

.. code-block:: C

  /**
   * Reconfigure the plugin
   */
  void plugin_reconfigure(PLUGIN_HANDLE *handle, string& newConfig)
  {
  ConfigCategory	config("newConfiguration", newConfig);
  MyPluginClass		*plugin = (MyPluginClass *)*handle;

          plugin->configure(&config);
  }

It should be noted that the *plugin_reconfigure* call may be delivered in a separate thread for a C/C++ plugin and that the plugin should implement any mutual exclusion mechanisms that are required based on the actions of the *plugin_reconfigure* method.

Configuration Lifecycle
-----------------------

Fledge has a very particular way of handling configuration, there are a number of design aims that have resulted in the configuration system within Fledge.

  - A desire to allow the plugins to define their own configuration elements.

  - Dynamic configuration that allows for maximum uptime during configuration changes.

  - A descriptive way to define the configuration such that user interfaces can be built without prior knowledge of the elements to be configured.

  - A common approach that will work across many different languages.

Fledge divides its configuration in categories. A category being a collection of configuration items. A category is also the smallest item of configuration that can be subscribed to by the code. This subscription mechanism is they way that Fledge facilitates dynamic reconfiguration. It allows a service to subscribe to one or more configuration categories, whenever an item within a category changes the central configuration manager will call a handler to pass the newly updated configuration category. This handler may be within a services or between services using the micro service management API that every service must support. The mechanism however is transparent to the code involved.

The configuration items within a category are JSON object, the object key is the name of the configuration item, the object itself contains data about that item. As an example, if we wanted to have a configuration item called *MaxRetries* that is an integer with a default value of 5, then we would configured it using the JSON object

.. code-block:: console

   "MaxRetries" : {
                "type" : "integer",
                "default" : "5"
                }

We have used the properties *type* and *default* to define properties of the configuration item *MaxRetries*.  These are not the only properties that a configuration item can have, the full set of properties are

.. list-table::
   :header-rows: 1

   * - Property
     - Description
   * - default
     - The default value for the configuration item. This is always expressed as a string regardless of the type of the configuration item.
   * - deprecated
     - A boolean flag to indicate that this item is no longer used and will be removed in a future release.
   * - description
     - A description of the configuration item used in the user interface to give more details of the item. Commonly used as a mouse over help prompt.
   * - displayName
     - The string to use in the user interface when presenting the configuration item. Generally a more user friendly form of the item name. Item names are referenced within the code.
   * - length
     - The maximum length of the string value of the item.
   * - mandatory
     - A boolean flag to indicate that this item can not be left blank.
   * - maximum
     - The maximum value for a numeric configuration item.
   * - minimum
     - The minimum value for a numeric configuration item.
   * - options
     - Only used for enumeration type elements. This is a JSON array of string that contains the options in the enumeration.
   * - order
     - Used in the user interface to give an indication of how high up in the dialogue to place this item.
   * - readonly
     - A boolean property that can be used to include items that can not be altered by the API.
   * - rule
     - A validation rule that will be run against the value. This must evaluate to true for the new value to be accepted by the API
   * - type
     - The type of the configuration item. The list of types supported are; integer, float, string, password, enumeration, boolean, JSON, URL, IPV4, IPV6, script, code, X509 certificate and northTask.
   * - validity
     - An expression used to determine if the configuration item is valid. Used in the UI to gray out one value based on the value of others.
   * - value
     - The current value of the configuration item. This is not included when defining a set of default configuration in, for example, a plugin.

Of the above properties of a configuration item *type*, *default* and *description* are mandatory, all other may be omitted.

Configuration data is stored by the storage service and is maintained by the configuration in the core Fledge service. When code requires configuration it would create a configuration category with a set of items as a JSON document. It would then register that configuration category with the configuration manager. The configuration manager is responsible for storing the data in the storage layer, as it does this it first checks to see if there is already a configuration category from a previous execution of the code. If one does exist then the two are merged, this merging process allows updates to the software to extend the configuration category whilst maintaining any changes in values made by the user.

Dynamic reconfiguration within Fledge code is supported by allowing code to subscribe for changes in a configuration category. The services that load plugin will automatically register for the plugin configuration category and when changes are seen will call the *plugin_reconfigure* entry point of the plugin with the new configuration. This allows the plugins to receive the updated configuration and take what actions it must in order to honour the changes to configuration. This allows for configuration to be changed without the need to stop and restart the services, however some plugins may need to close connections and reopen them, which may cause a slight interruption in the process of gathering data. That choice is up to the developers of the individual plugins.

Discovery
~~~~~~~~~

It is possible using this system to do a limited amount of discovery and tailoring of plugin configuration. A typical case when discovery might be used is to discover devices on a network that can be monitored. This can be achieved by putting the discovery code in the *plugin_info* entry point and having that discovery code alter the default configuration that is returned as part of the plugin information structure.

Any example of this might be to have an enumeration in the configuration that enumerates the devices to be monitored. The discovery code would then populate the enumerations options item with the various devices it discovered when the *plugin_info* call was made.

An example of the *plugin_info* entry point that does this might be as follows

.. code-block:: C

    /**
     * Return the information about this plugin
     */
    PLUGIN_INFORMATION *plugin_info()
    {
    DeviceDiscovery discover;

            char *config = discover.discover(default_config, "discovered");
            info.config = config;
            return &info;
    }

The configuration in *default_config* is assumed to have an enumeration item called *discovered*

.. code-block:: console

        "discovered" : {
                "description" : "The discovered devices, select 'Manual' to manually enter an IP address",
                "type" : "enumeration",
                "options" : [ "Manual" ],
                "default" : "Manual",
                "displayName": "Devices",
                "mandatory": "true",
                "order" : "2"
                },
        "IP" : {
                "description" : "The IP address of your device, used to add a device that could not be discovered",
                "type" : "string",
                "default" : "127.0.0.1",
                "displayName": "IP Address",
                "mandatory": "true",
                "order" : "3",
                "validity" : "discovered == \"Manual\""
                },

Note the use of the *Manual* option to allow entry of devices that could not be discovered.

The *discover* method does the actually discovery and manipulates the JSON configuration to add the the *options* element of the configuration item.

The code that connects to the device should then look at the *discovered* configuration item, if it finds it set to *Manual* then it will get an IP address from the *IP* configuration item. Otherwise it uses the information in the *discovered* item to connect, note that this need not just be an IP address, you can format the data in a way that is more user friendly and have the connection code extract what it needs or create a table in the *discover* method to allow for user meaningful strings to be mapped to network addresses.

The example here was written in C++, there is nothing that is specific to C++ however and the same approach can be taken in Python.

One thing to note however, the *plugin_info* call is used in the display of available plugins, discovery code that is very slow will impact the performance of plugin selection.
