*******************
INA219 South Plugin
*******************

A simple polling plugin for the INA219 voltage/current sensor

This requires the Raspberry Pi WiringPi library
::
  apt-get install libmodbus-dev

Building
========

To make ina219 plugin run the commands:
::
  mkdir build
  cd build
  cmake ..
  make

