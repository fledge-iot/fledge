.. Testing your Plugin

.. |br| raw:: html

   <br/>

.. Links
.. |expression filter| raw:: html

   <a href="../plugins/fledge-filter-expression/index.html">expression filter</a>

.. |Python 3.5 filter| raw:: html

   <a href="../plugins/fledge-filter-python35/index.html">Python 3.5 filter</a>

Testing Your Plugin
===================

The first step in testing your new plugin is to put the plugin in the
location in which your Fledge system will be loading it from. The exact
location depends on the way your installed you Fledge system and the
type of plugin.

If your Fledge system was installed from a package and you used the
default installation path, then your plugin must be stored under the
directory */usr/local/fledge*. If you installed Fledge in a nonstandard
location or your have built it from the source code, then the plugin
should be stored under the directory *$FLEDGE_ROOT*.

A C/C++ plugin or a hybrid plugin should be placed in the directory
*plugins/<type>/<plugin name>* under the installed directory
described above. Where *<type>* is one of *south*, *filter*, *north*,
*notificationRule* or *notificationDelivery*. And *<plugin name>* is
the name you gave your plugin.

A south plugin written in C/C++ and called DHT11, for a system
installed from a package, would be installed in a directory called
*/usr/local/fledge/plugins/south/DHT11*. Within that directory Fledge
would expect to find a file called *libDHT11.so*.

A south hybrid plugin called MD1421, for a development system built from
source would be installed in *${FLEDGE_ROOT}/plugins/south/MD1421*. In
this directory a JSON file called *MD1421.json* should exist, this is
what the system will read to create the plugin.

A Python plugin should be installed in the directory
*python/fledge/plugins/<plugin type>/<plugin name>* under the installed
directory described above. Where *<type>* is one of *south*, *filter*,
*north*, *notificationRule* or *notificationDelivery*. And *<plugin name>*
is the name you gave your plugin.

A Python filter plugin called normalise, on a system installed from
a package in the default location should be copied into a directory
*/usr/local/fledge/python/fledge/plugins/filter/normalise*. Within
this directory should be a file called *normalise.py* and an empty file
called *__init__.py*.

Initial Testing
---------------

After you have copied your plugin into the correct location
you can test if Fledge is able to see it by running the API call
*/fledge/plugins/installed*. This will list all the installed plugins
and their versions.

