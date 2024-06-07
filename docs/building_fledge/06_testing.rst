.. Fledge testing describes how to test Fledge

.. |br| raw:: html

   <br />

.. Images

.. |postman_ping| image:: https://s3.amazonaws.com/fledge/readthedocs/images/05_postman_ping.jpg
   :target: https://s3.amazonaws.com/fledge-iot/readthedocs/images/05_postman_ping.jpg

.. |win_server_waiting| image:: https://s3.amazonaws.com/fledge/readthedocs/images/05_win_server_waiting.jpg
   :target: https://s3.amazonaws.com/fledge-iot/readthedocs/images/05_win_server_waiting.jpg

.. |pi_loaded| image:: https://s3.amazonaws.com/fledge/readthedocs/images/05_pi_loaded.jpg
   :target: https://s3.amazonaws.com/fledge-iot/readthedocs/images/05_pi_loaded.jpg

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
  Fledge v1.8.0 running.
  Fledge Uptime:  9065 seconds.
  Fledge records: 86299 read, 86851 sent, 0 purged.
  Fledge does not require authentication.
  === Fledge services:
  fledge.services.core
  fledge.services.storage --address=0.0.0.0 --port=42583
  fledge.services.south --port=42583 --address=127.0.0.1 --name=Sine
  fledge.services.notification --port=42583 --address=127.0.0.1 --name=Fledge Notifications
  === Fledge tasks:
  fledge.tasks.purge --port=42583 --address=127.0.0.1 --name=purge
  tasks/sending_process --port=42583 --address=127.0.0.1 --name=PI Server
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
  {"uptime": 10480, "dataRead": 0, "dataSent": 0, "dataPurged": 0, "authenticationOptional": true, "serviceName": "Fledge", "hostName": "fledge", "ipAddresses": ["x.x.x.x", "x:x:x:x:x:x:x:x"], "health": "green", "safeMode": false}
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
  $ sudo cp -r python/fledge/plugins/south/coap /usr/local/fledge/python/fledge/plugins/south/
  $ sudo cp python/requirements-coap.txt /usr/local/fledge/python/
  $ sudo python3 -m pip install -r /usr/local/fledge/python/requirements-coap.txt
  $ sudo chown -R root:root /usr/local/fledge/python/fledge/plugins/south/coap
  $ curl -sX POST http://localhost:8081/fledge/service -d '{"name": "CoAP", "type": "south", "plugin": "coap", "enabled": true}'


Depending on your environment, you can call *fogbench* in one of those ways:

- In a development environment, use the script *scripts/extras/fogbench*, inside your project repository (remember to set the *FLEDGE_ROOT* environment variable with the path to your project repository folder).
- In an environment deployed with ``sudo make install``, use the script *bin/fogbench*.

You may call the *fogbench* tool like this:

.. code-block:: console

  $ /usr/local/fledge/bin/fogbench
  >>> Make sure south CoAP plugin service is running & listening on specified host and port
  usage: fogbench [-h] [-v] [-k {y,yes,n,no}] -t TEMPLATE [-o OUTPUT]
                  [-I ITERATIONS] [-O OCCURRENCES] [-H HOST] [-P PORT]
                  [-i INTERVAL] [-S {total}]
  fogbench: error: the following arguments are required: -t/--template
  $

...or more specifically, when you call invoke *fogbench* with the *--help* or *-h* argument:

.. code-block:: console

  $ /usr/local/fledge/bin/fogbench -h
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

The template file looks like this:


.. code-block:: console

  $ cat /usr/local/fledge/data/extras/fogbench/fogbench_sensor_coap.template.json
  [
      { "name"          : "asset_1",
        "sensor_values" : [ { "name": "dp_1", "type": "number", "min": -2.0, "max": 2.0 },
                            { "name": "dp_1", "type": "number", "min": -2.0, "max": 2.0 },
                            { "name": "dp_1", "type": "number", "min": -2.0, "max": 2.0 } ] },
      { "name"          : "asset_2",
        "sensor_values" : [ { "name": "lux", "type": "number", "min": 0, "max": 130000, "precision":3 } ] },
      { "name"          : "asset_3",
        "sensor_values" : [ { "name": "pressure", "type": "number", "min": 800.0, "max": 1100.0, "precision":1 } ] }
  ]
  $

In the array, each element simulates a message from a sensor, with a name, a set of data points that have their name, value type and range.


Data Coming from South
----------------------

Now you should have all the information necessary to test the CoAP South microservice. From the command line, type:

