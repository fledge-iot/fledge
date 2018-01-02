.. Version History presents a list of versions of FogLAMP released.

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs


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


Known Issues
~~~~~~~~~~~~

- **Startup Script**: ``foglamp start`` does not check if the Core microservice has started correctly, hence it may report that "FogLAMP started." when the process has died. As a workaround, check with ``foglamp status`` the presence of the FogLAMP microservices.
- **Snap Execution on Raspbian**: there is an issue on Raspbian when the FogLAMP snap package is used. It is an issue with the snap environment, it looks for a shared object to preload on Raspian, but the object is not available. As a workaround, a superuser should comment a line in the file */etc/ld.so.preload*. Add a ``#`` at the beginning of this line: ``/usr/lib/arm-linux-gnueabihf/libarmmem.so``. Save the file and you will be able to immediately use the snap.
- **OMF Translator North Plugin for FogLAMP Statistics**: in this version the statistics collected by FogLAMP are not sent automatically to the PI System via the OMF Translator plugin, as it is supposed to be. The issue will be fixed in a future release.


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



