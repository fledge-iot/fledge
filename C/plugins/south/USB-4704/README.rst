********************
USB4704 South Plugin
********************

A generic plugin for sensors connected to the Advantech USB-4704
Portable Data Acquisition Module.


Building
========

This plugin requries the Advantech BIODAQ library. This has not standard install
location, therefore you must se the environment variable BIODAQDIR to the location
in whch you installed this.

To make usb4704 plugin run the commands:
::
  export BIODAQDIR=...
  mkdir build
  cd build
  cmake ..
  make