.. code-block:: console

   $ curl http://localhost:8081/fledge/plugins/installed | jq
   {
     "plugins": [
       {
         "name": "http_north",
         "type": "north",
         "description": "HTTP North Plugin",
         "version": "2.2.0",
         "installedDirectory": "north/http_north",
         "packageName": "fledge-north-http-north"
       },
       {
         "name": "Kafka",
         "type": "north",
         "description": "Simple plugin to send data to Kafka topic",
         "version": "2.2.0",
         "installedDirectory": "north/Kafka",
         "packageName": "fledge-north-kafka"
       },
   ...
   }

Note, in the above example the *jq* program has been used to format the
returned JSON and the output has been truncated for brevity.

If your plugin does not appear it may be because there was a problem
loading it or because the *plugin_info* call returned a bad value. Examine
the syslog file to see if there are any errors recorded during the above
API call.

C/C++ Common Faults
-------------------

Common faults for C/C++ plugins are that a symbol could not be resolved
when the plugin was loaded or the JSON for the default configuration
is malformed.

There is a utility called *get_plugin_info* that is used by Python code
to call the C *plugin_info* call, this can be used to ascertain the
cause of some problems. It should return the default configuration of
your plugin and will verify that your plugin has no undefined symbols.

The location of *get_plugin_info* will depend on the type of
installation you have. If you have built from source then it can
be found in *./cmake_build/C/plugins/utils/get_plugin_info*. If you
have installed a package, or run *make install*, you can find it in
*/usr/local/fledge/extras/C/get_plugin_info*.

The utility is passed the library file of your plugin as its first argument
and the function to call, usually *plugin_info*.

.. code-block:: console

   $ ./get_plugin_info /usr/local/fledge/plugins/north/Kafka/libKafka.so plugin_info
    {"name": "Kafka", "type": "north", "flag": 0, "version": "2.2.0", "interface": "1.0.0", "config": {"SSL_CERT": {"displayName": "Certificate Name", "description": "Name of client certificate for identity authentications", "default": "", "validity": "KafkaSecurityProtocol == \"SSL\" || KafkaSecurityProtocol == \"SASL_SSL\"", "group": "Encryption", "type": "string", "order": "10"}, "topic": {"mandatory": "true", "description": "The topic to send reading data on", "default": "Fledge", "displayName": "Kafka Topic", "type": "string", "order": "2"}, "brokers": {"displayName": "Bootstrap Brokers", "description": "The bootstrap broker list to retrieve full Kafka brokers", "default": "localhost:9092,kafka.local:9092", "mandatory": "true", "type": "string", "order": "1"}, "KafkaUserID": {"group": "Authentication", "description": "User ID to be used with SASL_PLAINTEXT security protocol", "default": "user", "validity": "KafkaSecurityProtocol == \"SASL_PLAINTEXT\" || KafkaSecurityProtocol == \"SASL_SSL\"", "displayName": "User ID", "type": "string", "order": "7"}, "KafkaSASLMechanism": {"group": "Authentication", "description": "Authentication mechanism to be used to connect to kafka broker", "default": "PLAIN", "displayName": "SASL Mechanism", "type": "enumeration", "order": "6", "validity": "KafkaSecurityProtocol == \"SASL_PLAINTEXT\" || KafkaSecurityProtocol == \"SASL_SSL\"", "options": ["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"]}, "SSL_Password": {"displayName": "Certificate Password", "description": "Optional: Password to be used when loading the certificate chain", "default": "", "validity": "KafkaSecurityProtocol == \"SSL\" || KafkaSecurityProtocol == \"SASL_SSL\"", "group": "Encryption", "type": "password", "order": "12"}, "compression": {"displayName": "Compression Codec", "description": "The compression codec to be used to send data to the Kafka broker", "default": "none", "order": "4", "type": "enumeration", "options": ["none", "gzip", "snappy", "lz4"]}, "plugin": {"default": "Kafka", "readonly": "true", "type": "string", "description": "Simple plugin to send data to a Kafka topic"}, "KafkaSecurityProtocol": {"group": "Authentication", "description": "Security protocol to be used to connect to kafka broker", "default": "PLAINTEXT", "options": ["PLAINTEXT", "SASL_PLAINTEXT", "SSL", "SASL_SSL"], "displayName": "Security Protocol", "type": "enumeration", "order": "5"}, "source": {"displayName": "Data Source", "description": "The source of data to send", "default": "readings", "order": "13", "type": "enumeration", "options": ["readings", "statistics"]}, "json": {"displayName": "Send JSON", "description": "Send as JSON objects or as strings", "default": "Strings", "order": "3", "type": "enumeration", "options": ["Objects", "Strings"]}, "SSL_CA_File": {"displayName": "Root CA Name", "description": "Name of the root certificate authority that will be used to verify the certificate", "default": "", "validity": "KafkaSecurityProtocol == \"SSL\" || KafkaSecurityProtocol == \"SASL_SSL\"", "group": "Encryption", "type": "string", "order": "9"}, "SSL_Keyfile": {"displayName": "Private Key Name", "description": "Name of client private key required for communication", "default": "", "validity": "KafkaSecurityProtocol == \"SSL\" || KafkaSecurityProtocol == \"SASL_SSL\"", "group": "Encryption", "type": "string", "order": "11"}, "KafkaPassword": {"group": "Authentication", "description": "Password to be used with SASL_PLAINTEXT security protocol", "default": "pass", "validity": "KafkaSecurityProtocol == \"SASL_PLAINTEXT\" || KafkaSecurityProtocol == \"SASL_SSL\"", "displayName": "Password", "type": "password", "order": "8"}}}


If there is an undefined symbol you will get an error from this
utility. You can also check the validity of your JSON configuration by
piping the output to a program such as jq.

.. code-block:: console

   $ ./get_plugin_info plugins/south/Random/libRandom.so plugin_info | jq
    {
      "name": "Random",
      "version": "1.9.2",
      "type": "south",
      "interface": "1.0.0",
      "flag": 4096,
      "config": {
        "plugin": {
          "description": "Random data generation plugin",
          "type": "string",
          "default": "Random",
          "readonly": "true"
        },
        "asset": {
          "description": "Asset name",
          "type": "string",
          "default": "Random",
          "displayName": "Asset Name",
          "mandatory": "true"
        }
      }
    }

Running Under a Debugger
------------------------

If you have a C/C++ plugin that crashes you may want to run the plugin under a debugger. To build with debug symbols use the CMake option *-DCMAKE_BUILD_TYPE=Debug* when you create the *Makefile*.

Running a Service Under the Debugger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

   $ cmake -DCMAKE_BUILD_TYPE=Debug ..


The easiest approach to run under a debugger is 

  - Create the service that uses your plugin, say a south service and name that service as you normally would.
   
  - Disable that service from being started by Fledge

  - Use the fledge status script to find the arguments to pass the service

    .. code-block:: console

       $ scripts/fledge status
       Fledge v1.8.2 running.
       Fledge Uptime:  1451 seconds.
       Fledge records: 200889 read, 200740 sent, 120962 purged.
       Fledge does not require authentication.
       === Fledge services:
       fledge.services.core
       fledge.services.storage --address=0.0.0.0 --port=39821
       fledge.services.south --port=39821 --address=127.0.0.1 --name=AX8
       fledge.services.south --port=39821 --address=127.0.0.1 --name=Sine
       === Fledge tasks:

   - Note the *--port=* and *--address=* arguments

   - Set your LD_LIBRARY_PATH. This is normally done in the script that launches Fledge but will need to be run as a manual step when running under the debugger.

     .. code-block:: console

        export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/fledge/lib

     If you built from source rather than installing a package you will need to include the libraries you built

     .. code-block:: console

        export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${FLEDGE_ROOT}/cmake_build/C/lib

   - Get a startup token by calling the Fledge API endpoint

     *Note*: the caller must be authenticated as the *admin* user using either the username and password authentication or the certificate authentication mechanism in order to call the API endpoint.
     You must first set Fledge to require authentication.
     To do this, launch the Fledge GUI, navigate to Configuration and then Admin API.
     Set Authentication to *mandatory*.
     Authentication Method can be left as *any*.

     In order to authenticate as the *admin* user one of the two following methods should be used, the choice of which is dependant on the authentication mechanism configured in your Fledge installation.

     - User and password login

       .. code-block:: console

          curl -d '{"username": "admin", "some_pass": "fledge"}' -X POST http://localhost:8081/fledge/login

       Successful authentication will produce a response as shown below.

       .. code-block:: console

          {"message": "Logged in successfully", "uid": 1, "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOjEsImV4cCI6MTY1NDU5NTIyMn0.IlhIgQ93LbCP-ztGlIuJVd6AJrBlbNBNvCv7SeuMfAs", "admin": true}

     - Certificate login

       .. code-block:: console

          curl -T /some_path/admin.cert -X POST http://localhost:8081/fledge/login

       Successful authentication will produce a response as shown below.

       .. code-block:: console

          {"message": "Logged in successfully", "uid": 1, "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOjEsImV4cCI6MTY1NDU5NTkzN30.6VVD_5RwmpLga2A7ri2bXhlo3x_CLqOYiefAAmLP63Y", "admin": true}

   It is now possible to call the API endpoint to retrieve a startup token by passing the authentication token given in the authentication request.

   .. code-block:: console

      curl -X POST 127.0.0.1:8081/fledge/service/ServiceName/otp -H 'authorization: Token'

   Where *ServiceName* is the name you gave your service when you created it and *Token* received by the authentication request above.

   This call will respond with a startup token that can be used to start the service you are debugging. An example response is shown below.

   .. code-block:: console

      {"startupToken": "WvFTYeGUvSEFMndePGbyvOsVYUzbnJdi"}

   *startupToken* will be passed as service start argument: --token=*startupToken*

   - Load the service you wish to use to run your plugin, e.g. a south service, under the debugger. This should be run from the FLEDGE_ROOT directory

     .. code-block:: console

        $ cd $FLEDGE_ROOT
        $ gdb services/fledge.services.south

   - Run the service passing the *--port=* and *--address=* arguments you noted above and add *-d* and *--name=* with the name of your service and *--token=startupToken*

     .. code-block:: console

        (gdb) run --port=39821 --address=127.0.0.1 --name=ServiceName -d --token=startupToken

     Where *ServiceName* is the name you gave your service when you created it and startupToken is the token issued using the method described above. Note, this token may only be used once, each time the service is restarted using the debugger a new startup token must be obtained.

   - You can now use the debugger in the way you normally would to find any issues.

     .. note::
     
        At this stage the plugins have not been loaded into the address space. If you try to set a break point in the plugin code you will get a warning that the break point can not currently be set. However when the plugin is later loaded the break point will be set and behave as expected.

Only the plugin has been built with debug information, if you wish to be able to single step into the library code that supports the plugin, and the services you must rebuild Fledge itself with debug symbols. There are multiple ways this can be done, but perhaps the simplest approach is to modify the *Makefile* in the route of the Fledge source.

When building Fledge the *cmake* command is executed by the make process, hence rather than manually running cmake and rebuilding you can simple alter the line

.. code-block:: console

   CMAKE := cmake

in the *Makefile* to read

.. code-block:: console

   CMAKE := cmake -DCMAKE_BUILD_TYPE=Debug

After making this change you should run a *make clean* followed by a *make* command

.. code-block:: console

   $ make clean
   $ make

One side effect of this, caused by running *make clean* is that the plugins you have previously built have been removed from the $FLEDGE_ROOT/plugins directory and this must be rebuilt.

Alternatively you can manually build a debug version by running the following commands

.. code-block:: console

   $ cd $FLEDGE_ROOT/cmake_build
   $ cmake -DCMAKE_BUILD_TYPE=Debug ..
   $ make

This has the advantage that *make clean* is not run so your plugins will be preserved.

Running a Task Under the Debugger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Running a task under the debugger is much the same as running a service,
you will first need to find the management port and address of the core
management service. Create the task, e.g. a north sending process in
the same way as you normally would and disable it. You will also need
to set your LD_LIBRARY_PATH as with running a service under the debugger.

If you are using a plugin with a task, such as the north sending process
task, then the command to use to start the debugger is

.. code-block:: console

   $ gdb tasks/sending_process

Running the Storage Service Under the Debugger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Running the storage service under the debugger is more difficult as you can not start the storage service after Fledge has started, the startup of the storage service is coordinated by the core due to the nature of how configuration is stored. It is possible however to attach a debugger to a running storage service.

  - Run a command to find the process ID of the storage service

    .. code-block:: console

       $ ps aux | grep fledge.services.storage
       fledge  23318  0.0  0.3 270848 12388 ?        Ssl  10:00   0:01 /usr/local/fledge/services/fledge.services.storage --address=0.0.0.0 --port=33761
       fledge  31033  0.0  0.0  13136  1084 pts/1    S+   10:37   0:00 grep --color=auto fledge.services.storage

    - Use the process ID of the fledge service as an argument to gdb. Note you will need to run gdb as root on some systems

      .. code-block:: console

          $ sudo gdb /usr/local/fledge/services/fledge.services.storage 23318
          GNU gdb (Ubuntu 8.1-0ubuntu3) 8.1.0.20180409-git
          Copyright (C) 2018 Free Software Foundation, Inc.
          License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
          This is free software: you are free to change and redistribute it.
          There is NO WARRANTY, to the extent permitted by law.  Type "show copying"
          and "show warranty" for details.
          This GDB was configured as "x86_64-linux-gnu".
          Type "show configuration" for configuration details.
          For bug reporting instructions, please see:
          <http://www.gnu.org/software/gdb/bugs/>.
          Find the GDB manual and other documentation resources online at:
          <http://www.gnu.org/software/gdb/documentation/>.
          For help, type "help".
          Type "apropos word" to search for commands related to "word"...
          Reading symbols from services/fledge.services.storage...done.
          Attaching to program: /usr/local/fledge/services/fledge.services.storage, process 23318
          [New LWP 23320]
          [New LWP 23321]
          [New LWP 23322]
          [New LWP 23330]
          [Thread debugging using libthread_db enabled]
          Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
          0x00007f47a3e05d2d in __GI___pthread_timedjoin_ex (threadid=139945627997952, thread_return=0x0, abstime=0x0,
              block=<optimized out>) at pthread_join_common.c:89
          89	pthread_join_common.c: No such file or directory.
          (gdb)

   - You can now use gdb to set break points etc and debug the storage service and plugins.

If you are debugger a plugin that crashes the system when readings are
processed you should disable the south services until you have connected
the debugger to the storage system. If you have a system that is setup
and crashes, use the --safe-mode flag to the startup of Fledge in order
to disable all processes and services. This will allow you to disable
services or to run a particular service manually.

Using strace
------------

You can also use a similar approach to that of running gdb to use the *strace* command to trace system calls and signals

  - Create the service that uses your plugin, say a south service and name that service as you normally would.
   
  - Disable that service from being started by Fledge

  - Use the fledge status script to find the arguments to pass the service

    .. code-block:: console

       $ scripts/fledge status
       Fledge v1.8.2 running.
       Fledge Uptime:  1451 seconds.
       Fledge records: 200889 read, 200740 sent, 120962 purged.
       Fledge does not require authentication.
       === Fledge services:
       fledge.services.core
       fledge.services.storage --address=0.0.0.0 --port=39821
       fledge.services.south --port=39821 --address=127.0.0.1 --name=AX8
       fledge.services.south --port=39821 --address=127.0.0.1 --name=Sine
       === Fledge tasks:

   - Note the *--port=* and *--address=* arguments

   - Run *strace* with the service adding the same set of arguments you used in gdb when running the service

     .. code-block:: console

        $ strace services/fledge.services.south --port=39821 --address=127.0.0.1 --name=ServiceName --token=StartupToken -d

     Where *ServiceName* is the name you gave your service and *startupToken* as issued following above steps.

Memory Leaks and Corruptions
----------------------------

Fledge has integrated support that allows south and north services to be run using the *valgrind* tool.  This tool makes it easy to find memory corruption and leak issues in your plugin

  - Create the service that uses your plugin, say a south service and name that service as you normally would.
   
  - Shutdown Fledge

  - If using a south service to test your plugin set the environment variable VALGRIND_SOUTH to be the name of the service you just defined.

  - Start Fledge using the *fledge* script in the scripts directory.

  - Allow Fledge to run for some time. Note that the service running under *valgrind* will run much more slowly that it does outside of *valgrind*. You may have to allow it to run for more time than expected.

  - Shutdown Fledge. Again this may take longer than normal.

You will see a file created in your home directory called *south.serviceName.valgrind.out*. This is a text file that contains the result of running *valgrind*. Refer to the standard *valgrind* documentation for information on how to interpret this file.

If developing a plugin to run in a north service, then the variable VALGRIND_NORTH should be set.

Multiple services may be run under *valgrind* by setting the appropriate variable to be a comma separated list of service names.

Compiling under debug mode, by setting *CFLAGS=-DDebug* will allow *valgrind* to pinpoint memory leaks and corruptions to particular lines of your source code.

.. note::

   Don't forget to clear the environment variable once you have completed your analysis otherwise you will degrade the performance of the service.

Python Plugin Info
------------------

It is also possible to test the loading and validity of the *plugin_info* call in a Python plugin.

  - From the */usr/include/fledge* or *${FLEDGE_ROOT}* directory run the command

    .. code-block:: console

       python3 -c 'from fledge.plugins.south.<name>.<name> import plugin_info; print(plugin_info())'

    Where *<name>* is the name of your plugin.

    .. code-block:: console

       python3 -c 'from fledge.plugins.south.sinusoid.sinusoid import plugin_info; print(plugin_info())'
       {'name': 'Sinusoid Poll plugin', 'version': '1.8.1', 'mode': 'poll', 'type': 'south', 'interface': '1.0', 'config': {'plugin': {'description': 'Sinusoid Poll Plugin which implements sine wave with data points', 'type': 'string', 'default': 'sinusoid', 'readonly': 'true'}, 'assetName': {'description': 'Name of Asset', 'type': 'string', 'default': 'sinusoid', 'displayName': 'Asset name', 'mandatory': 'true'}}}

This allows you to confirm the plugin can be loaded and the *plugin_info* entry point can be called.

You can also check your default configuration. Although in Python this is usually harder to get wrong.

.. code-block:: console

   $ python3 -c 'from fledge.plugins.south.sinusoid.sinusoid import plugin_info; print(plugin_info()["config"])'
   {'plugin': {'description': 'Sinusoid Poll Plugin which implements sine wave with data points', 'type': 'string', 'default': 'sinusoid', 'readonly': 'true'}, 'assetName': {'description': 'Name of Asset', 'type': 'string', 'default': 'sinusoid', 'displayName': 'Asset name', 'mandatory': 'true'}}

Plugin Configuration Validation
-------------------------------

The plugin configuration validation feature provides automated connectivity testing for plugin configurations. This feature validates that network-related configuration parameters are correct and reachable before deploying or activating a plugin, helping to identify configuration issues early in the plugin testing process.

This is the first iteration of the configuration validation feature, focusing on network connectivity validation for common plugin patterns.

Overview
~~~~~~~~

The validation system performs two primary types of tests:

**Host Reachability Test**
   Tests whether the configured host or server is reachable over the network using socket-based connectivity testing.

**Listening Test**
   Tests whether a service is actively listening on the specified host and port combination.

The validation automatically detects relevant configuration fields and applies appropriate tests based on the field types and naming conventions.

Supported Configuration Keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The validation system recognizes the following configuration field patterns (case insensitive):

**Address Fields**
   - ``address``
   - ``ip``
   - ``server``
   - ``host``
   - ``hostname``

**Port Fields**
   - ``port``
   - ``brokerport``

**URL Fields**
   - ``url``

**Broker Fields**
   - ``broker``
   - ``brokerhost``

Configuration Value Priority
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When both ``default`` and ``value`` keys are present in a configuration field, the validation system uses the following priority:

1. **``value``** - Takes precedence when present
2. **``default``** - Used when ``value`` is not present
3. **Error** - Raised if neither ``value`` nor ``default`` is present

Common Configuration Patterns
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Host and Port Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Standard server configuration with separate host and port fields:

.. code-block:: json

   {
       "plugin": {
           "description": "Modbus TCP Plugin",
           "type": "string",
           "default": "modbus",
           "readonly": "true"
       },
       "address": {
           "description": "Address of Modbus TCP server",
           "type": "string",
           "default": "192.168.1.100",
           "order": "1",
           "displayName": "Server Address"
       },
       "port": {
           "description": "Port of Modbus TCP server",
           "type": "integer",
           "default": "502",
           "order": "2",
           "displayName": "Port"
       }
   }

**Validation Behavior:**
   - Tests host reachability to ``192.168.1.100``
   - Tests service listening on ``192.168.1.100:502``

Address-Only Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

Industrial protocol configuration with address field only:

.. code-block:: json

   {
       "plugin": {
           "description": "S7 PLC Plugin",
           "type": "string",
           "default": "s7",
           "readonly": "true"
       },
       "IP": {
           "description": "PLC IP Address",
           "type": "string",
           "default": "192.168.1.151",
           "order": "1",
           "displayName": "PLC IP Address"
       }
   }

**Validation Behavior:**
   - Tests host reachability to ``192.168.1.151``
   - Tests service listening on common industrial ports: ``102`` (S7), ``44818`` (EtherNet/IP), ``502`` (Modbus), ``80`` (HTTP), ``443`` (HTTPS)

IP Address Configuration
^^^^^^^^^^^^^^^^^^^^^^^^

Similar to address-only, but specifically for IP fields:

.. code-block:: json

   {
       "plugin": {
           "description": "EtherNet/IP Plugin",
           "type": "string",
           "default": "etherip",
           "readonly": "true"
       },
       "address": {
           "description": "Address of PLC",
           "type": "string",
           "default": "127.0.0.1",
           "value": "192.168.1.199",
           "order": "1",
           "displayName": "PLC IP Address"
       }
   }

**Validation Behavior:**
   - Uses ``value`` (``192.168.1.199``) over ``default``
   - Tests host reachability to ``192.168.1.199``
   - Tests service listening on default industrial ports

Broker Configuration
^^^^^^^^^^^^^^^^^^^^

MQTT broker configuration supports multiple patterns:

**Pattern 1: Broker URL**

.. code-block:: json

   {
       "plugin": {
           "description": "MQTT South Plugin",
           "type": "string",
           "default": "mqtt",
           "readonly": "true"
       },
       "broker": {
           "description": "MQTT Broker URL",
           "type": "string",
           "default": "tcp://mqtt.local:1883",
           "order": "1",
           "displayName": "MQTT Broker"
       }
   }

**Validation Behavior:**
   - Parses URL to extract host (``mqtt.local``) and port (``1883``)
   - Tests host reachability to ``mqtt.local``
   - Tests service listening on ``mqtt.local:1883``

**Pattern 2: Separate Host and Port**

.. code-block:: json

   {
       "brokerHost": {
           "description": "Hostname or IP address of the broker",
           "type": "string",
           "default": "localhost",
           "order": "1",
           "displayName": "MQTT Broker Host"
       },
       "brokerPort": {
           "description": "The network port of the broker",
           "type": "integer",
           "default": "1883",
           "order": "2",
           "displayName": "MQTT Broker Port"
       }
   }

**Validation Behavior:**
   - Tests host reachability to ``localhost``
   - Tests service listening on ``localhost:1883``

**Pattern 3: Broker Hostname Only**

.. code-block:: json

   {
       "broker": {
           "description": "The address of the MQTT broker",
           "type": "string",
           "default": "localhost",
           "order": "1",
           "displayName": "MQTT Broker"
       }
   }

**Validation Behavior:**
   - Tests host reachability to ``localhost``
   - Tests service listening on default MQTT ports: ``1883``, ``8883``

URL Configuration
^^^^^^^^^^^^^^^^^

Service URL configuration with protocol-specific handling:

.. code-block:: json

   {
       "plugin": {
           "description": "OPC UA South Plugin",
           "type": "string",
           "default": "opcua",
           "readonly": "true"
       },
       "url": {
           "description": "OPC UA Server URL",
           "type": "string",
           "default": "opc.tcp://localhost:4840/server",
           "order": "1",
           "displayName": "Server URL"
       }
   }

**Validation Behavior:**
   - Parses ``opc.tcp://`` URL format
   - Tests host reachability to ``localhost``
   - Tests service listening on ``localhost:4840``

**Supported URL Schemes:**
   - ``http://``, ``https://``
   - ``opc.tcp://`` (OPC UA)
   - ``tcp://`` (MQTT)
   - ``mqtt://``, ``mqtts://``
   - ``ftp://``

Server and Port Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generic server configuration pattern:

.. code-block:: json

   {
       "plugin": {
           "description": "Database North Plugin",
           "type": "string",
           "default": "database",
           "readonly": "true"
       },
       "ServerHostname": {
           "description": "Database server hostname",
           "type": "string",
           "default": "db.example.com",
           "order": "1",
           "displayName": "Server Hostname"
       },
       "ServerPort": {
           "description": "Database server port",
           "type": "integer",
           "default": "5432",
           "order": "2",
           "displayName": "Server Port"
       }
   }

**Validation Behavior:**
   - Tests host reachability to ``db.example.com``
   - Tests service listening on ``db.example.com:5432``

Default Port Assignment
~~~~~~~~~~~~~~~~~~~~~~~

When no explicit port is configured, the validation system applies default ports based on field names and common protocols:

**IP Fields** (``ip``, ``IP``)
   - ``102`` (S7 PLC)
   - ``44818`` (EtherNet/IP)
   - ``502`` (Modbus TCP)
   - ``80`` (HTTP)
   - ``443`` (HTTPS)

**Address Fields** (``address``)
   - ``502`` (Modbus TCP)
   - ``80`` (HTTP)
   - ``443`` (HTTPS)

**Host/Server Fields** (``host``, ``hostname``, ``server``)
   - ``80`` (HTTP)
   - ``443`` (HTTPS)

**Broker Fields** (``broker``, ``brokerhost``)
   - ``1883`` (MQTT)
   - ``8883`` (MQTTS)

Testing Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**API Endpoint:** ``PUT /fledge/plugin/validate``

**Request Body:** JSON configuration object

**Example Test Request:**

.. code-block:: bash

   curl -X PUT http://localhost:8081/fledge/plugin/validate \
        -H "Content-Type: application/json" \
        -d '{
            "plugin": {
                "description": "Test Plugin",
                "type": "string",
                "default": "test",
                "readonly": "true"
            },
            "address": {
                "description": "Server address",
                "type": "string",
                "default": "192.168.1.100"
            },
            "port": {
                "description": "Server port",
                "type": "integer",
                "default": "502"
            }
        }'

