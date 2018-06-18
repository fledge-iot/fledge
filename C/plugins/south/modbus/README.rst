*******************
Modbus South Plugin
*******************

A simple polling modbus south plugin that supports modbus-tcp and modbus-rtu.

This requires the Linux libmodbus library, this can be installed by running
::
  apt-get install libmodbus-dev

Building
========

To make modbus plugin run the commands:
::
  mkdir build
  cd build
  cmake ..
  make

