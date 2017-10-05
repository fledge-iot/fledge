
FogLAMP Storage Service
=======================

This is the storage service of the FogLAMP platform, it provides a storage layer with REST interface and a pluggable mechanism to attach to data storage systems, e.g. databases or document stores.

Building
--------

The storage service is built using cmake, to build the storage service

  ``mkdir build``
  
  ``cd build``
  
  ``cmake ..``
  
  ``make``

This will create the executable file ``storage`` and the storage plugins, currently only ``libpostgres.so``.

Prerequisites
-------------

To biuld the storage service the machine must have installed the cmake system, make and g++, plus the libraries fo rthe storage plugin, e.g. Postgres and the boost libraries


To run the storage service the system requires a number of libraries be installed; boost system and the Postgres libpg libraries

On Ubuntu based Linux distrobutions thse can be installed with apt-get

  ``apt-get install libboost-dev libboost-system-dev libboost-thread-dev libpq-dev``
  
  ``apt-get install cmake g++ make``

Running
-------

The storage service may be run in daemon mode or interactively by use of the -d command line argument.

The storage service will register with the core to allow other services and the core to find the API of the storage service. It asusmes the core is located on the same machine as it and is listening on port 8082. This can however be overwritten by the use of the command line argument --port= and --address= to set the port and address of the core microservice.

The storage layer will look for storage plugins in the current directory or in the directory $FOGLAMP_HOME/plugins

Ports
-----

The storage system listens for REST requests on two separate ports, the service ports for storage based requests and the management port for management requests. These may either be set to specific ports in the configuration file or dynamic ports can be allocated at runtime. In this later mode of operation the clients of the storage layer must determien these ports by connecting to the core and requesting for the storage layer registration information.
