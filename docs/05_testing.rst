.. FogLAMP testing describes how to test FogLAMP

.. |br| raw:: html

   <br />

.. Images
.. |postman_ping| image:: images/postman_ping.jpg
.. |win_server_waiting| image:: images/05_win_server_waiting.jpg
.. |pi_loaded| image:: images/05_pi_loaded.jpg

.. Links

.. Links in new tabs

.. |curl| raw:: html

   <a href="https://en.wikipedia.org/wiki/CURL" target="_blank">curl</a>

.. |postman| raw:: html

   <a href="https://www.getpostman.com" target="_blank">Postman</a>

.. |here OSIsoft| raw:: html

   <a href="https://www.osisoft.com/" target="_blank">here</a>

.. |here OMF| raw:: html

   <a href="http://omf-docs.readthedocs.io" target="_blank">here</a>

.. |here PI| raw:: html

   <a href="https://www.osisoft.com/pi-system" target="_blank">here</a>


.. =============================================


***************
Testing FogLAMP
***************

After the installation, you are now ready to test FogLAMP. An end-to-end test involves three types of tests:

- The **South** side, i.e. testing the collection of information from South microservices and associated plugins
- The **North** side, i.e. testing the tasks that send data North to historians, databases, Enterprise and Cloud systems
- The **East/West** side, i.e. testing the interaction of external applications with FogLAMP via REST API.

This chapter describes how to tests FogLAMP in these three directions.


First Checks: FogLAMP Status
============================

Before we start, let's make sure that FogLAMP is up and running and that we have the tasks and services in place to execute the tests. |br| First, run the ``foglamp status`` command to check if FogLAMP has already started. The result of the command can be:

- ``FogLAMP not running.`` - it means that we must start FogLAMP with ``foglamp start``
- ``FogLAMP starting.`` - it means that we have started FogLAMP but the starting phase has not been completed yet. You should wait for a little while (from few seconds to about a minute) to see FogLAMP running.
- ``FogLAMP running.`` - (plus extra rows giving the uptime and other info. It means that FogLAMP is up and running, hence it is ready for use.


When you have a running FogLAMP, check the extra information provided by the ``foglamp status`` command:

.. code-block:: console

  $ foglamp status
  FogLAMP running.
  FogLAMP uptime:  282 seconds.
  === FogLAMP services:
  foglamp.services.core
  foglamp.services.south --port=44180 --address=127.0.0.1 --name=COAP
  === FogLAMP tasks:
  foglamp.tasks.north.sending_process --stream_id 1 --debug_level 1 --port=44180 --address=127.0.0.1 --name=sending process
  foglamp.tasks.north.sending_process --stream_id 2 --debug_level 1 --port=44180 --address=127.0.0.1 --name=statistics to pi
  $
 
Let's analyze the output of the command:

- ``FogLAMP running.`` - The FogLAMP Core microservice is running on this machine and it is responding to the status command as *running* because other basic microservices are also running. 
- ``FogLAMP uptime:  282 seconds.`` - This is a simple uptime in second provided by the Core microservice. It is equivalent to the ``ping`` method called via the REST API. The following lines provide a list of the modules running in this installation of FogLAMP. They are separated by dots and described in this way:
  - The prefix ``foglamp`` is always present and identifies the FogLAMP modules.
  - The following term describes the type of module: *services* for microservices, *tasks* for tasks etc.
  - The following term is the name of the module: *core*, *storage*, *north*, *south*, *app*, *alert*
  - The last term is the name of the plugin executed as part of the module.
  - Extra arguments may be available: they are the arguments passed to the module by the core when it is launched.
- ``=== FogLAMP services:`` - This block contains the list of microservices running in the FogLAMP plaftorm.
  - ``foglamp.services.core`` is the Core microservice itself
  - ``foglamp.services.south --port=44180 --address=127.0.0.1 --name=COAP`` - This South microservice is a listener of data pushed to FogLAMP via a CoAP protocol
- ``=== FogLAMP tasks:`` - This block contains the list of tasks running in the FogLAMP platform.
  - ``foglamp.tasks.north.sending_process ... --name=sending process`` is a North task that prepares and sends data collected by the South modules to the OSIsoft PI System in OMF (OSIsoft Message Format).
  - ``foglamp.tasks.north.sending_process ... --name=statistics to pi`` is a North task that prepares and sends the internal statistics to the OSIsoft PI System in OMF (OSIsoft Message Format).


Hello, Foggy World!
===================

The output of the ``foglamp status`` command gives you an idea of the modules runnning in your machine, but let's try to get more information from FogLAMP.


The FogLAMP REST API
--------------------

First of all, we need to familiarize with the FogLAMP REST API. The API provides a set of methods used to monitor and administer the status of FogLAMP. Users and developers can also use the API to interact with external applications.

This is a short list of the methods available to the administrators.  A more detailed list will be available soon:
- **ping** provides the uptime of the FogLAMP Core microservice
- **statistics** provides a set of statistics of the FogLAMP platform, such as data collected, sent, purged, rejected etc.
- **asset** provides a list of asset that have readings buffered in FogLAMP.
- **categories** provides a list of the configuration of the modules and components in FogLAMP.


Useful Tools
~~~~~~~~~~~~

Systems Administrators and Developers may already have their favorite tools to interact with a REST API, and they can probably use the same tools with FogLAMP. If you are not familiar with any tool, we recommend one of these:

- If you are familiar with the Linux shell and command lines, |curl| is the simplest and most useful tool available. It comes with every Linux distribution (or you can easily add it if it is not available in the default installation.
- If you prefer to use a browser-like interface, we recommend |postman|. Postman is an application available on Linux, MacOS and Windows and allows you to save queries, results, and run a set of queries with a single click.


Hello World!
------------

Let's execute the *ping* method. First, you must identify the IP address where FogLAMP is running. If you have installed FogLAMP on your local machine, you can use *localhost*. Alternatively, check the IP address of the machine where FogLAMP is installed.

.. note:: This version of FogLAMP does not have any security setup by default, therefore you may be able to access the entry point for the REST API by any external aplication, but there may be security setting on your operating environment that prevent access to specific ports from external applications. If you receive an error using the ping method, and the ``foglamp status`` command says that everything is running, it is likely that you are experiencing a security issue.

The default port for the REST API is 8081. Using curl, try this command:

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/ping ; echo
  {"uptime": 2646.8824095726013}
  $
 
The ``echo`` at the end of the line is simply used to add an extra new line to the output. 
|br| |br|
If you are using Postman, select the *GET* method and type ``http://localhost:8081/foglamp/ping`` in the URI line. If you are accessing a remote machine, replace *localhost* with the correct IP address. The output should be something like:

|postman_ping|

This is the first message you may receive from FogLAMP!


Hello from the Southern Hemisphere of the FogLAMP World
=======================================================

Let's now try something more exciting. The primary job of FogLAMP is to collect data from the Edge (we call it *South*), buffer it in our storage engine and then we send the data to Cloud historians and Enterprise Servers (we call them *North*). We also offer information to local or networked applications, something we call *East* or *West*.
|br| |br|
In order to insert data you may need a sensor or a device that generates data. If you want to try FogLAMP but you do not have any sensor at hand, do not worry, we have a tool that can generate data as if it is a sensor.


fogbench: a Brief Intro
-----------------------

FogLAMP comes with a little but pretty handy tool called **fogbench**. The tools is written in Python and it uses the same libraries of other modules of FogLAMP, therefore no extra libraries are needed. With *fogbench* you can do many things, like inserting data stored in files, running benchmarks to understand how FogLAMP performs in a given environment, or test an end-to-end installation.

Depending on your environment, you can call *fogbench* in one of those ways:

- In a development environment, use the script *scripts/extras/fogbench*, inside your project repository (remember to set the *FOGLAMP_ROOT* environment variable with the path to your project repository folder).
- In an environment deployed with ``sudo make install``, use the script *bin/fogbench*.
- In a snap installation, call the ``foglamp.fogbench`` script.

Regardless of the position or environment, the *fogbench* tool, responds to your call like this:

.. code-block:: console

  $ foglamp.fogbench
  >>> Make sure device service is running & CoAP server is listening on specified host and port
  usage: fogbench [-h] [-v] [-k {y,yes,n,no}] -t TEMPLATE [-o OUTPUT]
                  [-I ITERATIONS] [-O OCCURRENCES] [-H HOST] [-P PORT]
                  [-i INTERVAL] [-S {total}]
  fogbench: error: the following arguments are required: -t/--template
  $

...or more specifically, when you call invoke *fogbench* with the *--help* or *-h* argument:

.. code-block:: console

  $ foglamp.fogbench -h
  >>> Make sure device service is running & CoAP server is listening on specified host and port
  usage: fogbench [-h] [-v] [-k {y,yes,n,no}] -t TEMPLATE [-o OUTPUT]
                  [-I ITERATIONS] [-O OCCURRENCES] [-H HOST] [-P PORT]
                  [-i INTERVAL] [-S {total}]

  fogbench -- a Python script used to test FogLAMP (simulate payloads)

  optional arguments:
    -h, --help            show this help message and exit
    -v, --version         show program's version number and exit
    -k {y,yes,n,no}, --keep {y,yes,n,no}
                            Do not delete the running sample (default: no)
    -t TEMPLATE, --template TEMPLATE
                          Set the template file, json extension
    -o OUTPUT, --output OUTPUT
                          Set the statistics output file
    -I ITERATIONS, --iterations ITERATIONS
                          The number of iterations of the test (default: 1)
    -O OCCURRENCES, --occurrences OCCURRENCES
                          The number of occurrences of the template (default: 1)
    -H HOST, --host HOST  CoAP server host address (default: localhost)
    -P PORT, --port PORT  The FogLAMP port. (default: 5683)
    -i INTERVAL, --interval INTERVAL
                          The interval in seconds for each iteration (default:
                          0)
    -S {total}, --statistics {total}
                          The type of statistics to collect (default: total)

  The initial version of fogbench is meant to test the sensor/device interface
  of FogLAMP using CoAP
  $

In order to use *fogbench* you need a template file. The template is a set of JSON elements that are used to create a random set of values that simulate the data generated by one or more sensors. FogLAMP comes with a template file named *fogbench_sensor_coap.template.json*. The template is located here:

- In a development environment, look in *data/extras/fogbench* in the project repository folder.
- In an environment deployed using ``sudo make install``, look in *$FOGLAMP_DATA/extras/fogbench*.
- In a snap installation, look in */snap/foglamp/current/usr/local/foglamp/data/extras/fogbench* (the directory is readonly).

The template file looks like this:


.. code-block:: console

  $ cat /snap/foglamp/current/usr/local/foglamp/data/extras/fogbench/fogbench_sensor_coap.template.json
  [
    { "name"          : "TI sensorTag/luxometer",
      "sensor_values" : [ { "name": "lux", "type": "number", "min": 0, "max": 130000, "precision":3 } ] },
    { "name"          : "TI sensorTag/pressure",
      "sensor_values" : [ { "name": "pressure", "type": "number", "min": 800.0, "max": 1100.0, "precision":1 } ] },
    { "name"          : "TI sensorTag/humidity",
      "sensor_values" : [ { "name": "humidity",    "type": "number", "min": 0.0, "max": 100.0 },
                          { "name": "temperature", "type": "number", "min": 0.0, "max": 50.0  } ] },
    { "name"          : "TI sensorTag/temperature",
      "sensor_values" : [ { "name": "object", "type": "number", "min": 0.0, "max": 50.0 },
                          { "name": "ambient", "type": "number", "min": 0.0, "max": 50.0 } ] },
    { "name"          : "TI sensorTag/accelerometer",
      "sensor_values" : [ { "name": "x", "type": "number", "min": -2.0, "max": 2.0 },
                          { "name": "y", "type": "number", "min": -2.0, "max": 2.0 },
                          { "name": "z", "type": "number", "min": -2.0, "max": 2.0 } ] },
    { "name"          : "TI sensorTag/gyroscope",
      "sensor_values" : [ { "name": "x", "type": "number", "min": -255.0, "max": 255.0 },
                          { "name": "y", "type": "number", "min": -255.0, "max": 255.0 },
                          { "name": "z", "type": "number", "min": -255.0, "max": 255.0 } ] },
    { "name"          : "TI sensorTag/magnetometer",
      "sensor_values" : [ { "name": "x", "type": "number", "min": -255.0, "max": 255.0 },
                          { "name": "y", "type": "number", "min": -255.0, "max": 255.0 },
                          { "name": "z", "type": "number", "min": -255.0, "max": 255.0 } ] },
    { "name"          : "mouse",
      "sensor_values" : [ { "name": "button", "type": "enum", "list": [ "up", "down" ] } ] },
    { "name"          : "switch",
      "sensor_values" : [ { "name": "button", "type": "enum", "list": [ "up", "down" ] } ] },
    { "name"          : "wall clock",
      "sensor_values" : [ { "name": "tick", "type": "enum", "list": [ "tock" ] } ] }
  ] 
  $

In the array, each element simulates a message from a sensor, with a name, a set of data points that have their name, value type and range.


Data Coming from South
----------------------

Now you should have all the information necessary to test the CoAP South microservice. From the command line, type:

- ``$FOGLAMP_ROOT/scripts/extras/fogbench -t $FOGLAMP_ROOT/data/extras/fogbench/fogbench_sensor_coap.template.json``, if you are in a development environment, with the *FOGLAMP_ROOT* environment variable set with the path to your project repository folder
- ``$FOGLAMP_ROOT/bin/fogbench -t $FOGLAMP_DATA/extras/fogbench/fogbench_sensor_coap.template.json``, if you are in a deployed environment, with *FOGLAMP_ROOT* and *FOGLAMP_DATA* set correctly.
  - If you have installed FogLAMP in the default location (i.e. */usr/local/foglamp*), type ``cd /usr/local/foglamp;bin/fogbench -t data/extras/fogbench/fogbench_sensor_coap.template.json``.
- ``foglamp.fogbench -t /snap/foglamp/current/usr/local/foglamp/data/extras/fogbench/fogbench_sensor_coap.template.json``, if you have installed a snap version of FogLAMP.

The output of your command should be:

.. code-block:: console

  $ scripts/extras/fogbench -t data/extras/fogbench/fogbench_sensor_coap.template.json
  >>> Make sure device service is running & CoAP server is listening on specified host and port
  Total Statistics:

  Start Time: 2017-12-17 07:17:50.615433
  Ene Time:   2017-12-17 07:17:50.650620

  Total Messages Transferred: 10
  Total Bytes Transferred:    2880

  Total Iterations: 1
  Total Messages per Iteration: 10.0
  Total Bytes per Iteration:    2880.0

  Min messages/second: 284.19586779208225
  Max messages/second: 284.19586779208225
  Avg messages/second: 284.19586779208225

  Min Bytes/second: 81848.4099241197
  Max Bytes/second: 81848.4099241197
  Avg Bytes/second: 81848.4099241197
  $

Congratulations! You have just inserted data into FogLAMP from the CoAP South microservice. More specifically, the output informs you that the data inserted has been composed by 10 different messages for a total of 2,880 Bytes, for an average of 284 messages per second and 81,848 Bytes per second.

If you want to stress FogLAMP a bit, you may insert the same data sample several times, by using the *-I* or *--iterations* argument:

.. code-block:: console

  $ scripts/extras/fogbench -t data/extras/fogbench/fogbench_sensor_coap.template.json -I 100
  >>> Make sure device service is running & CoAP server is listening on specified host and port
  Total Statistics:

  Start Time: 2017-12-17 07:33:40.568130
  End Time:   2017-12-17 07:33:43.205626

  Total Messages Transferred: 1000
  Total Bytes Transferred:    288000

  Total Iterations: 100
  Total Messages per Iteration: 10.0
  Total Bytes per Iteration:    2880.0

  Min messages/second: 98.3032852957946
  Max messages/second: 625.860558267618
  Avg messages/second: 455.15247432732866

  Min Bytes/second: 28311.346165188843
  Max Bytes/second: 180247.840781074
  Avg Bytes/second: 131083.9126062706
  $

Here we have inserted the same set of data 100 times, therefore the total number of Bytes inserted is 288,000. The performance and insertion rates varies with each iteration and *fogbench* presents the minimum, maximum and average values.


Checking What's Inside FogLAMP
==============================

We can check if FogLAMP has now stored what we have inserted from the South microservice by using the *asset* API. From curl or Postman, use this URL:

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset ; echo
  [{"asset_code": "switch", "count": 11}, {"asset_code": "TI sensorTag/temperature", "count": 11}, {"asset_code": "TI sensorTag/humidity", "count": 11}, {"asset_code": "TI sensorTag/luxometer", "count": 11}, {"asset_code": "TI sensorTag/accelerometer", "count": 11}, {"asset_code": "wall clock", "count": 11}, {"asset_code": "TI sensorTag/magnetometer", "count": 11}, {"asset_code": "mouse", "count": 11}, {"asset_code": "TI sensorTag/pressure", "count": 11}, {"asset_code": "TI sensorTag/gyroscope", "count": 11}]
  $

The output of the asset entry point provides a list of assets buffered in FogLAMP and the count of elements stored. The output is a JSON array with two elements:

- **asset_code** : the name of the sensor or device that provides the data
- **count** : the number of occurrences of the asset in the buffer


Feeding East/West Applications
------------------------------

Let's suppose that we are interested in the data collected for one of the assets listed in the previous query, for example *TI sensorTag/temperature*. The *asset* entry point can be used to retrieve the data points for individual assets by simply adding the code of the asset to the URI:

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset/TI%20sensorTag%2Ftemperature ; echo
  [{"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41}}, {"timestamp": "2017-12-18 10:38:12.580", "reading": {"ambient": 33, "object": 7}}] 
  $

Let's see the JSON output on a more readable format:

.. code-block:: json

  [ { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:29.652", "reading": {"ambient": 13, "object": 41} },
    { "timestamp": "2017-12-18 10:38:12.580", "reading": {"ambient": 33, "object": 7} } ] 

The JSON structure depends on the sensor and the plugin used to capture the data. In this case, the values shown are:

- **timestamp** : the timestamp generated by the sensors. In this case, since we have inserted 10 times the same value and one time a new value using *fogbench*, the result is 10 timestamps with the same value and one timestamp with a different value.
- **reading** : a JSON structure that is the set of data points provided by the sensor. In this case:
  - **ambient** : the ambient temperature in Celsius
  - **object** : the object temperature in Celsius. Again, the values are repeated 10 times, due to the iteration executed by *fogbench*, plus an isolated element, so there are 11 readings in total. Also, it is very unlikely that in a real sensor the ambient and the object temperature differ so much, but here we are using a random number generator.


You can dig even more in the data and extract only a subset of the reading. Fog example, you can select the ambient temperature and limit to the last 5 readings:


.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset/TI%20sensorTag%2Ftemperature/ambient?limit=5 ; echo
  [ { "ambient": 13, "timestamp": "2017-12-18 10:38:29.652" },
    { "ambient": 13, "timestamp": "2017-12-18 10:38:29.652" }
    { "ambient": 13, "timestamp": "2017-12-18 10:38:29.652" },
    { "ambient": 13, "timestamp": "2017-12-18 10:38:29.652" },
    { "ambient": 13, "timestamp": "2017-12-18 10:38:29.652" } ]
  $


We have beautified the JSON output for you, so it is more readable.

.. note:: When you select a specific element in the reading, the timestamp and the element are presented in the opposite order compared to the previous example. This is a known issue that will be fixed in the next version.


Sending Greetings to the Northern Hemisphere
============================================

The next and last step is to send data to North, which means that we can take all of some of the data we buffer in FogLAMP and we can send it to a historian or a database using a North task or microservice.


The OMF Translator
------------------

FogLAMP comes with a North plugin called *OMF Translator*. OMF is the OSIsoft Message Format, which is the message format accepted by the PI Connector Relay OMF. The PI Connector Relay OMF is provided by OSIsoft and it is used to feed the OSIsoft PI System.

- Information regarding OSIsoft are available |here OSIsoft|
- Information regarding OMF are available |here OMF|
- Information regarding the OSIsoft PI System are available |here PI|

*OMF Translator* is schedules as a North task that is executed every 30 seconds (the time may vary, we set it to 30 seconds to facilitate the testing.


Preparing the PI System
-----------------------

In order to test the North task and plugin, first you need to setup the PI system. Here we assume you are already familiar with PI and you have a Windows server with PI installed, up and running. The minimum installation must include the PI System and the PI Connector Relay OMF. Once you have checked that everything is installed and works correctly, you should collect the IP addess of the Windows system.


Setting the OMF Translator Plugin
---------------------------------

FogLAMP uses the same *OMF Translator* plugin to send two streams of data: the data coming from the South modules and buffered in FogLAMP and the statistics generated and collected from FogLAMP. In the current installation, these two streams refer to the categories and streams *SEND_PR_1* (South data) and *SEND_PR_2* (FogLAMP Statistics).

.. note:: In this version, only the South data can be sent to the PI System.

If you are curious to see which categories are available in FogLAMP, simply type:

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/categories ; echo
  { "categories": [ { "description": "Log Partitioning",                     "key": "LOGPART" },
                    { "description": "Sensors and Device Interface",         "key": "SENSORS" },
                    { "description": "HTTP North Plugin Configuration",      "key": "SEND_PR_3" },
                    { "description": "Streaming",                            "key": "STREAMING" },
                    { "description": "System Purge",                         "key": "SYPURGE" },
                    { "description": "POLL Plugin Configuration",            "key": "POLL" },
                    { "description": "HTTP South Plugin Configuration",      "key": "HTTP_SOUTH" },
                    { "description": "SensorTagCC2650 Plugin Configuration", "key": "CC2650POLL" },
                    { "description": "Scheduler configuration",              "key": "SCHEDULER" },
                    { "description": "Service Monitor configuration",        "key": "SMNTR" },
                    { "description": "COAP Device",                          "key": "COAP" },
                    { "description": "Device server configuration",          "key": "DEVICE" },
                    { "description": "Configuration of OMF types",           "key": "OMF_TYPES" },
                    { "description": "Configuration of the Sending Process", "key": "SEND_PR_1" },
                    { "description": "Purge the readings table",             "key": "PURGE_READ" },
                    { "description": "Configuration of the Sending Process", "key": "SEND_PR_2" } 
                  ]
  }
  $

The configuration for the OMF Translator used to stream the South data is:

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/category/SEND_PR_1 ; echo
  { "plugin":            { "description": "Python module name of the plugin to load",
                           "type": "string",
                           "default": "omf",
                           "value": "omf" },
    "OMFMaxRetry":       { "description": "Max number of retries for the communication with the OMF PI Connector Relay",
                           "type": "integer",
                           "default": "5",
                           "value": "5" },
    "stream_id":         { "description": "Stream ID",
                           "type": "integer",
                           "default": "1",
                           "value": "1" },
    "blockSize":         { "description": "The size of a block of readings to send in each transmission.",
                           "type": "integer",
                           "default": "5000",
                           "value": "5000" },
    "sleepInterval":     { "description": "A period of time, expressed in seconds, to wait between attempts to send readings when there are no readings to be sent.",
                           "type": "integer",
                           "default": "5",
                           "value": "5" },
    "translator":        { "description": "The name of the translator to use to translate the readings into the output format and send them",
                           "type": "string",
                           "default": "omf",
                           "value": "omf" },
    "URL":               { "description": "The URL of the PI Connector to send data to",
                           "type": "string",
                           "default": "http://WIN-4M7ODKB0RH2:8118/ingress/messages",
                           "value": "http://WIN-4M7ODKB0RH2:8118/ingress/messages" },
    "OMFHttpTimeout":    { "description": "Timeout in seconds for the HTTP operations with the OMF PI Connector Relay",
                           "type": "integer",
                           "default": "30",
                           "value": "30" },
    "producerToken":     { "description": "The producer token that represents this FogLAMP stream",
                           "type": "string",
                           "default": "omf_translator_0001",
                           "value": "omf_translator_0001" },
    "source":            { "description": "Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.",
                           "type": "string",
                           "default": "readings",
                           "value": "readings" },
    "duration":          { "description": "How long the sending process should run (in seconds) before stopping.",
                           "type": "integer",
                           "default": "60",
                           "value": "60" },
    "OMFRetrySleepTime": { "description": "Seconds between each retry for the communication with the OMF PI Connector Relay",
                           "type": "integer",
                           "default": "1",
                           "value": "1" },
    "StaticData":        { "description": "Static data to include in each sensor reading sent to OMF.",
                           "type": "JSON",
                           "default": "{\"Location\": \"Palo Alto\", \"Company\": \"Dianomic\"}",
                           "value": "{\"Location\": \"Palo Alto\", \"Company\": \"Dianomic\"}" },
    "enable":            { "description": "A switch that can be used to enable or disable execution of the sending process.",
                           "type": "boolean", "default": "True",
                           "value": "True" }
  }
  $

What we need to do now is to change the IP address in the URL of *SEND_PR_1* with the IP address of the Windows Server running the PI Connector Relay. Supposing the Windows IP address is *192.168.56.101*, we can use curl for this:

.. code-block:: console

  $ curl -H 'Content-Type: application/json' -X PUT -d '{ "value": "http://192.168.56.101:8118/ingress/messages" }' http://localhost:8081/foglamp/category/SEND_PR_1/URL;echo
  {"value": "http://192.168.56.101:8118/ingress/messages", "default": "http://WIN-4M7ODKB0RH2:8118/ingress/messages", "description": "The URL of the PI Connector to send data to", "type": "string"}
  $

By using the PUT method, FogLAMP replies with the new value of the entry. You can note that the *value* element is the only one that can be changed in *URL* (the other elements are factory settings).

Now we are ready to send data North, to the PI System.


Sending Data to the PI System
-----------------------------

The last bit to accomplish is to start the PI Connector Relay OMF on the Windows Server. The output may look like this screenshot, where you can see the Connector Relay debug window on the left and teh PI Data Explorer on the right.

|win_server_waiting|

Wait a few seconds ...et voilà! Readings and statistics are in the PI System:

|pi_loaded|


Congratulations! You have experienced an end-to-end test of FogLAMP, from South with sensor data through FogLAMP and East/West applications and finally to North towards Historians.


