.. Writing and Using Plugins describes how to implement a plugin for FogLAMP and how to use it
.. https://docs.google.com/document/d/1IKGXLWbyN6a7vx8UO3uDbq5Df0VvE4oCQIULgZVZbjM

.. |br| raw:: html

   <br />

.. Images

.. |DHT11 in PI| image:: https://s3.amazonaws.com/foglamp/readthedocs/images/06_dht11_tags_in_PI.jpg
   :target: https://s3.amazonaws.com/foglamp/readthedocs/images/06_dht11_tags_in_PI.jpg 

.. Links
.. _here: 05_testing.html#setting-the-omf-translator-plugin
.. _these steps: 04_installation.html

.. |Getting Started| raw:: html

   <a href="03_getting_started.html#building-foglamp">here</a>

.. Links in new tabs

.. |ADAFruit| raw:: html

   <a href="https://github.com/adafruit/Adafruit_Python_DHT" target="_blank">ADAFruit DHT Library</a>

.. |here BT| raw:: html

   <a href="https://bugs.launchpad.net/snappy/+bug/1674509" target="_blank">here</a>

.. |DHT Description| raw:: html

   <a href="http://www.aosong.com/en/products/details.asp?id=109" target="_blank">DHT11 Product Description</a>

.. |DHT Manual| raw:: html

   <a href="https://s3.amazonaws.com/foglamp/docs/v1/Common/plugins/South/DHT11/DHT11.pdf" target="_blank">DHT11 Product Manual</a>

.. |DHT Resistor| raw:: html

   <a href="https://s3.amazonaws.com/foglamp/docs/v1/Common/plugins/South/DHT11/DHT11-with-resistor.jpg" target="_blank">This picture</a>

.. |DHT Wired| raw:: html

   <a href="https://s3.amazonaws.com/foglamp/docs/v1/Common/plugins/South/DHT11/DHT11-RaspPI-wired.jpg" target="_blank">This picture</a>

.. |DHT Pins| raw:: html

   <a href="https://s3.amazonaws.com/foglamp/docs/v1/Common/plugins/South/DHT11/DHT11-RaspPI-pins.jpg" target="_blank">this</a>

.. |GPIO| raw:: html

   <a href="https://www.raspberrypi.org/documentation/usage/gpio-plus-and-raspi2/README.md" target="_blank">here</a>


.. =============================================


*******
Plugins
*******

FogLAMP makes extensive use of plugin components to extend the base functionality of the platform. In particular, plugins are used to extend the set of sensors and actuators that FogLAMP supports, the set of services to which FogLAMP will push accumulated data gathered from those sensors and the mechanism by which FogLAMP buffers data internally.

This chapter presents the plugins available in FogLAMP, how to write and use new plugins to support different sensors, protocols, historians and storage devices. It will guide you through the process and entry points that are required for the various different type of plugin.


FogLAMP Plugins
===============

In this version of FogLAMP you have three types of plugins:

- **South Microservice Plugins** - They are responsible for communication between FogLAMP and the sensors and actuators they support. Each instance of a FogLAMP South microservice will use a plugin for the actual communication to the sensors or actuators that that instance of the South microservice supports.
- **North Plugins** - They are responsible for taking reading data passed to them from the South bound task and doing any necessary conversion to the data and providing the protocol to send that converted data to a north-side service.
- **Storage Plugins** - They sit between the Storage microservice and the physical data storage mechanism that stores the FogLAMP configuration and readings data. Storage plugins differ from other plugins in that they interface to a storage system which is written in C/C++ rather than Python, however they share the same common attributes and entry points that the Python based plugins must support.


Plugins in this version of FogLAMP
----------------------------------

This version of FogLAMP provides the following plugins:

