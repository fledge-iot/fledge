.. |br| raw:: html

   <br />


*******
FogLAMP
*******

This is the FogLAMP project.

FogLAMP is an open source platform for the **Internet of Things**, and an essential component in **Fog Computing**. It uses a modular **microservices architecture** including sensor data collection, storage, processing and forwarding to historians, Enterprise systems and Cloud-based services. FogLAMP can run in highly available, stand alone, unattended environments that assume unreliable network connectivity.

FogLAMP also provides a means of buffering data coming from sensors and forwarding that data onto high level storage systems. It assumes the underlying network layer is not always connected or may not be reliable. Data from sensors may be stored within FogLAMP for a number of days before being purged from the FogLAMP storage. During this time it may be sent to one or more historians and also accessed via a REST API for use by *local* analytical applications.

FogLAMP has been designed to run in a Linux environment and makes use of Linux services.
|br| |br|

Architecture
============

FogLAMP is built using a microservices architecture for major component areas, these services consist of:

- a **core service** responsible for the management of the other services, the external REST API's, scheduling and monitoring of activities.
- a **South service** responsible for the communication between FogLAMP and the sensors/actuators.
- a **Storage service** responsible for the persistance of configuration and metrics and the buffering of sensor data.

FogLAMP makes extensive use of plugin components in order to increase the flexibility of the implementation:

- **South plugins** are used to allow for the easy expansion of FogLAMP to deal with new devices and device connection buses.
- **translator plugins** are used to allow for connection to different historians
- **datastore plugins** are used to allow FogLAMP to use different storage mechanisms for persisting meta data and the sensor data
- **authentication provider plugins** are used to allow the authentication mechanism to be matched with enterprise requirements or provided internally by FogLAMP.

The other paradigm that is used extensively within FogLAMP is the idea of **scheduling processes** to perform specific operations. The FogLAMP core contains a scheduler which can execute processes based on time schedules or triggered by events. This is used to start processes when an event occurs, such as FogLAMP starting, or based on a time trigger.

Scheduled processes are used to send data from FogLAMP to the historian, to purge data from the FogLAMP data buffer, to gather statistics for historical analysis and perform backups of the FogLAMP environment.
|br| |br|

Building FogLAMP
================

Build Prerequisites
-------------------

FogLAMP is currently based on C/C++ and Python code. The packages needed to build and run FogLAMP are:

- *cmake*, *g++*, *make*
- *libboost-dev*, *libboost-system-dev*, *libboost-thread-dev*, *libpq-dev*
- *python3-pip*
- *postgresql*

On Ubuntu based Linux distributions these can be installed with *apt-get*:
::
   apt-get install cmake g++ make
   apt-get install libboost-dev libboost-system-dev libboost-thread-dev libpq-dev
   apt-get install python3-pip
   apt-get install postgresql

You may need to use *sudo* to allow *apt-get* to install packages dependent upon our access rights.


Build
-----

To build FogLAMP simply run the command ``make`` in the top level directory. This will compile all the components that need to be compiled and will also create a runable structure of the Python code components of FogLAMP.

Once the *make* has completed set one environment variable to be able to run FogLAMP from the development tree.
::
   export FOGLAMP_ROOT=<basedir>/FogLAMP

Where *basedir* is the base directory into which you cloned the FogLAMP repository.
|br| |br|

Installing FogLAMP
==================

Create an installation by executing ``make install``. The installation will be placed in */usr/local/foglamp*, this may be overriden by setting the variable DESTDIR to a location in which you wish to install FogLAMP. You may need to execute ``sudo make install`` to install FogLAMP where the current user does not have permissions.


Creating the Database Repository
--------------------------------

This version of FogLAMP relies on PostgreSQL to run. With a version of PostgreSQL installed via *apt-get* first you need to create a new database user with:
::
   sudo -u postgres createuser <user>

where *user* is the name of the Linux user that will run FogLAMP.

Last, you must create the FogLAMP database, schema and tables:
::
   sudo -u postgres psql -f <FOGLAMP_ROOT>/plugins/storage/postgres/init.sql

Replace *FOGLAMP\_ROOT* with the path you have used to install FogLAMP.
|br| |br|

Executing FogLAMP
=================

FogLAMP is now ready to start. Use the command:
::
   <FOGLAMP_ROOT>/bin/foglamp start

To check if FogLAMP is running, simply use *curl* (you may need to install it first):
::
   curl http://localhost:8081/foglamp/ping

The command should return a JSON text with the total uptime in seconds.

