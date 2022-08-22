.. |br| raw:: html

   <br />
   
.. Links
.. |pluginlist| raw:: html

   <a href="https://fledge-iot.readthedocs.io/en/develop/fledge_plugins.html">Fledge Plugins</a>
   
   
.. |quickstart| raw:: html

   <a href="https://fledge-iot.readthedocs.io/en/develop/quick_start/installing.html">Installing Fledge</a>

.. |building| raw:: html

   <a href="https://fledge-iot.readthedocs.io/en/develop/building_fledge/building_fledge.html#building-fledge">Building Fledge</a>

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
- a **Storage service** responsible for the persistence of configuration and metrics and the buffering of sensor data.

This core set of services may also be extended using optional services that are available within their own repositories, for example a notification service and a control dispatcher service.

Fledge makes extensive use of plugin components in order to increase the flexibility of the implementation:

- **South plugins** are used to allow for the easy expansion of Fledge to deal with new South devices and South device connection buses.
- **North plugins** are used to allow for connection to different historians
- **Datastore plugins** are used to allow Fledge to use different storage mechanisms for persisting meta data and the sensor data

The South and North plugins are stored in separate source code repositories which are named in the pattern fledge-south-<device> fledge-north-<service>. A complete list of plugins can be found in the readthedocs documentation for the project. See |pluginlist|.

The optional services, for example the notification service also make use of plugins to extend the capabilities of those services.

The other paradigm that is used extensively within Fledge is the idea of **scheduling processes** to perform specific operations. The Fledge core contains a scheduler which can execute processes based on time schedules or triggered by events. This is used to start processes when an event occurs, such as Fledge starting, or based on a time trigger.

Scheduled processes are used to send data from Fledge to the historian, to purge data from the Fledge data buffer, to gather statistics for historical analysis and perform backups of the Fledge environment.
|br| |br|

Pre-built packages for Fledge are available, see |quickstart| for details of how to use these.

Building Fledge
================

See also |building| in the online documentation.

Build Prerequisites
-------------------

Fledge is currently based on C/C++ and Python code. The packages needed to build and run Fledge may be installed by running the script *requirements.sh*


Linux distributions
-------------------

Fledge can be built or installed in one of the following Linux distributions :

- Ubuntu Ubuntu 18.04 and Ubuntu 20.04
- Raspbian Stretch, Buster and Bullseye
- Coral Mendel

Install the prerequisites
-------------------------

The prerequisites required to build Fledge can be installed on any of the supported platforms by running the requirements.sh script from this directory.

.. code-block:: console

	sudo ./requirements.sh

.. note::

   This script will use the platforms package management software, such as apt on Ubuntu systems, to install the required packages. This must be done as the root user and hence the need to run requirements.sh using the sudo command
 
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

Upgrading Fledge on Debian based systems
========================================

Fledge supports the Kerberos authentication starting from the version 1.7.1 and so the related packages are installed by the script `requirements.sh <requirements.sh>`_.
The *krb5-user* package prompt a question during the installation process asking for the KDC definition, the packages are installed setting the environment *DEBIAN_FRONTEND*
to avoid this interaction:
::

	# for Kerberos authentication, avoid interactive questions
	DEBIAN_FRONTEND=noninteractive apt install -yq krb5-user
	apt install -y libcurl4-openssl-dev

The upgrade of the Fledge package should follow the same philosophy, it should be done executing the command:
::
    sudo DEBIAN_FRONTEND=noninteractive apt -y upgrade

before the upgrade of Fledge, *SETENV:* should be set/added in */etc/sudoers.d/fledge* to allow *sudo* to support the handling of the environment variables, a sample of the file:
::

    %sudo ALL=(ALL) NOPASSWD:SETENV: /usr/bin/apt -y update, /usr/bin/apt-get -y install fledge, /usr/bin/apt -y install /usr/local/fledge/data/plugins/fledge*.deb, /usr/bin/apt list, /usr/bin/apt -y install fledge*, /usr/bin/apt -y upgrade

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

This version of Fledge relies on SQLite to run. SQLite is embedded into the Storage service, but you may want to use PostgreSQL as a buffer and metadata storage (refer to the documentation on `ReadTheDocs <https://fledge-iot.readthedocs.io/en/develop/building_fledge/building_fledge.html?highlight=appendix#appendix-setting-the-postgresql-database>`_ for more info. With a version of PostgreSQL installed via *apt-get* first you need to create a new database user with:
::
   sudo -u postgres createuser -d <user>

where *user* is the name of the Linux user that will run Fledge. The Fledge database user must have *createdb* privileges (i.e. the *-d* argument).
|br| |br|


Troubleshooting
===============

Fledge version 1.7.0
--------------------

$FLEDGE_ROOT/data/etc directory ownership
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The execution of the *sudo make install* immediately after *git clone* will create a *data/etc* directory owned by the *root* user,
it should be owned by the user that will run Fledge, to fix it:
::
    chown -R <user>:<user> $FLEDGE_ROOT/data

where *user* is the name of the Linux user that will run Fledge.
|br| |br|
