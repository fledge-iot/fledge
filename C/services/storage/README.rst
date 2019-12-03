.. |br| raw:: html

   <br />


***********************
Fledge Storage Service
***********************

This is the Storage service of the Fledge platform, it provides a
storage layer with REST interface and a pluggable mechanism to attach
to data storage systems, e.g. databases or document stores.
|br| |br|


Building
========

The Storage service is built using cmake, to build the Storage service:
::
  mkdir build
  cd build
  cmake ..
  make

This will create the executable file ``storage`` service.

Use the command ``make install`` to install in the default location,
note you will need permission on the installation directory or use
the sudo command. Pass the option *DESTDIR=* to set your own destination
into which to install the Storage service.

Build the plugins by going to the directory *C/plugins/storage* and follow
the instructions in each of the plugin directories.
|br| |br|
  

Prerequisites
=============

To build the Storage service the machine must have installed the
*cmake* system, *make* and *g++*, plus the libraries for the Storage plugin,
e.g. Postgres and the boost libraries

To run the Storage service the system requires a number of libraries be
installed; boost system and the Postgres libpg libraries

On Ubuntu based Linux distributions these can be installed with *apt-get*:
::
  apt-get install libboost-dev libboost-system-dev libboost-thread-dev libpq-dev
  apt-get install cmake g++ make

|br| |br|


Running
=======

The Storage service may be run in daemon mode or interactively by use
of the *-d* command line argument.

The Storage service will register with the core to allow other services
and the core to find the API of the Storage service. It assumes the core
is located on the same machine. This can however be overridden by the use of
the command line argument *--port=* and *--address=* to set the port and
address of the core microservice.

The Storage layer will look for Storage plugins in the current directory
or in the directory *$FLEDGE_ROOT/plugins/storage*.
|br| |br|


Ports
=====

The Storage system listens for REST requests on two separate ports, the
service port for storage based requests and the management port for
management requests. These may either be set to specific ports in the
configuration file or dynamic ports can be allocated at runtime. In this
later mode of operation the clients of the Storage layer must determine
these ports by connecting to the core and requesting for the Storage
layer registration information.

To run the Storage service with fixed ports modify the configuration
cache file, *storage.json* in *$FLEDGE_DATA/etc* to pass explicit ports
rather than 0. Note that if not set, *$FLEDGE_DATA* has the same value of
*$FLEDGE_ROOT*. 

config.json file
----------------

This is an example of a *config.json* file:
::
  { "plugin"        : { "value":"postgres" },
      "threads"       : { "value":"1" },
      "port"          : { "value":"8082" },
      "managementPort": { "value":"1082" }
  }

|br| |br|


Testing
=======

A test suite is available in the development directory *tests/unit_tests/services/storage*.

