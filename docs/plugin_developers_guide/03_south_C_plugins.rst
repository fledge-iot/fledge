.. Writing and Using Plugins describes how to implement a plugin for Fledge and how to use it
.. https://docs.google.com/document/d/1IKGXLWbyN6a7vx8UO3uDbq5Df0VvE4oCQIULgZVZbjM

.. |br| raw:: html

   <br />

.. Images

.. Links
.. |C++ Support Classes| raw:: html

   <a href="035_CPP.html">C++ Support Classes</a>

.. =============================================


South Plugins in C
==================

South plugins written in C/C++ are no different in use to those written in Python, it is merely a case that they are implemented in a different language. The same options of polled or asynchronous methods still exist and the enduser of Fledge is not aware in which language the plugin has been written.


Polled Mode
-----------

Polled mode is the simplest form of South plugin that can be written, a poll routine is called at an interval defined in the plugin advanced configuration. The South service determines the type of the plugin by examining the mode property in the information the plugin returns from the *plugin_info* call.


Plugin Poll
~~~~~~~~~~~

The plugin *poll* method is called periodically to collect the readings from a poll mode sensor. As with all other calls the argument passed to the method is the handle returned by the *plugin_init* call, the return of the method should be a *Reading* instance that contains the data read.

The *Reading* class consists of

+---------------+---------------------------------------------------------+
| Property      | Description                                             |
+===============+=========================================================+
| assetName     | The asset key of the sensor device that is being read   |
+---------------+---------------------------------------------------------+
| userTimestamp | A timestamp for the reading data                        |
+---------------+---------------------------------------------------------+
| datapoints    | The reading data itself as a set if datapoint instances |
+---------------+---------------------------------------------------------+

More detail regarding the *Reading* class can be found in the section |C++ Support classes|.

It is important that the *poll* method does not block as this will prevent the proper operation of the South microservice.  Using the example of our simple DHT11 device attached to a GPIO pin, the *poll* routine could be:

.. code-block:: C

  /**
   * Poll for a plugin reading
   */
  Reading plugin_poll(PLUGIN_HANDLE handle)
  {
          DHT11 *dht11 = static_cast<DHT11 *>(handle);
          return dht11->takeReading();
  }

Where our *DHT11* class has a method *takeReading* as follows

.. code-block:: C

  /**
   * Take reading from sensor
   *
   * @param firstReading   This flag indicates whether this is the first reading to be taken from sensor,
   *                       if so get it reliably even if takes multiple retries. Subsequently (firstReading=false),
   *                       if reading from sensor fails, last good reading is returned.
   */
  Reading DHT11::takeReading(bool firstReading)
  {
          static uint8_t sensorData[4] = {0,0,0,0};

          bool valid = false;
          unsigned int count=0;
          do {
                  valid = readSensorData(sensorData);
                  count++;
          } while(!valid && firstReading && count < MAX_SENSOR_READ_RETRIES);

          if (firstReading && count >= MAX_SENSOR_READ_RETRIES)
                  Logger::getLogger()->error("Unable to get initial valid reading from DHT11 sensor connected to pin %d even after %d tries", m_pin, MAX_SENSOR_READ_RETRIES);

          vector<Datapoint *> vec;

          ostringstream tmp;
          tmp << ((unsigned int)sensorData[0]) << "." << ((unsigned int)sensorData[1]);
          DatapointValue dpv1(stod(tmp.str()));
          vec.push_back(new Datapoint("Humidity", dpv1));

          ostringstream tmp2;
          tmp2 << ((unsigned int)sensorData[2]) << "." <<  ((unsigned int)sensorData[3]);
          DatapointValue dpv2(stod(tmp2.str()));
          vec.push_back(new Datapoint ("Temperature", dpv2));

          return Reading(m_assetName, vec);
  }

We are creating two *DatapointValues* for the Humidity and Temperature values returned by reading the DHT11 sensor.

Plugin Poll Returning Multiple Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible in a C/C++ plugin to have a plugin that returns multiple readings in a single call to a poll routine. This is done by setting the interface version of 2.0.0 rather than 1.0.0. In this interface version the *plugin_poll* call returns a vector of *Reading* rather than a single *Reading*.

.. code-block:: C

  /**
   * Poll for a plugin reading
   */
  std::vector<Reading *> *plugin_poll(PLUGIN_HANDLE handle)
  {
          if (!handle)
                  throw runtime_error("Bad plugin handle");

          Modbus *modbus = static_cast<Modbus *>(handle);
          return modbus->takeReading();
  }

Async IO Mode
-------------

In asyncio mode the plugin runs either a separate thread or uses some incoming event from a device or callback mechanism to trigger sending data to Fledge. The asynchronous mode uses two additional entry points to the plugin, one to register a callback on which the plugin sends data, *plugin_register_ingest*  and another to start the asynchronous behavior *plugin_start*.

Plugin Register Ingest
~~~~~~~~~~~~~~~~~~~~~~

The *plugin_register_ingest* call is used to allow the south service to pass a callback function to the plugin that the plugin uses to send data to the service every time the plugin has some new data.

.. code-block:: C

  /**
   * Register ingest callback
   */
  void plugin_register_ingest(PLUGIN_HANDLE handle, INGEST_CB cb, void *data)
  {
          if (!handle)
                  throw new exception();

          MyPluginClass *plugin = static_cast<MyPluginClass *>(handle);
          plugin->registerIngest(data, cb);
  }

The plugin should store the callback function pointer and the data associated with the callback such that it can use that information to pass a reading to the south service. The following code snippets show how a plugin class might store the callback and data and then use it to send readings into Fledge at a later stage.

.. code-block:: C

  /**
   * Record the ingest callback function and data in member variables
   *
   * @param data  The Ingest function data
   * @param cb    The callback function to call
   */
  void MyPluginClass::registerIngest(void *data, INGEST_CB cb)
  {
          m_ingest = cb;
          m_data = data;
  }

  /**
   * Called when a data is available to send to the south service
   *
   * @param points        The points in the reading we must create
   */
  void MyPluginClass::ingest(Reading& reading)
  {

          (*m_ingest)(m_data, reading);
  }


Plugin Start
~~~~~~~~~~~~

The *plugin_start* method, as with other plugin calls, is called with the plugin handle data that was returned from the *plugin_init* call. The *plugin_start* call will only be called once for a plugin, it is the responsibility of *plugin_start* to take whatever action is required in the plugin in order to start the asynchronous actions of the plugin. This might be to start a thread, register an endpoint for a remote connection or call an entry point in a third party library to start asynchronous processing.

.. code-block:: C

  /**     
   * Start the Async handling for the plugin
   */
  void plugin_start(PLUGIN_HANDLE handle)
  {
          if (!handle)
                  return;

          MyPluginClass *plugin = static_cast<MyPluginClass *>(handle);
          plugin->start();
  }

  /**
   * Start the asynchronous processing thread
   */
  void MyPluginClass::start()
  {
          m_running = true;
          m_thread = new thread(threadWrapper, this);
  }

.. include:: 03_02_Control.rst

.. include:: 03_02_DHT11_C.rst
