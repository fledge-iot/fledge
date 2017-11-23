Storage Plugins
===============

This directory contains the source code for the plugins used by the storage service

Building
--------

To make this plugin outside the general build, run the commands:

  ``mkdir build``

  ``cd build``

  ``cmake ..``

  ``make``

Use the command:

  ``make install``

to install in the default location, note you will need permission on the
installation directory or use the sudo command. Pass the option DESTDIR=
to set your own destination into which to install the storage service.

