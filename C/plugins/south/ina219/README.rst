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

Readings
========

The asset coe is controlled via a configuration options, the asset will
return three data points per readings
::
  voltage - The voltage across the load (V)
  current - The current the load is taking (mA)
  power - The power the load is consuming (mW)
