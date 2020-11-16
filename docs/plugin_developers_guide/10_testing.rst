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

A Python filter plugin call normalise, on a system installed from
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
         "name": "pi_server",
         "type": "north",
         "description": "PI Server North Plugin",
         "version": "1.0.0",
         "installedDirectory": "north/pi_server",
         "packageName": "fledge-north-pi-server"
       },
       {
         "name": "ocs",
         "type": "north",
         "description": "OCS (OSIsoft Cloud Services) North Plugin",
         "version": "1.0.0",
         "installedDirectory": "north/ocs",
         "packageName": "fledge-north-ocs"
       },
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

The utility is passed the library file of your plugin as its first argument
and the function to call, usually *plugin_info*.

.. code-block:: console

   $ get_plugin_info plugins/north/GCP/libGCP.so  plugin_info
   {"name": "GCP", "version": "1.8.1", "type": "north", "interface": "1.0.0", "flag": 0, "config": { "plugin" : { "description" : "Google Cloud Platform IoT-Core", "type" : "string", "default" : "GCP", "readonly" : "true" }, "project_id" : { "description" : "The GCP IoT Core Project ID", "type" : "string", "default" : "", "order" : "1", "displayName" : "Project ID" }, "region" : { "description" : "The GCP Region", "type" : "enumeration", "options" : [ "us-central1", "europe-west1", "asia-east1" ], "default" : "us-central1", "order" : "2", "displayName" : "The GCP Region" }, "registry_id" : { "description" : "The Registry ID of the GCP Project", "type" : "string", "default" : "", "order" : "3", "displayName" : "Registry ID" }, "device_id" : { "description" : "Device ID within GCP IoT Core", "type" : "string", "default" : "", "order" : "4", "displayName" : "Device ID" }, "key" : { "description" : "Name of the key file to use", "type" : "string", "default" : "", "order" : "5", "displayName" : "Key Name" }, "algorithm" : { "description" : "JWT algorithm", "type" : "enumeration", "options" : [ "ES256", "RS256" ], "default" : "RS256", "order" : "6", "displayName" : "JWT Algorithm" }, "source": { "description" : "The source of data to send", "type" : "enumeration", "default" : "readings", "order" : "8", "displayName" : "Data Source", "options" : ["readings", "statistics"] } }}

If there is an undefined symbol you will get an error from this
utility. You can also check the validity of your JSON configuration by
piping the output to a program such as jq.

Running Under a Debugger
------------------------

If you have a C/C++ plugin that crashes you may want to run the plugin under a debugger. To build with debug symbols use the CMake option *-DBUILD_TYPE=Debug* when you create the *Makefile*.

.. code-block:: console

   $ cmake -DBUILD_TYPE=Debug ..


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

   - Load the service you wish to use to run your plugin, e..g a south service, under the debugger

     .. code-block:: console

        $ gdb services/fledge.services.south

   - Run the service passing the *--port=* and *--address=* arguments you noted above and add *-d* and *--name=* with the name of your service.

     .. code-block:: console

        (gdb) run --port=39821 --address=127.0.0.1 --name=DebugPlugin -d

   - You can now use the debugger in the way you normally would to find any issues.
