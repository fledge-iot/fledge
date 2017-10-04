
FogLAMP Storage Service
=======================

This is the storage service of the FogLAMP platform, it provides a storage layer with REST interface and a pluggable mechanism to attach to data storage systems, e.g. databases or document stores.

Building
--------

The storage service is built usign cmake, to build the storage service

  ``mkdir build``
  ``cd build``
  ``cmake ..``
  ''make''

This will create the executable file ``storage`` and the storage plugins, currently only ``libpostgres.so``.

Prerequisites
-------------

To biuld the storage service the machine must have installed the cmake system, make and g++, plus the libraries fo rthe storage plugin, e.g. Postgres and the bosot libraries


To run thr boost system, libraries are required and the Postgres libpg libraries

On Ubuntu based Linux distrobutions thse can be installed with apt-get

  ``apt-get install libboost-dev libboost-system-dev libboost-thread-dev libpq-dev``
  ``apt-get install cmake g++ make``