+---------+------------+-----------------------------+----------------------------+----------------------------------------+
| Type    | Name       | Description                 | Availability               | Notes                                  |
+=========+============+=============================+============================+========================================+
| Storage | Postgres   | PostgreSQL storage |br|     | Ubuntu: x86 |br|           |                                        |
|         |            | for data and metadata       | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |                             | Raspbian                   |                                        |
+---------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | COAP       | CoAP Listener               | Ubuntu: x86 |br|           |                                        |
|         |            |                             | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |                             | Raspbian                   |                                        |
+---------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | CC2650POLL | TI SensorTag CC2650 |br|    | Ubuntu: x86 |br|           | It requires BLE support. |br|          |
|         |            | in polling mode             | Ubuntu Core: x86, ARM |br| | There are issues with Ubuntu Core |br| |
|         |            |                             | Raspbian                   | on ARM, reported |here BT|             |
+---------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | CC2650ASYN | TI SensorTag CC2650 |br|    | Ubuntu: x86 |br|           | It requires BLE support. |br|          |
|         |            | asynchronous |br|           | Ubuntu Core: x86, ARM |br| | There are issues with Ubuntu Core |br| |
|         |            | (listening) mode            | Raspbian                   | on ARM, reported |here BT|.            |
+---------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | HTTP_SOUTH | HTTP Listener               | Ubuntu: x86  |br|          |                                        |
|         |            |                             | Ubuntu Core: x86, ARM |br| |                                        |
|         |            |                             | Raspbian                   |                                        |
+---------+------------+-----------------------------+----------------------------+----------------------------------------+
| South   | dht11pi    | Wired DHT11 Sensor |br|     | Ubuntu Core: ARM |br|      | It requires the |ADAFruit|. |br|       |
|         |            | in polling mode             | Raspbian                   | The plugin is still experimental.      |
+---------+------------+-----------------------------+----------------------------+----------------------------------------+
| North   | OMF        | OSIsoft Message Format |br| | Ubuntu: x86 |br|           | It works with PI Connector |br|        |
|         |            | sender to PI Connector |br| | Ubuntu Core: x86, ARM |br| | Relay OMF 1.0 and 1.2.                 |
|         |            | Relay OMF                   | Raspbian                   |                                        |
+---------+------------+-----------------------------+----------------------------+----------------------------------------+

|br|


Writing and Using Plugins
=========================

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
          'type': 'south',
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


Plugin Shutdown
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


Plugin Start
~~~~~~~~~~~~

The *plugin_start* method, as with other plugin calls, is called with the plugin handle data that was returned from the *plugin_init* call. The *plugin_start* call will only be called once for a plugin, it is the responsibility of *plugin_start* to install the plugin code into the python event handling system for asyncIO. Assuming an example whereby the interface to a sensor is via HTTP and the sensor will make HTTP POST calls to our plugin in order to send data into FogLAMP, a *plugin_start* for this scenario would create a web application endpoint for reception of the POST command.

.. code-block:: python

  loop = asyncio.get_event_loop()
 
  app = web.Application( middlewares=[middleware.error_middleware] )
  app.router.add_route( 'POST', '/', SensorPhoneIngest.render_post )
  handler = app.make_handler()
  coro = loop.create_server( handler, host, port )
  server = asyncio.ensure_future( coro )

This code first gets the event loop for this Python execution, it then creates the web application and adds a route for the POST request. In this case it is calling the *render_post* method of the object *SensorPhone*. It then goes on to create the handler and install the web server instance into the event system.


Async Handler
~~~~~~~~~~~~~

The async handler is defined for incoming message has the responsibility of taking the sensor data and ingesting that into FogLAMP. Unlike the poll mechanism, this is done from within the handler rather than by passing the data back to the South service itself. A convenient method exists for ingesting readings, *Ingest.add_readings*. This call is passed an asset, timestamp, key and readings document for the asset and will do everything else required to make sure the readings are stored in the FogLAMP buffer. |br| In the case of our HTTP based example above, the code would create the items needed to generate the arguments to the *Ingest.add_readings* call, by creating data items and retrieving them from the payload sent by the sensor.

.. code-block:: python

  try:
      if not Ingest.is_available():
          increment_discarded_counter = True
          message = {'busy': True}
      else:
          payload = await request.json()

          asset = 'SensorPhone'
          timestamp = str(datetime.now(tz=timezone.utc))
          messages = payload.get('messages')

          if not isinstance(messages, list):
                  raise ValueError('messages must be a list')

          for readings in messages:
               key = str(uuid.uuid4())
  await Ingest.add_readings(asset=asset, timestamp=timestamp, key=key, readings=readings)

  except ...

It would then respond to the HTTP request and return. Since the handler is embedded in the event loop this will happen in the context of a coroutine and would happen each time a new POST request is received.

.. code-block:: python

  message['status'] = code
  return web.json_response(message)
 

A South Plugin Example: the DHT11 Sensor
========================================

Let's try to put all the information together and write a plugin. We can continue to use the example of an inexpensive sensor, the DHT11, used to measure temperature and humidity, directly wired to a Raspberry PI. This plugin is also available in the FogLAMP project on GitHub, in the *contrib* folder.

First, here is a set of links where you can find more information regarding this sensor:

- |DHT Description|
- |DHT Manual|
- |ADAFruit|


