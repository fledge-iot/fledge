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
         "version": "1.8.1",
         "installedDirectory": "north/http_north",
         "packageName": "fledge-north-http-north"
       },
       {
         "name": "GCP",
         "type": "north",
         "description": "Google Cloud Platform IoT-Core",
         "version": "1.8.1",
         "installedDirectory": "north/GCP",
         "packageName": "fledge-north-gcp"
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

   $ get_plugin_info plugins/north/GCP/libGCP.so  plugin_info
   {"name": "GCP", "version": "1.8.1", "type": "north", "interface": "1.0.0", "flag": 0, "config": { "plugin" : { "description" : "Google Cloud Platform IoT-Core", "type" : "string", "default" : "GCP", "readonly" : "true" }, "project_id" : { "description" : "The GCP IoT Core Project ID", "type" : "string", "default" : "", "order" : "1", "displayName" : "Project ID" }, "region" : { "description" : "The GCP Region", "type" : "enumeration", "options" : [ "us-central1", "europe-west1", "asia-east1" ], "default" : "us-central1", "order" : "2", "displayName" : "The GCP Region" }, "registry_id" : { "description" : "The Registry ID of the GCP Project", "type" : "string", "default" : "", "order" : "3", "displayName" : "Registry ID" }, "device_id" : { "description" : "Device ID within GCP IoT Core", "type" : "string", "default" : "", "order" : "4", "displayName" : "Device ID" }, "key" : { "description" : "Name of the key file to use", "type" : "string", "default" : "", "order" : "5", "displayName" : "Key Name" }, "algorithm" : { "description" : "JWT algorithm", "type" : "enumeration", "options" : [ "ES256", "RS256" ], "default" : "RS256", "order" : "6", "displayName" : "JWT Algorithm" }, "source": { "description" : "The source of data to send", "type" : "enumeration", "default" : "readings", "order" : "8", "displayName" : "Data Source", "options" : ["readings", "statistics"] } }}

If there is an undefined symbol you will get an error from this
utility. You can also check the validity of your JSON configuration by
piping the output to a program such as jq.

.. code-block:: console

   $ get_plugin_info plugins/south/Random/libRandom.so plugin_info | jq
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

The same approach can be used to make use of the *valgrind* command to find memory corruption and leak issues in your plugin

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

   - Run *valgrind* with the service adding the same set of arguments you used in gdb when running the service.

     Add any arguments you wish to pass to *valgrind* itself before the service executable name, in this case we are passing *--leak-check=full*.

     .. code-block:: console

        $ valgrind --leak-check=full  services/fledge.services.south --port=39821 --address=127.0.0.1 --name=ServiceName --token=StartupToken -d

     Where *ServiceName* is the name you gave your service and startupToken is a one time use token obtained following the steps shown above.

  - Once the service has run for a while shut it down to trigger *valgrind* to print a summary of memory leaks found during the execution.


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

