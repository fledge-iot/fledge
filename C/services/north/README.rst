.. |br| raw:: html

   <br />


*********************
Fledge North Service
*********************

This is the north service of the Fledge platform written in C.
This service is responsible for sending the readings data onwards to the
upstream systems. The service registers with the storage service to be
given any new data as it arrives.
|br| |br|


Building
========

The Storage service is built using cmake, to build the Storage service:
::
  mkdir build
  cd build
  cmake ..
  make

This will create the executable file ``north`` service.

Use the command ``make install`` to install in the default location,
note you will need permission on the installation directory or use
the sudo command. Pass the option *DESTDIR=* to set your own destination
into which to install the Storage service.

Build the plugins by going to the directory *C/plugins/north* and follow
the instructions in each of the plugin directories.
|br| |br|
  

Prerequisites
=============

To build the North service the machine must have installed the
*cmake* system, *make* and *g++*, plus the libraries for the North plugin,
e.g. the boost libraries


On Ubuntu based Linux distributions these can be installed with *apt-get*:
::
  apt-get install libboost-dev libboost-system-dev libboost-thread-dev
  apt-get install cmake g++ make

|br| |br|


Running
=======

The North service may be run in daemon mode or interactively by use
of the *-d* command line argument.

The North service will register with the core to allow the core to
monitor the North service and to allow the North storage to find the
Storage service.  It assumes the core is located on the same machine. This
can however be overridden by the use of the command line argument
*--port=* and *--address=* to set the port and address of the core
microservice.

The North service will look for North plugins in the current directory
or in the directory *$FLEDGE_ROOT/plugins/north*.
|br| |br|
