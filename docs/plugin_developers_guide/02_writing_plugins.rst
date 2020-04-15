.. Writing and Using Plugins describes how to implement a plugin for Fledge and how to use it
.. https://docs.google.com/document/d/1IKGXLWbyN6a7vx8UO3uDbq5Df0VvE4oCQIULgZVZbjM

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. =============================================


Writing and Using Plugins
=========================

A plugin has a small set of external entry points that must exist in order for Fledge to load and execute that plugin. Currently plugins may be written in either Python or C/C++, the set of entry points is the same for both langauges. The entry points detailed here will be presented for both langauages, a more indepth discussion of writing plugins in C/C++ will then follow.

Common Fledge Plugin API
-------------------------

Every plugin provides at least one common API entry point, the *plugin_info* entry point. It is used to obtain information about a plugin before it is initialised and used. It allows Fledge to determine what type of plugin it is, e.g. a South bound plugin or a North bound plugin, obtain default configuration information for the plugin and determine version information.


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

- **Name** - A textual name that will be used for reporting purposes for this plugin.
- **Version** - This property allows the version of the plugin to be communicated to the plugin loader. This is used for reporting purposes only and has no effect on the way Fledge interacts with the plugin.
- **Type** - The type of the plugin, used by the plugin loader to determine if the plugin is being used correctly. The type is a simple string and may be South, North, Storage, Filter, Rule or Delivery.

.. note:: If you browse the Fledge code you may find old plugins with type *device*: this was the type used to indicate a South plugin and it is now deprecated.

- **Interface** - This property reports the version of the plugin API to which this plugin was written. It allows Fledge to support upgrades of the API whilst being able to recognise the version that a particular plugin is compliant with. Currently all interfaces are version 1.0.
- **Configuration** - This allows the plugin to return a JSON document which contains the default configuration of the plugin.  This is in line with the extensible plugin mechanism of Fledge, each plugin will return a set of configuration items that it wishes to use, this will then be used to extend the set of Fledge configuration items. This structure, a JSON document, includes default values but no actual values for each configuration option. The first time Fledge’s configuration manager sees a category it will register the category and create values for each item using the default value in the configuration document. On subsequent calls the value already in the configuration manager will be used. |br| This mechanism allows the plugin to extend the set of configuration variables whilst giving the user the opportunity to modify the value of these configuration items. It also allow new versions of plugins to add new configuration items whilst retaining the values of previous items. And new items will automatically be assigned the default value for that item. |br| As an example, a plugin that wishes to maintain two configuration variables, say a GPIO pin to use and a polling interval, would return a configuration document that looks as follows:

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

It should also be observed in the abovbe example that in C/C++ the *plugin_init* call is passed a pointer to a *ConfigCategory* class that encapsulates the JSON configuration category for the plugin. Details of the ConfigCategory class are available below.

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
------------------

The plugin reconfigure method is called whenever the configuration of the plugin is changed. It allows for the dynamic reconfiguration of the plugin whilst it is running. The method is called with the handle of the plugin and the updated configuration document. The plugin should take whatever action it needs to and return a new or updated copy of the handle that will be passed to future calls.

The plugin reconfigure method is shared between most but not all plugin types. In particular it does not exist for the shorted lived plugins that are created to perform a single operstion and then terminated. These are the north plugins and the notification delivery plugins.

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


In C/C++ the *plugin_reconfigure* class is very similar, note however that the *plugin_reconfigure* call is passed the JSON configuration category as a string and not a *ConfigCategory*, it is easy to parse and create the C++ class however, a name for the category must be given however.

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

It is worth noting, that the *plugin_reconfigure* call may be delivered in a seperate thread for a C/C++ plugin and that the plugin should implement any mutual exclusion mechanisms that are required based on the actions of the *plugin_reconfigure* method.
