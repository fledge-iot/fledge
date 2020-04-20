.. Fledge testing describes how to test Fledge

.. |br| raw:: html

   <br />

.. Images

.. |postman_ping| image:: https://s3.amazonaws.com/fledge/readthedocs/images/05_postman_ping.jpg
   :target: https://s3.amazonaws.com/fledge/readthedocs/images/05_postman_ping.jpg

.. |win_server_waiting| image:: https://s3.amazonaws.com/fledge/readthedocs/images/05_win_server_waiting.jpg
   :target: https://s3.amazonaws.com/fledge/readthedocs/images/05_win_server_waiting.jpg

.. |pi_loaded| image:: https://s3.amazonaws.com/fledge/readthedocs/images/05_pi_loaded.jpg
   :target: https://s3.amazonaws.com/fledge/readthedocs/images/05_pi_loaded.jpg

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

.. |jq| raw:: html

   <a href="https://stedolan.github.io/jq" target="_blank">jq</a>

.. |get start| raw:: html

   <a href="building_fledge.html" target="_blank">Building Fledge</a>


.. =============================================


***************
Testing Fledge
***************

After the installation, you are now ready to test Fledge. An end-to-end test involves three types of tests:

- The **South** side, i.e. testing the collection of information from South microservices and associated plugins
- The **North** side, i.e. testing the tasks that send data North to historians, databases, Enterprise and Cloud systems
- The **East/West** side, i.e. testing the interaction of external applications with Fledge via REST API.

This chapter describes how to tests Fledge in these three directions.


First Checks: Fledge Status
============================

Before we start, let's make sure that Fledge is up and running and that we have the tasks and services in place to execute the tests. |br| First, run the ``fledge status`` command to check if Fledge has already started. The result of the command can be:

- ``Fledge not running.`` - it means that we must start Fledge with ``fledge start``
- ``Fledge starting.`` - it means that we have started Fledge but the starting phase has not been completed yet. You should wait for a little while (from few seconds to about a minute) to see Fledge running.
- ``Fledge running.`` - (plus extra rows giving the uptime and other info. It means that Fledge is up and running, hence it is ready for use.


When you have a running Fledge, check the extra information provided by the ``fledge status`` command:

.. code-block:: console

  $ fledge status
  Fledge running.
  Fledge uptime:  282 seconds.
  Fledge Records: 10 read, 0 sent, 0 purged.
  Fledge does not require authentication.
  === Fledge services:
  fledge.services.core
  === Fledge tasks:
  fledge.tasks.north.sending_process --stream_id 1 --debug_level 1 --port=44180 --address=127.0.0.1 --name=sending process
  fledge.tasks.north.sending_process --stream_id 2 --debug_level 1 --port=44180 --address=127.0.0.1 --name=statistics to pi
  $

Let's analyze the output of the command:

- ``Fledge running.`` - The Fledge Core microservice is running on this machine and it is responding to the status command as *running* because other basic microservices are also running.
- ``Fledge uptime:  282 seconds.`` - This is a simple uptime in second provided by the Core microservice. It is equivalent to the ``ping`` method called via the REST API.
- ``Fledge records:`` - This is a summary of the number of records received from sensors and devices (South), sent to other services (North) and purged from the buffer.
- ``Fledge authentication`` - This row describes if a user or an application must authenticate to ogLAMP in order to operate with the REST API.

The following lines provide a list of the modules running in this installation of Fledge. They are separated by dots and described in this way:

  - The prefix ``fledge`` is always present and identifies the Fledge modules.
  - The following term describes the type of module: *services* for microservices, *tasks* for tasks etc.
  - The following term is the name of the module: *core*, *storage*, *north*, *south*, *app*, *alert*
  - The last term is the name of the plugin executed as part of the module.
  - Extra arguments may be available: they are the arguments passed to the module by the core when it is launched.

- ``=== Fledge services:`` - This block contains the list of microservices running in the Fledge platform.

  - ``fledge.services.core`` is the Core microservice itself
  - ``fledge.services.south --port=44180 --address=127.0.0.1 --name=COAP`` - This South microservice is a listener of data pushed to Fledge via a CoAP protocol

- ``=== Fledge tasks:`` - This block contains the list of tasks running in the Fledge platform.

  - ``fledge.tasks.north.sending_process ... --name=sending process`` is a North task that prepares and sends data collected by the South modules to the OSIsoft PI System in OMF (OSIsoft Message Format).
  - ``fledge.tasks.north.sending_process ... --name=statistics to pi`` is a North task that prepares and sends the internal statistics to the OSIsoft PI System in OMF (OSIsoft Message Format).


Hello, Foggy World!
===================

The output of the ``fledge status`` command gives you an idea of the modules running in your machine, but let's try to get more information from Fledge.


The Fledge REST API
--------------------

First of all, we need to familiarize with the Fledge REST API. The API provides a set of methods used to monitor and administer the status of Fledge. Users and developers can also use the API to interact with external applications.

This is a short list of the methods available to the administrators.  A more detailed list will be available soon:
- **ping** provides the uptime of the Fledge Core microservice
- **statistics** provides a set of statistics of the Fledge platform, such as data collected, sent, purged, rejected etc.
- **asset** provides a list of asset that have readings buffered in Fledge.
- **category** provides a list of the configuration of the modules and components in Fledge.


Useful Tools
~~~~~~~~~~~~

Systems Administrators and Developers may already have their favorite tools to interact with a REST API, and they can probably use the same tools with Fledge. If you are not familiar with any tool, we recommend one of these:

- If you are familiar with the Linux shell and command lines, |curl| is the simplest and most useful tool available. It comes with every Linux distribution (or you can easily add it if it is not available in the default installation.
- If you prefer to use a browser-like interface, we recommend |postman|. Postman is an application available on Linux, MacOS and Windows and allows you to save queries, results, and run a set of queries with a single click.


Hello World!
------------

Let's execute the *ping* method. First, you must identify the IP address where Fledge is running. If you have installed Fledge on your local machine, you can use *localhost*. Alternatively, check the IP address of the machine where Fledge is installed.

.. note:: This version of Fledge does not have any security setup by default, therefore you may be able to access the entry point for the REST API by any external application, but there may be security setting on your operating environment that prevent access to specific ports from external applications. If you receive an error using the ping method, and the ``fledge status`` command says that everything is running, it is likely that you are experiencing a security issue.

The default port for the REST API is 8081. Using curl, try this command:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/ping ; echo
  {"dataPurged": 0, "dataRead": 10, "uptime": 2646.8824095726013, "dataSent": 0, "authenticationOptional": true}
  $

The ``echo`` at the end of the line is simply used to add an extra new line to the output.
|br| |br|
If you are using Postman, select the *GET* method and type ``http://localhost:8081/fledge/ping`` in the URI address input. If you are accessing a remote machine, replace *localhost* with the correct IP address. The output should be something like:

|postman_ping|

This is the first message you may receive from Fledge!


Hello from the Southern Hemisphere of the Fledge World
=======================================================

Let's now try something more exciting. The primary job of Fledge is to collect data from the Edge (we call it *South*), buffer it in our storage engine and then we send the data to Cloud historians and Enterprise Servers (we call them *North*). We also offer information to local or networked applications, something we call *East* or *West*.
|br| |br|
In order to insert data you may need a sensor or a device that generates data. If you want to try Fledge but you do not have any sensor at hand, do not worry, we have a tool that can generate data as if it is a sensor.


fogbench: a Brief Intro
-----------------------

Fledge comes with a little but pretty handy tool called **fogbench**. The tools is written in Python and it uses the same libraries of other modules of Fledge, therefore no extra libraries are needed. With *fogbench* you can do many things, like inserting data stored in files, running benchmarks to understand how Fledge performs in a given environment, or test an end-to-end installation.

Note: This following instructions assume you have downloaded and installed the CoAP south plugin from https://github.com/fledge-iot/fledge-south-coap.


.. code-block:: console

  $ git clone https://github.com/fledge-iot/fledge-south-coap
  $ cd fledge-south-coap
  $ sudo cp -r python /usr/local/fledge/python/fledge/plugins/south/
  $ sudo pip3 install -r /usr/local/fledge/python/requirements-coap.txt
  $ chown -R root:root /usr/local/fledge/python/fledge/plugins/south/coap
  $ curl -sX POST http://localhost:8081/fledge/service -d '{"name": "CoAP", "type": "south", "plugin": "coap", "enabled": true}'


Depending on your environment, you can call *fogbench* in one of those ways:

- In a development environment, use the script *scripts/extras/fogbench*, inside your project repository (remember to set the *FLEDGE_ROOT* environment variable with the path to your project repository folder).
- In an environment deployed with ``sudo make install``, use the script *bin/fogbench*.
- In a snap installation, call the ``fledge.fogbench`` script.

Regardless of the position or environment, the *fogbench* tool, responds to your call like this:

.. code-block:: console

  $ fledge.fogbench
  >>> Make sure south CoAP plugin service is running & listening on specified host and port
  usage: fogbench [-h] [-v] [-k {y,yes,n,no}] -t TEMPLATE [-o OUTPUT]
                  [-I ITERATIONS] [-O OCCURRENCES] [-H HOST] [-P PORT]
                  [-i INTERVAL] [-S {total}]
  fogbench: error: the following arguments are required: -t/--template
  $

...or more specifically, when you call invoke *fogbench* with the *--help* or *-h* argument:

.. code-block:: console

  $ fledge.fogbench -h
  >>> Make sure south CoAP plugin service is running & listening on specified host and port
  usage: fogbench [-h] [-v] [-k {y,yes,n,no}] -t TEMPLATE [-o OUTPUT]
                  [-I ITERATIONS] [-O OCCURRENCES] [-H HOST] [-P PORT]
                  [-i INTERVAL] [-S {total}]

  fogbench -- a Python script used to test Fledge (simulate payloads)

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
    -P PORT, --port PORT  The Fledge port. (default: 5683)
    -i INTERVAL, --interval INTERVAL
                          The interval in seconds for each iteration (default:
                          0)
    -S {total}, --statistics {total}
                          The type of statistics to collect (default: total)

  The initial version of fogbench is meant to test the sensor/device interface
  of Fledge using CoAP
  $

In order to use *fogbench* you need a template file. The template is a set of JSON elements that are used to create a random set of values that simulate the data generated by one or more sensors. Fledge comes with a template file named *fogbench_sensor_coap.template.json*. The template is located here:

- In a development environment, look in *data/extras/fogbench* in the project repository folder.
- In an environment deployed using ``sudo make install``, look in *$FLEDGE_DATA/extras/fogbench*.
- In a snap installation, look in */snap/fledge/current/usr/local/fledge/data/extras/fogbench* (the directory is readonly).

The template file looks like this:


.. code-block:: console

  $ cat /snap/fledge/current/usr/local/fledge/data/extras/fogbench/fogbench_sensor_coap.template.json
  [
    { "name"          : "fogbench/luxometer",
      "sensor_values" : [ { "name": "lux", "type": "number", "min": 0, "max": 130000, "precision":3 } ] },
    { "name"          : "fogbench/pressure",
      "sensor_values" : [ { "name": "pressure", "type": "number", "min": 800.0, "max": 1100.0, "precision":1 } ] },
    { "name"          : "fogbench/humidity",
      "sensor_values" : [ { "name": "humidity",    "type": "number", "min": 0.0, "max": 100.0 },
                          { "name": "temperature", "type": "number", "min": 0.0, "max": 50.0  } ] },
    { "name"          : "fogbench/temperature",
      "sensor_values" : [ { "name": "object", "type": "number", "min": 0.0, "max": 50.0 },
                          { "name": "ambient", "type": "number", "min": 0.0, "max": 50.0 } ] },
    { "name"          : "fogbench/accelerometer",
      "sensor_values" : [ { "name": "x", "type": "number", "min": -2.0, "max": 2.0 },
                          { "name": "y", "type": "number", "min": -2.0, "max": 2.0 },
                          { "name": "z", "type": "number", "min": -2.0, "max": 2.0 } ] },
    { "name"          : "fogbench/gyroscope",
      "sensor_values" : [ { "name": "x", "type": "number", "min": -255.0, "max": 255.0 },
                          { "name": "y", "type": "number", "min": -255.0, "max": 255.0 },
                          { "name": "z", "type": "number", "min": -255.0, "max": 255.0 } ] },
    { "name"          : "fogbench/magnetometer",
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

- ``$FLEDGE_ROOT/scripts/extras/fogbench`` ``-t $FLEDGE_ROOT/data/extras/fogbench/fogbench_sensor_coap.template.json``, if you are in a development environment, with the *FLEDGE_ROOT* environment variable set with the path to your project repository folder
- ``$FLEDGE_ROOT/bin/fogbench -t $FLEDGE_DATA/extras/fogbench/fogbench_sensor_coap.template.json``, if you are in a deployed environment, with *FLEDGE_ROOT* and *FLEDGE_DATA* set correctly.
  - If you have installed Fledge in the default location (i.e. */usr/local/fledge*), type ``cd /usr/local/fledge;bin/fogbench -t data/extras/fogbench/fogbench_sensor_coap.template.json``.
- ``fledge.fogbench`` ``-t /snap/fledge/current/usr/local/fledge/data/extras/fogbench/fogbench_sensor_coap.template.json``, if you have installed a snap version of Fledge.

The output of your command should be:

.. code-block:: console

  $ scripts/extras/fogbench -t data/extras/fogbench/fogbench_sensor_coap.template.json
  >>> Make sure south CoAP plugin service is running & listening on specified host and port
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

Congratulations! You have just inserted data into Fledge from the CoAP South microservice. More specifically, the output informs you that the data inserted has been composed by 10 different messages for a total of 2,880 Bytes, for an average of 284 messages per second and 81,848 Bytes per second.

If you want to stress Fledge a bit, you may insert the same data sample several times, by using the *-I* or *--iterations* argument:

.. code-block:: console

  $ scripts/extras/fogbench -t data/extras/fogbench/fogbench_sensor_coap.template.json -I 100
  >>> Make sure south CoAP plugin service is running & listening on specified host and port
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


Checking What's Inside Fledge
==============================

We can check if Fledge has now stored what we have inserted from the South microservice by using the *asset* API. From curl or Postman, use this URL:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/asset ; echo
  [{"asset_code": "switch", "count": 11}, {"asset_code": "fogbench/temperature", "count": 11}, {"asset_code": "fogbench/humidity", "count": 11}, {"asset_code": "fogbench/luxometer", "count": 11}, {"asset_code": "fogbench/accelerometer", "count": 11}, {"asset_code": "wall clock", "count": 11}, {"asset_code": "fogbench/magnetometer", "count": 11}, {"asset_code": "mouse", "count": 11}, {"asset_code": "fogbench/pressure", "count": 11}, {"asset_code": "fogbench/gyroscope", "count": 11}]
  $

The output of the asset entry point provides a list of assets buffered in Fledge and the count of elements stored. The output is a JSON array with two elements:

- **asset_code** : the name of the sensor or device that provides the data
- **count** : the number of occurrences of the asset in the buffer


Feeding East/West Applications
------------------------------

Let's suppose that we are interested in the data collected for one of the assets listed in the previous query, for example *fogbench/temperature*. The *asset* entry point can be used to retrieve the data points for individual assets by simply adding the code of the asset to the URI:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/asset/fogbench%2Ftemperature ; echo
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

  $ curl -s http://localhost:8081/fledge/asset/fogbench%2Ftemperature/ambient?limit=5 ; echo
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

The next and last step is to send data to North, which means that we can take all of some of the data we buffer in Fledge and we can send it to a historian or a database using a North task or microservice.


The OMF Translator
------------------

Fledge comes with a North plugin called *OMF Translator*. OMF is the OSIsoft Message Format, which is the message format accepted by the PI Connector Relay OMF. The PI Connector Relay OMF is provided by OSIsoft and it is used to feed the OSIsoft PI System.

- Information regarding OSIsoft are available |here OSIsoft|
- Information regarding OMF are available |here OMF|
- Information regarding the OSIsoft PI System are available |here PI|

*OMF Translator* is scheduled as a North task that is executed every 30 seconds (the time may vary, we set it to 30 seconds to facilitate the testing).


Preparing the PI System
-----------------------

In order to test the North task and plugin, first you need to setup the PI system. Here we assume you are already familiar with PI and you have a Windows server with PI installed, up and running. The minimum installation must include the PI System and the PI Connector Relay OMF. Once you have checked that everything is installed and works correctly, you should collect the IP address of the Windows system.


Setting the OMF Translator Plugin
---------------------------------

Fledge uses the same *OMF Translator* plugin to send two streams of data: the data coming from the South modules and buffered in Fledge and the statistics generated and collected from Fledge. In the current installation, these two streams refer to the categories and streams *SEND_PR_1* (South data) and *SEND_PR_2* (Fledge Statistics).

.. note:: In this version, only the South data can be sent to the PI System.

If you are curious to see which categories are available in Fledge, simply type:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/category ; echo
  { "categories": [ { "key": "SCHEDULER",  "description": "Scheduler configuration"                   },
                    { "key": "SEND_PR_1",  "description": "OMF North Plugin Configuration"            },
                    { "key": "SEND_PR_2",  "description": "OMF North Statistics Plugin Configuration" },
                    { "key": "SEND_PR_4",  "description": "OCS North Plugin Configuration"            },
                    { "key": "SMNTR",      "description": "Service Monitor configuration"             },
                    { "key": "South",      "description": "South Service configuration"               },
                    { "key": "rest_api",   "description": "The Fledge Admin and User REST API"       },
                    { "key": "service",    "description": "The Fledge service configuration"         }
                  ]
  }
  $


For each plugin, you will see corresponding category e.g. For fledge-south-coap the registered category will be ``{ "key": "COAP", "description": "CoAP Listener South Plugin"}``.
The configuration for the OMF Translator used to stream the South data is initially disabled, all you can see about the settings is:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/category/SEND_PR_1 ; echo
  {
    "plugin": {
      "value": "omf",
      "type": "string",
      "default": "omf",
      "description": "Python module name of the plugin to load"
    }
  }
  $

At this point it may be a good idea to familiarize with the |jq| tool, it will help you a lot in selecting and using data via the REST API. You may remember, we discussed it in the |get start| chapter.

First, we can see the list of all the scheduled tasks (the process of sending data to a PI Connector Relay OMF is one of them). The command is:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/schedule | jq
  {
    "schedules": [
      {
        "name": "OMF to OCS north",
        "repeat": 30,
        "time": 0,
        "processName": "North Readings to OCS",
        "exclusive": true,
        "type": "INTERVAL",
        "enabled": false,
        "day": null,
        "id": "5d7fed92-fb9a-11e7-8c3f-9a214cf093ae"
      },
  ...
  $

...which means: "show me all the tasks that can be scheduled", The output has been made more readable by jq. There are several tasks, we need to identify the one we need and extract its unique id. We can achieve that with the power of jq: first we can select the JSON object that shows the elements of the sending task:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/schedule | jq '.schedules[] | select( .name == "OMF to PI north")'
  {
    "id": "2b614d26-760f-11e7-b5a5-be2e44b06b34",
    "name": "OMF to PI north",
    "type": "INTERVAL",
    "repeat": 30,
    "time": 0,
    "day": null,
    "exclusive": true,
    "processName": "North Readings to PI",
    "enabled": false
  }
  $

Let's have a look at what we have found:

- **id** is the unique identifier of the schedule.
- **name** is a user-friendly name of the schedule.
- **type** is the type of schedule, in this case a schedule that is triggered at regular intervals.
- **repeat** specifies the interval of 30 seconds.
- **time** specifies when the schedule should run: since the type is INTERVAL, this element is irrelevant.
- **day** indicates the day of the week the schedule should run, in this case it will be constantly every 30 seconds
- **exclusive** indicates that only a single instance of this task should run at any time.
- **processName** is the name of the task to be executed.
- **enabled** indicates whether the schedule is currently enabled or disabled.

Now let's identify the plugin used to send data to the PI Connector Relay OMF. This is currently identified by the key *SEND_PR_1* (yes, we know it is not intuitive, we will make it better in future releases):

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/category | jq '.categories[] | select ( .key == "SEND_PR_1" )'
  {
    "key":         "SEND_PR_1",
    "description": "OMF North Plugin Configuration"
  }
  $

We can get the specific information adding the name of the task to the URL:

.. code-block:: console

  $  curl -s http://localhost:8081/fledge/category/SEND_PR_1 | jq
  {
    "plugin": {
      "description": "Python module name of the plugin to load",
      "type":        "string",
      "value":       "omf",
      "default":     "omf"
    }
  }
  $

Now, the output returned does not say much: this is because the plugin has never been enabled, so the configuration has not been loaded yet. First, let's enabled the schedule. From a the previous query of the schedulable tasks, we know the id is *2b614d26-760f-11e7-b5a5-be2e44b06b34*:

.. code-block:: console

  $ curl  -X PUT http://localhost:8081/fledge/schedule/2b614d26-760f-11e7-b5a5-be2e44b06b34 -d '{ "enabled" : true }'
  { "schedule": { "id":          "2b614d26-760f-11e7-b5a5-be2e44b06b34",
                  "name":        "OMF to PI north",
                  "type":        "INTERVAL",
                  "repeat":      30.0,
                  "time":        0,
                  "day":         null,
                  "exclusive":   true,
                  "processName": "North Readings to PI",
                  "enabled":     true
                }
  }
  $

Once enabled, the plugin will be executed inside the *SEND_PR_1* task within 30 seconds, so you have to wait up to 30 seconds to see the new, full configuration. After 30 seconds or so, you should see something like this:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/category/SEND_PR_1 | jq
  { "north":             { "description": "The name of the north to use to translate the readings into the output format and send them",
                           "type": "string", "value": "omf", "default": "omf" },
    "OMFRetrySleepTime": { "description": "Seconds between each retry for the communication with the OMF PI Connector Relay",
                           "type": "integer", "value": "1", "default": "1" },
    "filterRule":        { "description": "JQ formatted filter to apply (applicable if applyFilter is True)",
                           "type": "string", "value": ".[]", "default": ".[]" },
    "URL":               { "description": "The URL of the PI Connector to send data to",
                           "type": "string", "value": "https://pi-server:5460/ingress/messages", "default": "https://pi-server:5460/ingress/messages" },
    "plugin":            { "description": "OMF North Plugin",
                           "type": "string", "value": "omf", "default": "omf" },
    "producerToken":     { "description": "The producer token that represents this Fledge stream",
                           "type": "string", "value": "omf_north_0001", "default": "omf_north_0001" },
    "OMFMaxRetry":       { "description": "Max number of retries for the communication with the OMF PI Connector Relay",
                           "type": "integer", "value": "5", "default": "5" },
    "enable":            { "description": "A switch that can be used to enable or disable execution of the sending process.",
                           "type": "boolean", "value": "True", "default": "True" },
    "OMFHttpTimeout":    { "description": "Timeout in seconds for the HTTP operations with the OMF PI Connector Relay",
                           "type": "integer", "value": "30", "default": "30" },
    "StaticData":        { "description": "Static data to include in each sensor reading sent to OMF.",
                           "type": "JSON", "value": "{\"Company\": \"Dianomic\", \"Location\": \"Palo Alto\"}", "default": "{\"Company\": \"Dianomic\", \"Location\": \"Palo Alto\"}" },
    "duration":          { "description": "How long the sending process should run (in seconds) before stopping.",
                           "type": "integer", "value": "60", "default": "60" },
    "sleepInterval":     { "description": "A period of time, expressed in seconds, to wait between attempts to send readings when there are no readings to be sent.",
                           "type": "integer", "value": "5", "default": "5" },
    "source":            { "description": "Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.",
                           "type": "string", "value": "readings", "default": "readings" },
    "blockSize":         { "description": "The size of a block of readings to send in each transmission.",
                           "type": "integer", "value": "5000", "default": "5000" },
    "applyFilter":       { "description": "Whether to apply filter before processing the data",
                           "type": "boolean", "value": "False", "default": "False" },
    "stream_id":         { "description": "Stream ID",
                           "type": "integer", "value": "1", "default": "1" }
  }
  $

You can look at the descriptions to have a taste of what you can control with this plugin. The default configuration should be fine, with the exception of the *URL*, which of course should refer to the IP address of the machine and the port used by the PI Connector Relay OMF. The PI Connector Relay OMF 1.0 used the HTTP protocol with port 8118 and version 1.2, or higher, uses the HTTPS and port 5460. Assuming that the port is *5460* and the IP address is *192.168.56.101*, you can set the new URL with this PUT method:

.. code-block:: console

  $ curl -sH'Content-Type: application/json' -X PUT -d '{ "value": "https://192.168.56.101:5460/ingress/messages" }' http://localhost:8081/fledge/category/SEND_PR_1/URL | jq
  { "description": "The URL of the PI Connector to send data to",
    "type":        "string",
    "value":       "https://192.168.56.101:5460/ingress/messages",
    "default":     "https://pi-server:5460/ingress/messages"
  }
  $

You can note that the *value* element is the only one that can be changed in *URL* (the other elements are factory settings).

Now we are ready to send data North, to the PI System.


Sending Data to the PI System
-----------------------------

The last bit to accomplish is to start the PI Connector Relay OMF on the Windows Server. The output may look like this screenshot, where you can see the Connector Relay debug window on the left and teh PI Data Explorer on the right.

|win_server_waiting|

Wait a few seconds ...et voilà! Readings and statistics are in the PI System:

|pi_loaded|


Congratulations! You have experienced an end-to-end test of Fledge, from South with sensor data through Fledge and East/West applications and finally to North towards Historians.


