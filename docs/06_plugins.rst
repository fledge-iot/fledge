.. Writing and Using Plugins describes how to implement a plugin for FogLAMP and how to use it

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs


.. =============================================


*************************
Writing and Using Plugins
*************************

FogLAMP makes extensive use of plugin components to extend the base functionality of the platform. In particular, plugins are used to extend the set of sensors and actuators that FogLAMP supports, the set of services to which FogLAMP will push accumulated data gathered from those sensors and the mechanism by which FogLAMP buffers data internally.

This chapter is aimed at those who wish to extend FogLAMP by writing new plugins to support different sensors, protocols, historians and storage devices. It will guide you through the process and entry points that are required for the various different type of plugin.


FogLAMP Plugins
===============


South Microservice Plugins
--------------------------

The FogLAMP South microservice is responsible for communication between FogLAMP and the sensors and actuators it supports. Each instance of a FogLAMP South micro service will use a plugin for the actual communication to the sensors or actuators that that instance of the South microservice supports.


North Plugins
-------------

The FogLAMP North plugins are responsible for taking reading data passed to them from the South bound task and doing any necessary conversion to the data and providing the protocol to send that converted data to a north side service.


Storage Plugins
---------------

FogLAMP Storage plugins sit between the FogLAMP storage microservice and the physical data storage mechanism that stores the FogLAMP configuration and readings data. Storage plugins differ from other plugins in that they interface to a storage system which is written in C/C++ rather than Python, however they share the same common attributes and entry points that the Python based plugins must support.


Common FogLAMP Plugin API
-------------------------

Every plugin provides at least one common API entry point, the *plugin_info* entry point. It is used to obtain information about a plugin before it is initialised and used. It allows FogLAMP to determine what type of plugin it is, e.g. a South bound plugin or a North bound plugin, obtain default configuration information for the plugin and determine version information.


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
          'type': 'device',
          'interface': '1.0',
          'config': _DEFAULT_CONFIG
      }

These are the properties returned by the JSON document:

- **Name** - A textual name that will be used for reporting purposes for this plugin.
- **Version** - This property allows the version of the plugin to be communicated to the plugin loader. This is used for reporting purposes only and has no effect on the way FogLAMP interacts with the plugin.
- **Type** - The type of the plugin, used by the plugin loader to determine if the plugin is being used correctly. The type is a simple string and may be South, North or Storage.

.. note:: If you browse the FogLAMP code you may find old plugins with type *device*: this was the type used to indicate a South plugin and it is now deprecated.

- **Interface** - This property reports the version of the plugin API to which this plugin was written. It allows FogLAMP to support upgrades of the API whilst being able to recognise the version that a particular plugin is compliant with. Currently all interfaces are version 1.0.
- **Configuration** - This allows the plugin to return a JSON document which contains the default configuration of the plugin.  This is in line with the extensible plugin mechanism of FogLAMP, each plugin will return a set of configuration items that it wishes to use, this will then be used to extend the set of FogLAMP configuration items. This structure, a JSON document, includes default values but no actual values for each configuration option. The first time FogLAMP’s configuration manager sees a category it will register the category and create values for each item using the default value in the configuration document. On subsequent calls the value already in the configuration manager will be used. |br| This mechanism allows the plugin to extend the set of configuration variables whilst giving the user the opportunity to modify the value of these configuration items. It also allow new versions of plugins to add new configuration items whilst retaining the values of previous items. And new items will automatically be assigned the default value for that item. |br| As an example, a plugin that wishes to maintain two configuration variables, say a GPIO pin to use and a polling interval, would return a configuration document that looks as follows:

.. code-block:: json

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


Plugin Initialization
---------------------

The plugin initialization is called after the service that has loaded the plugin has collected the plugin information and resolved the configuration of the plugin but before any other calls will be made to the plugin. The initialization routine is called with the resolved configuration of the plugin, this includes values as opposed to the defaults that were returned in the *plugin_info* call.

This call is used by the plugin to do any initialization or state creation it needs to do. The call returns a handle which will be passed into each subsequent call of the plugin. The handle allows the plugin to have state information that is maintained and passed to it whilst allowing for multiple instances of the same plugin to be loaded by a service if desired. It is equivalent to a this or self pointer for the plugin, although the plugin is not defined as a class.

In a simple example of a sensor that reads a GPIO pin for data, we might choose to use that configured GPIO pin as the handle we pass to other calls. 

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


Plugin Reconfigure
------------------

The plugin reconfigure method is called whenever the configuration of the plugin is changed. It allows for the dynamic reconfiguration of the plugin whilst it is running. The method is called with the handle of the plugin and the updated configuration document. The plugin should take whatever action it needs to and return a new or updated copy of the handle that will be passed to future calls.

Using a simple example of our sensor reading a GPIO pin, we extract the new pin number from the new configuration data and return that as the new handle for the plugin instance.

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


Plugin shutdown
---------------

The plugin shutdown method is called as part of the shutdown sequence of the service that loaded the plugin. It gives the plugin the opportunity to do any cleanup operations before terminating. As with all calls it is passed the handle of our plugin instance. Plugins can not prevent the shutdown and do not have to implement any actions. In our simple sensor example there is nothing to do in order to shutdown the plugin.
      

South Plugins
=============

South plugins are used to communicate with sensors and actuators, there are two modes of plugin operation; *asyncio* and *polled*.


Polled Mode
-----------

Polled mode is the simplest form of South plugin that can be written, a poll routine is called at an interval defined in the plugin configuration. The South service determines the type of the plugin by examining at the mode property in the information the plugin returns from the *plugin_info* call.


Plugin Poll
~~~~~~~~~~~

The plugin *poll* method is called periodically to collect the readings from a poll mode sensor. As with all other calls the argument passed to the method is the handle returned by the initialization call, the return of the method should be the JSON payload of the readings to return.

The JSON payload returned, as a Python dictionary, should contain the properties; asset, timestamp, key and readings.

+-----------+-------------------------------------------------------+
| Property  | Description                                           |
+===========+=======================================================+
| asset     | The asset key of the sensor device that is being read |
+-----------+-------------------------------------------------------+
| timestamp | A timestamp for the reading data                      |
+-----------+-------------------------------------------------------+
| key       | A UUID which is the unique key of this reading        |
+-----------+-------------------------------------------------------+
| readings  | The reading data itself as a JSON object              |
+-----------+-------------------------------------------------------+

It is important that the *poll* method does not block as this will prevent the proper operation of the South microservice. 
Using the example of our simple DHT11 device attached to a GPIO pin, the *poll* routine could be:

.. code-block:: python

  def plugin_poll(handle):
      """ Extracts data from the sensor and returns it in a JSON document as a Python dict.

      Available for poll mode only.

      Args:
          handle: handle returned by the plugin initialisation call
      Returns:
          returns a sensor reading in a JSON document, as a Python dict, if it is available
          None - If no reading is available
      Raises:
          DataRetrievalError
      """


      try:
          humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, handle)
          if humidity is not None and temperature is not None:
              time_stamp = str(datetime.now(tz=timezone.utc))
              readings =  { 'temperature': temperature , 'humidity' : humidity }
              wrapper = {
                      'asset':     'dht11',
                      'timestamp': time_stamp,
                       'key':       str(uuid.uuid4()),
                      'readings':  readings
              }
              return wrapper
          else:
              return None

      except Exception as ex:
          raise exceptions.DataRetrievalError(ex)

      return None


Async IO Mode
-------------

In asyncio mode the plugin inserts itself into the event processing loop of the South server itself. This is a more complex mechanism and is intended for plugins that need to block or listen for incoming data via a network.