Validation Response Format
~~~~~~~~~~~~~~~~~~~~~~~~~~

The validation API returns a JSON response with test results:

**Success Response (HTTP 200):**

.. code-block:: json

   {
       "HostReachable": {
           "description": "Host Reachable",
           "result": "pass",
           "values": [
               {"address": "192.168.1.100", "port": "502"}
           ]
       },
       "Listening": {
           "description": "Listening",
           "result": "fail",
           "values": [
               {"address": "192.168.1.100", "port": "502"}
           ],
           "detail": {
               "reason": "No service is listening on 192.168.1.100:502"
           }
       }
   }

**No Validation Required (HTTP 204):**

Returned when no network-related configuration fields are detected.

**Error Response (HTTP 400):**

.. code-block:: json

   {
       "error": "Configuration item 'address' must have either 'value' or 'default' key"
   }

Configuration Testing Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**During Plugin Development**
   - Test configurations with the validation API before finalizing plugin design
   - Use realistic default values that can be validated
   - Ensure network-related fields follow recognized naming patterns

**Configuration Design**
   - Use consistent field naming conventions (``address``, ``port``, ``host``)
   - Provide meaningful default values for testing
   - Include both ``default`` and ``value`` support for flexibility

**Field Naming**
   - Use recognized field names for automatic detection
   - Follow consistent naming patterns across plugins
   - Consider using descriptive field names that match the validation patterns

**Error Handling**
   - Always provide either ``default`` or ``value`` keys for network-related fields
   - Use appropriate data types (``string`` for hostnames, ``integer`` for ports)
   - Provide clear descriptions for configuration fields

**Integration Testing**
   - Validate configurations during plugin development
   - Use validation results to verify network connectivity before deployment
   - Consider validation feedback when designing plugin configurations

Validation Limitations
~~~~~~~~~~~~~~~~~~~~~~

This is the first iteration of the plugin configuration validation feature. Current limitations include:

- Network connectivity testing only (no protocol-specific validation)
- Limited to common network configuration patterns
- No support for complex authentication scenarios
- Basic URL scheme support
- No certificate or encryption validation

Future enhancements may include additional validation types, protocol-specific testing, and expanded configuration pattern support.

