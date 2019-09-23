.. |br| raw:: html

   <br />


*******
Fledge
*******

This is the Fledge project.

Fledge is an open source platform for the **Internet of Things**, and an essential component in **Fog Computing**. It uses a modular **microservices architecture** including sensor data collection, storage, processing and forwarding to historians, Enterprise systems and Cloud-based services. Fledge can run in highly available, stand alone, unattended environments that assume unreliable network connectivity.

Fledge also provides a means of buffering data coming from sensors and forwarding that data onto high level storage systems. It assumes the underlying network layer is not always connected or may not be reliable. Data from sensors may be stored within Fledge for a number of days before being purged from the Fledge storage. During this time it may be sent to one or more historians and also accessed via a REST API for use by *local* analytical applications.

Fledge has been designed to run in a Linux environment and makes use of Linux services.
|br| |br|

Architecture
============

Fledge is built using a microservices architecture for major component areas, these services consist of:

- a **Core service** responsible for the management of the other services, the external REST API's, scheduling and monitoring of activities.
- a **South service** responsible for the communication between Fledge and the sensors/actuators.
- a **Storage service** responsible for the persistance of configuration and metrics and the buffering of sensor data.

Fledge makes extensive use of plugin components in order to increase the flexibility of the implementation:

- **South plugins** are used to allow for the easy expansion of Fledge to deal with new South devices and South device connection buses.
- **North plugins** are used to allow for connection to different historians
- **Datastore plugins** are used to allow Fledge to use different storage mechanisms for persisting meta data and the sensor data
- **Authentication provider plugins** are used to allow the authentication mechanism to be matched with enterprise requirements or provided internally by Fledge.

The other paradigm that is used extensively within Fledge is the idea of **scheduling processes** to perform specific operations. The Fledge core contains a scheduler which can execute processes based on time schedules or triggered by events. This is used to start processes when an event occurs, such as Fledge starting, or based on a time trigger.

Scheduled processes are used to send data from Fledge to the historian, to purge data from the Fledge data buffer, to gather statistics for historical analysis and perform backups of the Fledge environment.
|br| |br|

Building Fledge
================

Build Prerequisites
-------------------

Fledge is currently based on C/C++ and Python code. The packages needed to build and run Fledge are:

- autoconf 
- automake 
- avahi-daemon
- build-essential
- cmake
- curl
- g++
- libtool 
- libboost-dev
- libboost-system-dev
- libboost-thread-dev
- libpq-dev
- libssl-dev
- libz-dev
- make
- postgresql
- python3-pip
- python-dev
- python3-dev
- uuid-dev
- sqlite3
- libsqlite3-dev


Linux distributions
-------------------

Fledge can be built or installed in one of the following Linux distributions :

- Ubuntu 16.04 and Ubuntu 18.04
- Raspbian Stretch and Buster
- Red Hat 7.6
- CentOS 7.6
- Coral Mendel

Install the prerequisites on Ubuntu
-----------------------------------

On Ubuntu-based Linux distributions the packages can be installed with given `requirements.sh <requirements.sh>`_ or manual *apt-get*:
::
   apt-get install avahi-daemon curl
   apt-get install cmake g++ make build-essential autoconf automake uuid-dev
   apt-get install libtool libboost-dev libboost-system-dev libboost-thread-dev libpq-dev libssl-dev libz-dev
   apt-get install python-dev python3-dev python3-pip
   apt-get install postgresql
   apt-get install sqlite3 libsqlite3-dev

You may need to use *sudo* to allow *apt-get* to install packages dependent upon your access rights.

Install the prerequisites on Red Hat/CentOS
-------------------------------------------

On Red Hat and CentOS distributions the required packages can be installed automatically with given `requirements.sh <requirements.sh>`_:
::
	sudo ./requirements.sh

You should run this as a user with *sudo* access rights.


Build
-----

To build Fledge run the command ``make`` in the top level directory. This will compile all the components that need to be compiled and will also create a runable structure of the Python code components of Fledge.

**NOTE:**

- *The GCC compiler version 5.4 available in Ubuntu 16.04 LTS raises warnings. This is a known bug of the compiler and it can be ignored.*

- *openssl toolkit is a requirement if we want to use https based REST client and certificate based authentication.*

Once the *make* has completed you can decide to test Fledge from your development environment or you can install it. 
|br| |br|


Testing Fledge from Your Development Environment
=================================================

you can test Fledge directly from your Development Environment. All you need to do is to set one environment variable to be able to run Fledge from the development tree.
::
   export FLEDGE_ROOT=<basedir>/Fledge

Where *basedir* is the base directory into which you cloned the Fledge repository.

Finally, start the Fledge core daemon:
::
   $FLEDGE_ROOT/scripts/fledge start

|br|

Installing Fledge
==================

Create an installation by executing ``make install``, then set the *FLEDGE_ROOT* environment variable specifying the installation path. By default the installation will be placed in */usr/local/fledge*. You may need to execute ``sudo make install`` to install Fledge where the current user does not have permissions:
::
   sudo make install
   export FLEDGE_ROOT=/usr/local/fledge

The destination may be overriden by setting the variable *DESTDIR* in the make command line, to a location in which you wish to install Fledge. For example, to install Fledge in the */opt* directory use the command:
::
   sudo make install DESTDIR=/opt
   export FLEDGE_ROOT=/opt/usr/local/fledge

|br|



Executing Fledge
=================

Fledge is now ready to start. Use the command:
::
   $FLEDGE_ROOT/bin/fledge start

To check if Fledge is running, use the command:
::
   $FLEDGE_ROOT/bin/fledge status

The command returns the status of Fledge on the machine it has been executed.


If You Use PostgreSQL: Creating the Database Repository
=======================================================

This version of Fledge relies on SQLite to run. SQLite is embedded into the Storage service, but you may want to use PostgreSQL as a buffer and metadata storage (refer to the documentation on `ReadTheDocs <http://fledge.readthedocs.io>`_ for more info. With a version of PostgreSQL installed via *apt-get* first you need to create a new database user with:
::
   sudo -u postgres createuser -d <user>

where *user* is the name of the Linux user that will run Fledge. The Fledge database user must have *createdb* privileges (i.e. the *-d* argument).
|br| |br|

