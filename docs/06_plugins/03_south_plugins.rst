.. Writing and Using Plugins describes how to implement a plugin for FogLAMP and how to use it
.. https://docs.google.com/document/d/1IKGXLWbyN6a7vx8UO3uDbq5Df0VvE4oCQIULgZVZbjM

.. |br| raw:: html

   <br />

.. Images

.. Links

.. =============================================


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
                      'asset': 'dht11',
                      'timestamp': time_stamp,
                      'key': str(uuid.uuid4()),
                      'readings': readings
              }
              return wrapper
          else:
              return None

      except Exception as ex:
          raise exceptions.DataRetrievalError(ex)

      return None


Async IO Mode
-------------

In asyncio mode the plugin inserts itself into the event processing loop of the South Service itself. This is a more complex mechanism and is intended for plugins that need to block or listen for incoming data via a network.


Plugin Start
~~~~~~~~~~~~

The *plugin_start* method, as with other plugin calls, is called with the plugin handle data that was returned from the *plugin_init* call. The *plugin_start* call will only be called once for a plugin, it is the responsibility of *plugin_start* to install the plugin code into the python event handling system for asyncIO. Assuming an example whereby the interface to a sensor is via HTTP and the sensor will make HTTP POST calls to our plugin in order to send data into FogLAMP, a *plugin_start* for this scenario would create a web application endpoint for reception of the POST command.

.. code-block:: python

  loop = asyncio.get_event_loop()
  app = web.Application(middlewares=[middleware.error_middleware])
  app.router.add_route('POST', '/', SensorPhoneIngest.render_post)
  handler = app.make_handler()
  coro = loop.create_server(handler, host, port)
  server = asyncio.ensure_future(coro)

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


.. include:: 03_01_DHT11.rst