The Hardware
------------

The DHT sensor is directly connected to a Raspberry PI 2 or 3. You may decide to buy a sensor and a resistor and solder them yourself, or you can buy a ready-made circuit that provides the correct output to wire to the Raspberry PI. |DHT Resistor| shows a DHT11 with resistor that you can buy online.

The sensor can be directly connected to the Raspberry PI GPIO (General Purpose Input/Output). An introduction to the GPIO and the pinset is available |GPIO|. In our case, you must connect the sensor on these pins:

- **VCC** is connected to PIN #2 (5v Power)
- **GND** is connected to PIN #6 (Ground)
- **DATA** is connected to PIN #7 (BCM 4 - GPCLK0)

|DHT Wired| shows the sensor wired to the Raspberry PI and |DHT Pins| is a zoom into the wires used.


The Software
------------

For this plugin we use the ADAFruit Python Library (links to the GitHub repository are above). First, you must install the library (in future versions the library will be provided in a ready-made package):

.. code-block:: console
 
  $ git clone https://github.com/adafruit/Adafruit_Python_DHT.git
  Cloning into 'Adafruit_Python_DHT'...
  remote: Counting objects: 249, done.
  remote: Total 249 (delta 0), reused 0 (delta 0), pack-reused 249
  Receiving objects: 100% (249/249), 77.00 KiB | 0 bytes/s, done.
  Resolving deltas: 100% (142/142), done.
  $ cd Adafruit_Python_DHT
  $ sudo apt-get install build-essential python-dev
  Reading package lists... Done
  Building dependency tree
  Reading state information... Done
  The following NEW packages will be installed:
  build-essential python-dev
  ...
  $ sudo python3 setup.py install
  running install
  running bdist_egg
  running egg_info
  creating Adafruit_DHT.egg-info
  ...
  $


The Plugin
----------

This is the code for the plugin:

.. code-block:: python

  """ Plugin for a DHT11 temperature and humidity sensor attached directly
      to the GPIO pins of a Raspberry Pi

      This plugin uses the Adafruit DHT library, to install this perform
      the following steps:

          git clone https://github.com/adafruit/Adafruit_Python_DHT.git
          cd Adafruit_Python_DHT
          sudo apt-get install build-essential python-dev
          sudo python setup.py install

      To access the GPIO pins foglamp must be able to access /dev/gpiomem,
      the default access for this is owner and group read/write. Either
      FogLAMP must be added to the group or the permissions altered to
      allow FogLAMP access to the device.
      """

  from datetime import datetime, timezone
  import Adafruit_DHT
  import uuid
  import copy

  from foglamp.common import logger
  from foglamp.services.south import exceptions

  __author__ = "Mark Riddoch"
  __copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
  __license__ = "Apache 2.0"
  __version__ = "${VERSION}"

  _DEFAULT_CONFIG = {
      'plugin': {
          'description': 'Python module name of the plugin to load',
          'type':        'string',
          'default':     'dht11pi'
      },
      'pollInterval': {
          'description': 'The interval between poll calls to the device poll routine expressed in milliseconds.',
          'type':        'integer',
          'default':     '1000'
      },
      'gpiopin': {
          'description': 'The GPIO pin into which the DHT11 data pin is connected',
          'type':        'integer',
          'default':     '4'
      }

  }

  _LOGGER = logger.setup(__name__)
  """ Setup the access to the logging system of FogLAMP """

  def plugin_info():
      """ Returns information about the plugin.

      Args:
      Returns:
          dict: plugin information
      Raises:
      """

      return {
          'name':      'DHT11 GPIO',
          'version':   '1.0',
          'mode':      'poll',
          'type':      'south',
          'interface': '1.0',
          'config':    _DEFAULT_CONFIG
      }


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


  def plugin_shutdown(handle):
      """ Shutdowns the plugin doing required cleanup, to be called prior to the device service being shut down.

      Args:
          handle: handle returned by the plugin initialisation call
      Returns:
      Raises:
      """


The configuration
-----------------

Since the plugin is still experimental, it works only in a build environment, the snap version will be available in the next release.

The configuration must be set manually in the FogLAMP metadata. in the repository, the file *cmds.sql* in the *contrib/plugins/south/dht11pi* folder must be executed with *psql* (or another PostgreSQL client) to add the configuration to the FogLAMP metadata.
 
Let's see the SQL commands:

.. code-block:: sql

  --- Create the South service instannce
  INSERT INTO foglamp.scheduled_processes ( name, script )
       VALUES ( 'dht11pi', '["services/south"]');

  --- Add the schedule to start the service at system startup
  INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,schedule_interval, exclusive )
       VALUES ( '543a59ce-a9ca-11e7-abc4-cec278b6b11a', 'device', 'dht11pi', 1, '0:0', true );

  --- Insert the config needed to load the plugin
  INSERT INTO foglamp.configuration ( key, description, value )
       VALUES ( 'dht11pi', 'DHT11 on Raspberry Pi Configuration',
                '{"plugin" : { "type" : "string", "value" : "dht11pi", "default" : "dht11pi", "description" : "Plugin to load" } }' );


Building FogLAMP and Adding the Plugin
--------------------------------------

If you have not built FogLAMP yet, follow the steps described |Getting Started|. After the build, you can optionally install FogLAMP following `these steps`_.

Once the Storage database has been setup, let's update the configurarion to include the new plugin:

.. code-block:: console

  $ psql -d foglamp -f cmds.sql
  INSERT 0 1
  INSERT 0 1
  INSERT 0 1
  $


Now it is time to apply a workaround and include our new plugin. 

- If you intend to start and execute FogLAMP from the build folder: copy the structure of the *contrib* folder into the *python* folder:

.. code-block:: console

  $ cd ~/FogLAMP
  $ cp -R contrib/plugins python/foglamp/.
  $

- If you have installed FogLAMP by executing ``sudo make install``, copy the structure of the *contrib* folder into the installed *python* folder:

.. code-block:: console

  $ cd ~/FogLAMP
  $ sudo cp -R contrib/plugins /usr/local/FogLAMP/python/foglamp/.
  $

.. note:: If you have installed FogLAMP using an alternative *DESTDIR*, remember to add the path to the destination directory to the ``cp`` command.


Using the Plugin
----------------

Now you are ready to use the DHT11 plugin. If stop and restart FogLAMP if it is already running, or start it now.

- Starting FogLAMP from the build folder:

.. code-block:: console

  $ cd ~/FogLAMP
  $ export FOGLAMP_ROOT=$HOME/FogLAMP
  $ scripts/foglamp start
  Starting FogLAMP................
  FogLAMP started.
  $


- Starting FogLAMP from the installed folder:

.. code-block:: console

  $ cd /usr/local/FogLAMP
  $ bin/foglamp start
  Starting FogLAMP................
  FogLAMP started.
  $


Let's see what we have collected so far:

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset | jq
  [
    {
      "count": 158,
      "asset_code": "dht11"
    }
  ]
  $

Finally, let's extract some values:

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset/dht11?limit=5 | jq
  [
    {
      "timestamp": "2017-12-30 14:41:39.672",
      "reading": {
        "temperature": 19,
        "humidity": 62
      }
    },
    {
      "timestamp": "2017-12-30 14:41:35.615",
      "reading": {
        "temperature": 19,
        "humidity": 63
      }
    },
    {
      "timestamp": "2017-12-30 14:41:34.087",
      "reading": {
        "temperature": 19,
        "humidity": 62
      }
    },
    {
      "timestamp": "2017-12-30 14:41:32.557",
      "reading": {
        "temperature": 19,
        "humidity": 63
      }
    },
    {
      "timestamp": "2017-12-30 14:41:31.028",
      "reading": {
        "temperature": 19,
        "humidity": 63
      }
    }
  ]
  $


Clearly we will not see many changes in temperature or humidity, unless we place our thumb on the sensor or we blow warm breathe on it :-)

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset/dht11?limit=5 | jq
  [
    {
      "timestamp": "2017-12-30 14:43:16.787",
      "reading": {
        "temperature": 25,
        "humidity": 95
      }
    },
    {
      "timestamp": "2017-12-30 14:43:15.258",
      "reading": {
        "temperature": 25,
        "humidity": 95
      }
    },
    {
      "timestamp": "2017-12-30 14:43:13.729",
      "reading": {
        "temperature": 24,
        "humidity": 95
      }
    },
    {
      "timestamp": "2017-12-30 14:43:12.201",
      "reading": {
        "temperature": 24,
        "humidity": 95
      }
    },
    {
      "timestamp": "2017-12-30 14:43:05.616",
      "reading": {
        "temperature": 22,
        "humidity": 95
      }
    }
  ]
  $

Needless to say, the North plugin will send the buffered data to the PI system using the PI Connector Relay OMF. Do not forget to set the correct IP address for the PI Connector Relay, as it is described `here`_.

|DHT11 in PI|


