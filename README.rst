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

- a **Core service** responsible for the management of the other services, the external REST API's, scheduling and monitoring of activities.
- a **South service** responsible for the communication between FogLAMP and the sensors/actuators.
- a **Storage service** responsible for the persistance of configuration and metrics and the buffering of sensor data.

FogLAMP makes extensive use of plugin components in order to increase the flexibility of the implementation:

- **South plugins** are used to allow for the easy expansion of FogLAMP to deal with new South devices and South device connection buses.
- **North plugins** are used to allow for connection to different historians
- **Datastore plugins** are used to allow FogLAMP to use different storage mechanisms for persisting meta data and the sensor data
- **Authentication provider plugins** are used to allow the authentication mechanism to be matched with enterprise requirements or provided internally by FogLAMP.

The other paradigm that is used extensively within FogLAMP is the idea of **scheduling processes** to perform specific operations. The FogLAMP core contains a scheduler which can execute processes based on time schedules or triggered by events. This is used to start processes when an event occurs, such as FogLAMP starting, or based on a time trigger.

Scheduled processes are used to send data from FogLAMP to the historian, to purge data from the FogLAMP data buffer, to gather statistics for historical analysis and perform backups of the FogLAMP environment.
|br| |br|

Building FogLAMP
================

Build Prerequisites
-------------------

FogLAMP is currently based on C/C++ and Python code. The packages needed to build and run FogLAMP are:

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

FogLAMP can be built or installed in one of the following Linux distributions :

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

To build FogLAMP run the command ``make`` in the top level directory. This will compile all the components that need to be compiled and will also create a runable structure of the Python code components of FogLAMP.

**NOTE:**

- *The GCC compiler version 5.4 available in Ubuntu 16.04 LTS raises warnings. This is a known bug of the compiler and it can be ignored.*

- *openssl toolkit is a requirement if we want to use https based REST client and certificate based authentication.*

Once the *make* has completed you can decide to test FogLAMP from your development environment or you can install it. 
|br| |br|


Testing FogLAMP from Your Development Environment
=================================================

you can test FogLAMP directly from your Development Environment. All you need to do is to set one environment variable to be able to run FogLAMP from the development tree.
::
   export FOGLAMP_ROOT=<basedir>/FogLAMP

Where *basedir* is the base directory into which you cloned the FogLAMP repository.

Finally, start the FogLAMP core daemon:
::
   $FOGLAMP_ROOT/scripts/foglamp start

|br|

Installing FogLAMP
==================

Create an installation by executing ``make install``, then set the *FOGLAMP_ROOT* environment variable specifying the installation path. By default the installation will be placed in */usr/local/foglamp*. You may need to execute ``sudo make install`` to install FogLAMP where the current user does not have permissions:
::
   sudo make install
   export FOGLAMP_ROOT=/usr/local/foglamp

The destination may be overriden by setting the variable *DESTDIR* in the make command line, to a location in which you wish to install FogLAMP. For example, to install FogLAMP in the */opt* directory use the command:
::
   sudo make install DESTDIR=/opt
   export FOGLAMP_ROOT=/opt/usr/local/foglamp

|br|

Upgrading FogLAMP on Debian based systems
=========================================

FogLAMP supports the Kerberos authentication starting from the version 1.7.1 and so the related packages are installed by the script `requirements.sh <requirements.sh>`_.
The *krb5-user* package prompt a question during the installation process asking for the KDC definition, the packages are installed setting the environment *DEBIAN_FRONTEND*
to avoid this interaction:
::

	# for Kerberos authentication, avoid interactive questions
	DEBIAN_FRONTEND=noninteractive apt install -yq krb5-user
	apt install -y libcurl4-openssl-dev

The upgrade of the FogLAMP package should follow the same philosophy, it should be done executing the command:
::
    sudo DEBIAN_FRONTEND=noninteractive apt -y upgrade

before the upgrade of FogLAMP, *SETENV:* should be set/added in */etc/sudoers.d/foglamp* to allow *sudo* to support the handling of the environment variables, a sample of the file:
::

    %sudo ALL=(ALL) NOPASSWD:SETENV: /usr/bin/apt -y update, /usr/bin/apt-get -y install foglamp, /usr/bin/apt -y install /usr/local/foglamp/data/plugins/foglamp*.deb, /usr/bin/apt list, /usr/bin/apt -y install foglamp*, /usr/bin/apt -y upgrade

|br|

Executing FogLAMP
=================

FogLAMP is now ready to start. Use the command:
::
   $FOGLAMP_ROOT/bin/foglamp start

To check if FogLAMP is running, use the command:
::
   $FOGLAMP_ROOT/bin/foglamp status

The command returns the status of FogLAMP on the machine it has been executed.


If You Use PostgreSQL: Creating the Database Repository
=======================================================

This version of FogLAMP relies on SQLite to run. SQLite is embedded into the Storage service, but you may want to use PostgreSQL as a buffer and metadata storage (refer to the documentation on `ReadTheDocs <http://foglamp.readthedocs.io>`_ for more info. With a version of PostgreSQL installed via *apt-get* first you need to create a new database user with:
::
   sudo -u postgres createuser -d <user>

where *user* is the name of the Linux user that will run FogLAMP. The FogLAMP database user must have *createdb* privileges (i.e. the *-d* argument).
|br| |br|

