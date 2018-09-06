*******************
OPC UA South Plugin
*******************

A simple asynchronous OPC UA plugin that registers for change events on OPC UA objects

Thia plugin assumes the freeopcua is available at a fixed location in the file system. To build you
must clone the freeopcua repository in your home directory.
::
  git clone https://github.com/FreeOpcUa/freeopcua.git

Building
========

To make opcua plugin run the commands:
::
  mkdir build
  cd build
  cmake ..
  make

