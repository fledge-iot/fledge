.. |br| raw:: html

   <br />


*********************
FogLAMP South Service
*********************

This is the south service of the FogLAMP platform written in C.
This service is responsible for gathering readings and sending
then to the FogLAMP buffer for storage.
|br| |br|


Building
========

The Storage service is built using cmake, to build the Storage service:
::
  mkdir build
  cd build
  cmake ..
  make

This will create the executable file ``south`` service.

Use the command ``make install`` to install in the default location,
note you will need permission on the installation directory or use
the sudo command. Pass the option *DESTDIR=* to set your own destination
into which to install the Storage service.

Build the plugins by going to the directory *C/plugins/south* and follow
the instructions in each of the plugin directories.
|br| |br|
  

Prerequisites
=============

To build the South service the machine must have installed the
*cmake* system, *make* and *g++*, plus the libraries for the South plugin,
e.g. the boost libraries


On Ubuntu based Linux distributions these can be installed with *apt-get*:
::
  apt-get install libboost-dev libboost-system-dev libboost-thread-dev
  apt-get install cmake g++ make

|br| |br|


Running
=======

The South service may be run in daemon mode or interactively by use
of the *-d* command line argument.

The South service will register with the core to allow the core to
monitor the South service and to allow the South storage to find the
Storage service.  It assumes the core is located on the same machine. This
can however be overridden by the use of the command line argument
*--port=* and *--address=* to set the port and address of the core
microservice.

The South service will look for South plugins in the current directory
or in the directory *$FOGLAMP_ROOT/plugins/south*.
|br| |br|