- ``$FLEDGE_ROOT/scripts/extras/fogbench`` ``-t $FLEDGE_ROOT/data/extras/fogbench/fogbench_sensor_coap.template.json``, if you are in a development environment, with the *FLEDGE_ROOT* environment variable set with the path to your project repository folder
- ``$FLEDGE_ROOT/bin/fogbench -t $FLEDGE_DATA/extras/fogbench/fogbench_sensor_coap.template.json``, if you are in a deployed environment, with *FLEDGE_ROOT* and *FLEDGE_DATA* set correctly.
  - If you have installed Fledge in the default location (i.e. */usr/local/fledge*), type ``/usr/local/fledge/bin/fogbench -t data/extras/fogbench/fogbench_sensor_coap.template.json``.

In development environment the output of your command should be:

.. code-block:: console

  $ $FLEDGE_ROOT/scripts/extras/fogbench -t $FLEDGE_ROOT/data/extras/fogbench/fogbench_sensor_coap.template.json
    >>> Make sure south CoAP plugin service is running
     & listening on specified host and port

    Total Statistics:

    Start Time: 2023-04-14 11:15:50.679366
    End Time:   2023-04-14 11:15:50.711856

    Total Messages Transferred: 3
    Total Bytes Transferred:    720

    Total Iterations: 1
    Total Messages per Iteration: 3.0
    Total Bytes per Iteration:    720.0

    Min messages/second: 92.33610341643583
    Max messages/second: 92.33610341643583
    Avg messages/second: 92.33610341643583

    Min Bytes/second: 22160.6648199446
    Max Bytes/second: 22160.6648199446
    Avg Bytes/second: 22160.6648199446
  $

Congratulations! You have just inserted data into Fledge from the CoAP South microservice. More specifically, the output informs you that the data inserted has been composed by 10 different messages for a total of 720 Bytes, for an average of 92 messages per second and 22,160 Bytes per second.

If you want to stress Fledge a bit, you may insert the same data sample several times, by using the *-I* or *--iterations* argument:

.. code-block:: console

  $ $FLEDGE_ROOT/scripts/extras/fogbench -t data/extras/fogbench/fogbench_sensor_coap.template.json -I 100
    >>> Make sure south CoAP plugin service is running & listening on specified host and port
    Total Statistics:

    Start Time: 2023-04-14 11:18:03.586924
    End Time:   2023-04-14 11:18:04.582291

    Total Messages Transferred: 300
    Total Bytes Transferred:    72000

    Total Iterations: 100
    Total Messages per Iteration: 3.0
    Total Bytes per Iteration:    720.0

    Min messages/second: 90.53597295992274
    Max messages/second: 454.33893684688775
    Avg messages/second: 323.7178365566367

    Min Bytes/second: 21728.63351038146
    Max Bytes/second: 109041.34484325306
    Avg Bytes/second: 77692.28077359282
  $

Here we have inserted the same set of data 100 times, therefore the total number of Bytes inserted is 72,000. The performance and insertion rates varies with each iteration and *fogbench* presents the minimum, maximum and average values.


Checking What's Inside Fledge
==============================

We can check if Fledge has now stored what we have inserted from the South microservice by using the *asset* API. From curl or Postman, use this URL:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/asset ; echo
    [{"count": 11, "assetCode": "asset_1"}, {"count": 11, "assetCode": "asset_2"}, {"count": 11, "assetCode": "asset_3"}]
  $

The output of the asset entry point provides a list of assets buffered in Fledge and the count of elements stored. The output is a JSON array with two elements:

- **count** : the number of occurrences of the asset in the buffer.
- **assetCode** : the name of the sensor or device that provides the data.


Feeding East/West Applications
------------------------------

Let's suppose that we are interested in the data collected for one of the assets listed in the previous query, for example *fogbench_temperature*. The *asset* entry point can be used to retrieve the data points for individual assets by simply adding the code of the asset to the URI:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/asset/asset_2 ; echo
    [{"reading": {"lux": 75723.923}, "timestamp": "2023-04-14 11:25:05.672528"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}, {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}]
  $

Let's see the JSON output on a more readable format:

.. code-block:: json

    [
     {"reading": {"lux": 75723.923}, "timestamp": "2023-04-14 11:25:05.672528"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"},
     {"reading": {"lux": 50475.99}, "timestamp": "2023-04-14 11:24:49.767983"}
   ]

The JSON structure depends on the sensor and the plugin used to capture the data. In this case, the values shown are:

- **reading** : a JSON structure that is the set of data points provided by the sensor. In this case only datapoint named lux:
- **lux** : the lux meter value
- **timestamp** : the timestamp generated by the sensors. In this case, since we have inserted 10 times the same value and one time a new value using *fogbench*, the result is 10 timestamps with the same value and one timestamp with a different value.

You can dig even more in the data and extract only a subset of the reading. Fog example, you can select the lux and limit to the last 5 readings:


.. code-block:: console

  $ curl -s http://localhost:8081/fledge/asset/asset_2/lux?limit=5 ; echo
    [
     {"timestamp": "2023-04-14 11:25:05.672528", "lux": 75723.923},
     {"timestamp": "2023-04-14 11:24:49.767983", "lux": 50475.99},
     {"timestamp": "2023-04-14 11:24:49.767983", "lux": 50475.99},
     {"timestamp": "2023-04-14 11:24:49.767983", "lux": 50475.99},
     {"timestamp": "2023-04-14 11:24:49.767983", "lux": 50475.99}
    ]
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

Fledge uses the same *OMF Translator* plugin to send the data coming from the South modules and buffered in Fledge.

.. note:: In this version, only the South data can be sent to the PI System.

If you are curious to see which categories are available in Fledge, simply type:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/category ; echo
  {
      "categories": [
        {
          "key": "Storage",
          "description": "Storage configuration",
          "displayName": "Storage"
        },
        {
          "key": "Advanced",
          "description": "Advanced",
          "displayName": "Advanced"
        },
        {
          "key": "LOGGING",
          "description": "Logging Level of Core Server",
          "displayName": "Logging"
        },
        {
          "key": "SCHEDULER",
          "description": "Scheduler configuration",
          "displayName": "Scheduler"
        },
        {
          "key": "SMNTR",
          "description": "Service Monitor",
          "displayName": "Service Monitor"
        },
        {
          "key": "rest_api",
          "description": "Fledge Admin and User REST API",
          "displayName": "Admin API"
        },
        {
          "key": "password",
          "description": "To control the password policy",
          "displayName": "Password Policy"
        },
        {
          "key": "service",
          "description": "Fledge Service",
          "displayName": "Fledge Service"
        },
        {
          "key": "Installation",
          "description": "Installation",
          "displayName": "Installation"
        },
        {
          "key": "sqlite",
          "description": "Storage Plugin",
          "displayName": "sqlite"
        },
        {
          "key": "General",
          "description": "General",
          "displayName": "General"
        },
        {
          "key": "Utilities",
          "description": "Utilities",
          "displayName": "Utilities"
        },
        {
          "key": "purge_system",
          "description": "Configuration of the Purge System",
          "displayName": "Purge System"
        },
        {
          "key": "PURGE_READ",
          "description": "Purge the readings, log, statistics history table",
          "displayName": "Purge"
        }
      ]
  }
  $


For each plugin, you will see corresponding category e.g. For fledge-south-coap the registered category will be ``{ "key": "COAP", "description": "CoAP Listener South Plugin"}``.
The configuration for the OMF Translator used to stream the South data is initially disabled, all you can see about the settings is:

.. code-block:: console

  $ curl -sX GET   http://localhost:8081/fledge/category/OMF%20to%20PI%20north
  {
    "enable": {
      "description": "A switch that can be used to enable or disable execution of the sending process.",
      "type": "boolean",
      "readonly": "true",
      "default": "true",
      "value": "true"
    },
    "streamId": {
      "description": "Identifies the specific stream to handle and the related information, among them the ID of the last object streamed.",
      "type": "integer",
      "readonly": "true",
      "default": "0",
      "value": "4",
      "order": "16"
    },
    "plugin": {
      "description": "PI Server North C Plugin",
      "type": "string",
      "default": "OMF",
      "readonly": "true",
      "value": "OMF"
    },
    "source": {
       "description": "Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.",
       "type": "enumeration",
       "options": [
         "readings",
         "statistics"
        ],
      "default": "readings",
      "order": "5",
      "displayName": "Data Source",
      "value": "readings"
    },
  ...}
  $ curl -sX GET   http://localhost:8081/fledge/category/Stats%20OMF%20to%20PI%20north
  {
    "enable": {
      "description": "A switch that can be used to enable or disable execution of the sending process.",
      "type": "boolean",
      "readonly": "true",
      "default": "true",
      "value": "true"
    },
    "streamId": {
      "description": "Identifies the specific stream to handle and the related information, among them the ID of the last object streamed.",
      "type": "integer",
      "readonly": "true",
      "default": "0",
      "value": "5",
      "order": "16"
    },
    "plugin": {
      "description": "PI Server North C Plugin",
      "type": "string",
      "default": "OMF",
      "readonly": "true",
      "value": "OMF"
    },
    "source": {
      "description": "Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.",
      "type": "enumeration",
      "options": [
        "readings",
        "statistics"
       ],
      "default": "readings",
      "order": "5",
      "displayName": "Data Source",
      "value": "statistics"
    },
  ...}
  $

At this point it may be a good idea to familiarize with the |jq| tool, it will help you a lot in selecting and using data via the REST API. You may remember, we discussed it in the |get start| chapter.

First, we can see the list of all the scheduled tasks (the process of sending data to a PI Connector Relay OMF is one of them). The command is:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/schedule | jq
  {
    "schedules": [
      {
        "id": "ef8bd42b-da9f-47c4-ade8-751ce9a504be",
        "name": "OMF to PI north",
        "processName": "north_c",
        "type": "INTERVAL",
        "repeat": 30.0,
        "time": 0,
        "day": null,
        "exclusive": true,
        "enabled": false
      },
      {
        "id": "27501b35-e0cd-4340-afc2-a4465fe877d6",
        "name": "Stats OMF to PI north",
        "processName": "north_c",
        "type": "INTERVAL",
        "repeat": 30.0,
        "time": 0,
        "day": null,
        "exclusive": true,
        "enabled": true
      },
    ...
    ]
  }
  $

...which means: "show me all the tasks that can be scheduled", The output has been made more readable by jq. There are several tasks, we need to identify the one we need and extract its unique id. We can achieve that with the power of jq: first we can select the JSON object that shows the elements of the sending task:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/schedule | jq '.schedules[] | select( .name == "OMF to PI north")'
  {
    "id": "ef8bd42b-da9f-47c4-ade8-751ce9a504be",
    "name": "OMF to PI north",
    "processName": "north_c",
    "type": "INTERVAL",
    "repeat": 30,
    "time": 0,
    "day": null,
    "exclusive": true,
    "enabled": true
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

Now let's identify the plugin used to send data to the PI Connector Relay OMF.

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/category | jq '.categories[] | select ( .key == "OMF to PI north" )'
  {
    "key": "OMF to PI north",
    "description": "Configuration of the Sending Process",
    "displayName": "OMF to PI north"
  }
  $

We can get the specific information adding the name of the task to the URL:

.. code-block:: console

  $  curl -s http://localhost:8081/fledge/category/OMF%20to%20PI%20north | jq .plugin
  {
    "description": "PI Server North C Plugin",
    "type": "string",
    "default": "OMF",
    "readonly": "true",
    "value": "OMF"
  }
  $

Now, the output returned does not say much: this is because the plugin has never been enabled, so the configuration has not been loaded yet. First, let's enabled the schedule. From a the previous query of the schedulable tasks, we know the id is *ef8bd42b-da9f-47c4-ade8-751ce9a504be*:

.. code-block:: console

  $ curl  -X PUT http://localhost:8081/fledge/schedule/ef8bd42b-da9f-47c4-ade8-751ce9a504be -d '{ "enabled" : true }'
  {
    "schedule": {
      "id": "ef8bd42b-da9f-47c4-ade8-751ce9a504be",
      "name": "OMF to PI north",
      "processName": "north_c",
      "type": "INTERVAL",
      "repeat": 30,
      "time": 0,
      "day": null,
      "exclusive": true,
      "enabled": true
    }
  }
  $

Once enabled, the plugin will be executed inside the *OMF to PI north* task within 30 seconds, so you have to wait up to 30 seconds to see the new, full configuration. After 30 seconds or so, you should see something like this:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/category/OMF%20to%20PI%20north | jq
  {
    "enable": {
      "description": "A switch that can be used to enable or disable execution of the sending process.",
      "type": "boolean",
      "readonly": "true",
      "default": "true",
      "value": "true"
    },
    "streamId": {
      "description": "Identifies the specific stream to handle and the related information, among them the ID of the last object streamed.",
      "type": "integer",
      "readonly": "true",
      "default": "0",
      "value": "4",
      "order": "16"
    },
    "plugin": {
      "description": "PI Server North C Plugin",
      "type": "string",
      "default": "OMF",
      "readonly": "true",
      "value": "OMF"
    },
    "PIServerEndpoint": {
      "description": "Select the endpoint among PI Web API, Connector Relay, OSIsoft Cloud Services or Edge Data Store",
      "type": "enumeration",
      "options": [
      "PI Web API",
      "Connector Relay",
      "OSIsoft Cloud Services",
      "Edge Data Store"
    ],
      "default": "Connector Relay",
      "order": "1",
      "displayName": "Endpoint",
      "value": "Connector Relay"
    },
    "ServerHostname": {
      "description": "Hostname of the server running the endpoint either PI Web API or Connector Relay",
      "type": "string",
      "default": "localhost",
      "order": "2",
      "displayName": "Server hostname",
      "validity": "PIServerEndpoint != \"Edge Data Store\" && PIServerEndpoint != \"OSIsoft Cloud Services\"",
      "value": "localhost"
    },
    "ServerPort": {
      "description": "Port on which the endpoint either PI Web API or Connector Relay or Edge Data Store is listening, 0 will use the default one",
      "type": "integer",
      "default": "0",
      "order": "3",
      "displayName": "Server port, 0=use the default",
      "validity": "PIServerEndpoint != \"OSIsoft Cloud Services\"",
      "value": "0"
    },
    "producerToken": {
      "description": "The producer token that represents this Fledge stream",
      "type": "string",
      "default": "omf_north_0001",
      "order": "4",
      "displayName": "Producer Token",
      "validity": "PIServerEndpoint == \"Connector Relay\"",
      "value": "omf_north_0001"
    },
    "source": {
      "description": "Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.",
      "type": "enumeration",
      "options": [
        "readings",
        "statistics"
      ],
      "default": "readings",
      "order": "5",
      "displayName": "Data Source",
      "value": "readings"
    },
    "StaticData": {
      "description": "Static data to include in each sensor reading sent to the PI Server.",
      "type": "string",
      "default": "Location: Palo Alto, Company: Dianomic",
      "order": "6",
      "displayName": "Static Data",
      "value": "Location: Palo Alto, Company: Dianomic"
    },
    "OMFRetrySleepTime": {
      "description": "Seconds between each retry for the communication with the OMF PI Connector Relay, NOTE : the time is doubled at each attempt.",
      "type": "integer",
      "default": "1",
      "order": "7",
      "displayName": "Sleep Time Retry",
      "value": "1"
    },
	  "OMFMaxRetry": {
		  "description": "Max number of retries for the communication with the OMF PI Connector Relay",
		  "type": "integer",
		  "default": "3",
		  "order": "8",
		  "displayName": "Maximum Retry",
		  "value": "3"
	  },
    "OMFHttpTimeout": {
      "description": "Timeout in seconds for the HTTP operations with the OMF PI Connector Relay",
      "type": "integer",
      "default": "10",
      "order": "9",
      "displayName": "HTTP Timeout",
      "value": "10"
    },
    "formatInteger": {
      "description": "OMF format property to apply to the type Integer",
      "type": "string",
      "default": "int64",
      "order": "10",
      "displayName": "Integer Format",
      "value": "int64"
    },
    "formatNumber": {
      "description": "OMF format property to apply to the type Number",
      "type": "string",
      "default": "float64",
      "order": "11",
      "displayName": "Number Format",
      "value": "float64"
    },
    "compression": {
      "description": "Compress readings data before sending to PI server",
      "type": "boolean",
      "default": "true",
      "order": "12",
      "displayName": "Compression",
      "value": "false"
    },
    "DefaultAFLocation": {
      "description": "Defines the hierarchies tree in Asset Framework in which the assets will be created, each level is separated by /, PI Web API only.",
      "type": "string",
      "default": "/fledge/data_piwebapi/default",
      "order": "13",
      "displayName": "Asset Framework hierarchies tree",
      "validity": "PIServerEndpoint == \"PI Web API\"",
      "value": "/fledge/data_piwebapi/default"
    },
    "AFMap": {
      "description": "Defines a set of rules to address where assets should be placed in the AF hierarchy.",
      "type": "JSON",
      "default": "{ }",
      "order": "14",
      "displayName": "Asset Framework hierarchies rules",
      "validity": "PIServerEndpoint == \"PI Web API\"",
      "value": "{ }"
    },
    "notBlockingErrors": {
      "description": "These errors are considered not blocking in the communication with the PI Server, the sending operation will proceed with the next block of data if one of these is encountered",
      "type": "JSON",
      "default": "{ \"errors400\" : [ \"Redefinition of the type with the same ID is not allowed\", \"Invalid value type for the property\", \"Property does not exist in the type definition\", \"Container is not defined\", \"Unable to find the property of the container of type\" ] }",
      "order": "15",
      "readonly": "true",
      "value": "{ \"errors400\" : [ \"Redefinition of the type with the same ID is not allowed\", \"Invalid value type for the property\", \"Property does not exist in the type definition\", \"Container is not defined\", \"Unable to find the property of the container of type\" ] }"
    },
    "PIWebAPIAuthenticationMethod": {
      "description": "Defines the authentication method to be used with the PI Web API.",
      "type": "enumeration",
      "options": [
        "anonymous",
        "basic",
        "kerberos"
      ],
      "default": "anonymous",
      "order": "17",
      "displayName": "PI Web API Authentication Method",
      "validity": "PIServerEndpoint == \"PI Web API\"",
      "value": "anonymous"
    },
    "PIWebAPIUserId": {
      "description": "User id of PI Web API to be used with the basic access authentication.",
      "type": "string",
      "default": "user_id",
      "order": "18",
      "displayName": "PI Web API User Id",
      "validity": "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"basic\"",
      "value": "user_id"
    },
    "PIWebAPIPassword": {
      "description": "Password of the user of PI Web API to be used with the basic access authentication.",
      "type": "password",
      "default": "password",
      "order": "19",
      "displayName": "PI Web API Password",
      "validity": "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"basic\"",
      "value": "****"
    },
    "PIWebAPIKerberosKeytabFileName": {
      "description": "Keytab file name used for Kerberos authentication in PI Web API.",
      "type": "string",
      "default": "piwebapi_kerberos_https.keytab",
      "order": "20",
      "displayName": "PI Web API Kerberos keytab file",
      "validity": "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"kerberos\"",
      "value": "piwebapi_kerberos_https.keytab"
    },
    "OCSNamespace": {
      "description": "Specifies the OCS namespace where the information are stored and it is used for the interaction with the OCS API",
      "type": "string",
      "default": "name_space",
      "order": "21",
      "displayName": "OCS Namespace",
      "validity": "PIServerEndpoint == \"OSIsoft Cloud Services\"",
      "value": "name_space"
    },
    "OCSTenantId": {
      "description": "Tenant id associated to the specific OCS account",
      "type": "string",
      "default": "ocs_tenant_id",
      "order": "22",
      "displayName": "OCS Tenant ID",
      "validity": "PIServerEndpoint == \"OSIsoft Cloud Services\"",
      "value": "ocs_tenant_id"
    },
    "OCSClientId": {
      "description": "Client id associated to the specific OCS account, it is used to authenticate the source for using the OCS API",
      "type": "string",
      "default": "ocs_client_id",
      "order": "23",
      "displayName": "OCS Client ID",
      "validity": "PIServerEndpoint == \"OSIsoft Cloud Services\"",
      "value": "ocs_client_id"
    },
    "OCSClientSecret": {
      "description": "Client secret associated to the specific OCS account, it is used to authenticate the source for using the OCS API",
      "type": "password",
      "default": "ocs_client_secret",
      "order": "24",
      "displayName": "OCS Client Secret",
      "validity": "PIServerEndpoint == \"OSIsoft Cloud Services\"",
      "value": "****"
    }
  }
  $

You can look at the descriptions to have a taste of what you can control with this plugin. The default configuration should be fine, with the exception of the *ServerHostname*, which of course should refer to the IP address of the machine and the port used by the PI Connector Relay OMF. The PI Connector Relay OMF 1.0 used the HTTP protocol with port 8118 and version 1.2, or higher, uses the HTTPS and port 5460. Assuming that the port is *5460* and the IP address is *192.168.56.101*, you can set the new ServerHostname with this PUT method:

.. code-block:: console

  $ curl -sH'Content-Type: application/json' -X PUT -d '{ "ServerHostname": "192.168.56.101" }' http://localhost:8081/fledge/category/OMF%20to%20PI%20north | jq
  "ServerHostname": {
    "description": "Hostname of the server running the endpoint either PI Web API or Connector Relay",
    "type": "string",
    "default": "localhost",
    "order": "2",
    "displayName": "Server hostname",
    "validity": "PIServerEndpoint != \"Edge Data Store\" && PIServerEndpoint != \"OSIsoft Cloud Services\"",
    "value": "192.168.56.101"
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


