.. |br| raw:: html

   <br />


***************
Storage Plugins
***************

This directory contains the source code for the plugins used by the Storage service.

Building
========

To make this plugin, run the commands:
::
  mkdir build
  cd build
  cmake ..
  make

Use the command ``make install`` to install in the default location,
note you will need permission on the installation directory or use
the sudo command. Pass the option *DESTDIR=* to set your own destination
into which to install the Storage service.

