.. Version History presents a list of versions of FogLAMP released.

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. |1.1 requirements| raw:: html

   <a href="https://github.com/foglamp/FogLAMP/blob/1.1/python/requirements.txt" target="_blank">check here</a>


.. =============================================


***************
Version History
***************

FogLAMP v1
==========


v1.0
----

Release Date: 2017-12-11


Features
~~~~~~~~

- All the essential microservices are now in place: *Core, Storage, South, North*.
- Storage plugins available in the main repository:

  - **Postgres**: The storage layer relies on PostgreSQL for data and metadata

- South plugins available in the main repository:

  - **CoAP Listener**: A CoAP microservice plugin listening to client applications that send data to FogLAMP

- North plugins available in the main repository:

  - **OMF Translator**: A task plugin sending data to OSIsoft PI Connector Relay 1.0


.. _1.0-known_issues:

Known Issues
~~~~~~~~~~~~

- **Startup Script**: ``foglamp start`` does not check if the Core microservice has started correctly, hence it may report that "FogLAMP started." when the process has died. As a workaround, check with ``foglamp status`` the presence of the FogLAMP microservices.
- **Snap Execution on Raspbian**: there is an issue on Raspbian when the FogLAMP snap package is used. It is an issue with the snap environment, it looks for a shared object to preload on Raspian, but the object is not available. As a workaround, a superuser should comment a line in the file */etc/ld.so.preload*. Add a ``#`` at the beginning of this line: ``/usr/lib/arm-linux-gnueabihf/libarmmem.so``. Save the file and you will be able to immediately use the snap.
- **OMF Translator North Plugin for FogLAMP Statistics**: in this version the statistics collected by FogLAMP are not sent automatically to the PI System via the OMF Translator plugin, as it is supposed to be. The issue will be fixed in a future release.
- **Snap installed in an environment with an existing version of PostgreSQL**: the FogLAMP snap does not check if another version of PostgreSQL is available on the machine. The result may be a conflict between the tailored version of PostgreSQL installed with the snap and the version of PostgreSQL generally available on the machine. You can check if PosgreSQL is installed using the command ``sudo dpkg -l | grep 'postgres'``. All packages should be removed with ``sudo dpkg --purge <package>``.


v1.1
----

Release Date: 2018-01-09


New Features
~~~~~~~~~~~~

- **Startup Script**:

  - ``foglamp start`` script now checks if the Core microservice has started.
  - ``foglamp start`` creates a *core.err* file in *$FOGLAMP_DATA* and writes the stderr there. 


Known Issues
~~~~~~~~~~~~

- **Incompatibility between aiohttp and yarl when FogLAMP is built from source**: in this version we use *aiohttp 2.3.6* (|1.1 requirements|). This version is incompatible with updated versions of *yarl* (0.18.0+). If you intend to use this version, change the requirements for *aiohttp* for version 2.3.8 or higher.
- **PostgreSQL with Snap**: the issue described in version 1.0 still persists, see :ref:`1.0-known_issues` in v1.0.


v1.1.1
------

Release Date: 2018-01-18


New Features
~~~~~~~~~~~~

- **Fixed aiohttp incompatibility**: This fix is for the incompatibility of *aiohttp* with *yarl*, discovered in the previous version. The issue has been fixed.
- **Fixed avahi-daemon issue**: Avahi daemon is a pre-requisite of FogLAMP, FogLAMP can now run as a snap or build from source without avahi daemon installed.


Known Issues
~~~~~~~~~~~~

- **PostgreSQL with Snap**: the issue described in version 1.0 still persists, see :ref:`1.0-known_issues` in v1.0.


v1.2
----

Release Date: 2018-0X-XX


New Features
~~~~~~~~~~~~

- **Changes in the REST API**
  - **ping Method**: the ping method now returns uptime, number of records read/sent/purged and if FogLAMP requires REST API authentication.
- **fooglamp status**: the command now shows what the ``ping`` REST method provides.
- **setenv script**: a new script has been added to simplify the user interaction. The script is in *$FOGLAMP_ROOT/extras/scripts* and it is called *setenv.sh*.
- **foglamp service script**: a new service script has been added to setup FogLAMP as a service. The script is in *$FOGLAMP_ROOT/extras/scripts* and it is called *foglamp.service*.


Known Issues
~~~~~~~~~~~~



