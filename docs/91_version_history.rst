.. Version History presents a list of versions of Fledge released.

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. |1.1 requirements| raw:: html

   <a href="https://github.com/fledge/Fledge/blob/1.1/python/requirements.txt" target="_blank">check here</a>


.. =============================================


***************
Version History
***************

Fledge v1
==========

v1.6.0
-------

Release Date: 2019-05-22

- **Fledge Core**

    - New Features:

       - The scope of the Fledge certificate store has been widen to allow it to store .pem certificates and keys for accessing cloud functions.
       - The creation of a Docker container for Fledge has been added to the packaging options for Fledge in this version of Fledge.
       - Red Hat Enterprise Linux packages have been made available from this release of Fledge onwards. These packages include all the applicable plugins and notification service for Fledge.
       - The Fledge API now supports the creation of configuration snapshots which can be used to create configuration checkpoints and rollback configuration changes.
       - The Fledge administration API has been extended to allow the installation of new plugins via API.
       

    - Improvements/Bug Fix:

       - A bug that prevents multiple Fledge's on the same network being discoverable via multicast DNS lookup has been fixed.
       - Set, unset optional configuration attributes


- **GUI**

    - New Features:
       
       - The Fledge Graphical User Interface now has the ability to show sets of graphs over a time period for data such as the spectrum analysis produced but the Fast Fourier transform filter.
       - The Fledge Graphical User Interface is now available as an RPM file that may be installed on Red Hat Enterprise Linux or CentOS.


    - Improvements/Bug Fix:

       - Improvements have been made to the Fledge Graphical User Interface to allow more control of the time periods displayed in the graphs of asset values.
       - Some improvements to screen layout in the Fledge Graphical User Interface have been made in order to improve the look and reduce the screen space used in some of the screens.
       - Improvements have been made to the appearance of dropdown and other elements with the Fledge Graphical User Interface.


- **Plugins**

    - New Features:
       - A new threshold filter has been added that can be used to block onward transmission of data until a configured expression evaluates too true.
       - The Modbus RTU/TCP south plugin is now available on CentOS 7.6 and RHEL 7.6.
       - A new north plugin has been added to allow data to be sent the Google Cloud Platform IoT Core interface.
       - The FFT filter now has an option to output raw frequency spectra. Note this can not be accepted into all north bound systems.
       - Changed the release status of the FFT filter plugin.
       - Added the ability in the modbus plugin to define multiple registers that create composite values. For example two 16 bit registers can be put together to make one 32 bit value. This is does using an array of register values in a modbus map, e.g. {"name":"rpm","slave":1,"register":[33,34],"scale":0.1,"offset":0}. Register 33 contains the low 16 its of the RPM and register 34 the high 16 bits of the RPM.
       - Addition of a new Notification Delivery plugin to send notifications to a Google Hangouts chatroom.
       - A new plugin has been created that uses machine learning based on Google's TensorFlow technology to classify image data and populate derived information the north side systems. The current TensorFlow model in use will recognise hard written digits and populate those digits. This plugins is currently a proof of concept for machine learning. 


    - Improvements/Bug Fix:
       - Removal of unnecessary include directive from Modbus-C plugin.
       - Improved error reporting for the modbus-c plugin and added documentation on the configuration of the plugin.
       - Improved the subscription handling in the OPCUA south plugin.
       - Stability improvements have been made to the notification service, these related to the handling of dynamic reconfigurations of the notifications.
       - Removed erroneous default for script configuration option in Python35 notification delivery plugin.
       - Corrected description of the enable configuration item.


v1.5.2
-------

Release Date: 2019-04-08

- **Fledge Core**

    - New Features:
       - Notification service, notification rule and delivery plugins
       - Addition of a new notification delivery plugin that will create an asset reading when a notification is delivered. This can then be sent to any system north of the Fledge instance via the usual mechanisms
       - Bulk insert support for SQLite and Postgres storage plugins

    - Enhancements / Bug Fix:
       - Performance improvements for SQLite storage plugin.
       - Improved performance of data browsing where large datasets have been acquired
       - Optimized statistics history collection
       - Optimized purge task
       - The readings count shown on GUI and south page and corresponding API endpoints now shows total readings count and not what is currently buffered by Fledge. So these counts don't reduce when purge task runs
       - Static data in the OMF plugin was not being correctly taken from the plugin configuration
       - Reduced the number of informational log messages being sent to the syslog


- **GUI**

    - New Features:
       - Notifications UI

    - Bug Fix:
       - Backup creation time format


v1.5.1
-------

Release Date: 2019-03-12

- **Fledge Core**

    - Bug Fix: plugin loading errors


- **GUI**

    - Bug Fix: uptime shows up to 24 hour clock only


v1.5.0
-------

Release Date: 2019-02-21

- **Fledge Core**

    - Performance improvements and Bug Fixes
    - Introduction of Safe Mode in case Fledge is accidentally configured to generate so much data that it is overwhelmed and can no longer be managed.


- **GUI**

    - re-organization of screens for Health, Assets, South and North
    - bug fixes


- **South**

    - Many Performance improvements, including conversion to C++
    - Modbus plugin
    - many other new south plugins


- **North**

    - Compressed data via OMF
    - Kafka


- **Filters**: Perform data pre-processing, and allow distributed applications to be built on Fledge.

    - Delta: only send data upon change
    - Expression: run a complex mathematical expression across one or more data streams
    - Python: run arbitrary python code to modify a data stream
    - Asset: modify Asset metadata
    - RMS: Generate new asset with Root Mean Squared and Peak calcuations across data streams
    - FFT (beta): execute a Fast Fourier Transform across a data stream. Valuable for Vibration Analysis
    - Many others


- **Event Notification Engine (beta)**
 
    - Run rules to detect conditions and generate events at the edge
    - Default Delivery Mechanisms: email, external script
    - Fully pluggable, so custom Rules and Delivery Mechanisms can be easily created


- **Debian Packages for All Repo's**


v1.4.1
----

Release Date: 2018-10-10



v1.4.0
----

Release Date: 2018-09-25



v1.3.1
----

Release Date: 2018-07-13


Fixed Issues
~~~~~~~~~~~~

- **Open File Descriptiors**

  - **open file descriptors**: Storage service did not close open files, leading to multiple open file descriptors



v1.3
----

Release Date: 2018-07-05


New Features
~~~~~~~~~~~~

- **Python version upgrade**

  - **python 3 version**: The minimal supported python version is now python 3.5.3. 

- **aiohttp python package version upgrade**

  - **aiohttp package version**: aiohttp (version 3.2.1) and aiohttp_cors (version 0.7.0) is now being used
  
- **Removal of south plugins**

  - **coap**: coap south plugin was moved into its own repository https://github.com/fledge/fledge-south-coap
  - **http**: http south plugin was moved into its own repository https://github.com/fledge/fledge-south-http


Known Issues
~~~~~~~~~~~~

- **Issues in Documentation**

  - **plugin documentation**: testing Fledge requires user to first install southbound plugins necessary (CoAP, http)



v1.2
----

Release Date: 2018-04-23


New Features
~~~~~~~~~~~~

- **Changes in the REST API**

  - **ping Method**: the ping method now returns uptime, number of records read/sent/purged and if Fledge requires REST API authentication.

- **Storage Layer**

  - **Default Storage Engine**: The default storage engine is now SQLite. We provide a script to migrate from PostgreSQL in 1.1.1 version to 1.2. PostgreSQL is still available in the main repository and package, but it will be removed to an operate repository in future versions. 
  
- **Admin and Maintenance Scripts**

  - **fledge status**: the command now shows what the ``ping`` REST method provides.
  - **setenv script**: a new script has been added to simplify the user interaction. The script is in *$FLEDGE_ROOT/extras/scripts* and it is called *setenv.sh*.
  - **fledge service script**: a new service script has been added to setup Fledge as a service. The script is in *$FLEDGE_ROOT/extras/scripts* and it is called *fledge.service*.


Known Issues
~~~~~~~~~~~~

- **Issues in the REST API**

  - **asset method response**: the ``asset`` method returns a JSON object with asset code named ``asset_code`` instead of ``assetCode``
  - **task method response**: the ``task`` method returns a JSON object with unexpected element ``"exitCode"``


v1.1.1
------

Release Date: 2018-01-18


New Features
~~~~~~~~~~~~

- **Fixed aiohttp incompatibility**: This fix is for the incompatibility of *aiohttp* with *yarl*, discovered in the previous version. The issue has been fixed.
- **Fixed avahi-daemon issue**: Avahi daemon is a pre-requisite of Fledge, Fledge can now run as a snap or build from source without avahi daemon installed.


Known Issues
~~~~~~~~~~~~

- **PostgreSQL with Snap**: the issue described in version 1.0 still persists, see :ref:`1.0-known_issues` in v1.0.


v1.1
----

Release Date: 2018-01-09


New Features
~~~~~~~~~~~~

- **Startup Script**:

  - ``fledge start`` script now checks if the Core microservice has started.
  - ``fledge start`` creates a *core.err* file in *$FLEDGE_DATA* and writes the stderr there. 


Known Issues
~~~~~~~~~~~~

- **Incompatibility between aiohttp and yarl when Fledge is built from source**: in this version we use *aiohttp 2.3.6* (|1.1 requirements|). This version is incompatible with updated versions of *yarl* (0.18.0+). If you intend to use this version, change the requirements for *aiohttp* for version 2.3.8 or higher.
- **PostgreSQL with Snap**: the issue described in version 1.0 still persists, see :ref:`1.0-known_issues` in v1.0.


v1.0
----

Release Date: 2017-12-11


Features
~~~~~~~~

- All the essential microservices are now in place: *Core, Storage, South, North*.
- Storage plugins available in the main repository:

  - **Postgres**: The storage layer relies on PostgreSQL for data and metadata

- South plugins available in the main repository:

  - **CoAP Listener**: A CoAP microservice plugin listening to client applications that send data to Fledge

- North plugins available in the main repository:

  - **OMF Translator**: A task plugin sending data to OSIsoft PI Connector Relay 1.0


.. _1.0-known_issues:

Known Issues
~~~~~~~~~~~~

- **Startup Script**: ``fledge start`` does not check if the Core microservice has started correctly, hence it may report that "Fledge started." when the process has died. As a workaround, check with ``fledge status`` the presence of the Fledge microservices.
- **Snap Execution on Raspbian**: there is an issue on Raspbian when the Fledge snap package is used. It is an issue with the snap environment, it looks for a shared object to preload on Raspian, but the object is not available. As a workaround, a superuser should comment a line in the file */etc/ld.so.preload*. Add a ``#`` at the beginning of this line: ``/usr/lib/arm-linux-gnueabihf/libarmmem.so``. Save the file and you will be able to immediately use the snap.
- **OMF Translator North Plugin for Fledge Statistics**: in this version the statistics collected by Fledge are not sent automatically to the PI System via the OMF Translator plugin, as it is supposed to be. The issue will be fixed in a future release.
- **Snap installed in an environment with an existing version of PostgreSQL**: the Fledge snap does not check if another version of PostgreSQL is available on the machine. The result may be a conflict between the tailored version of PostgreSQL installed with the snap and the version of PostgreSQL generally available on the machine. You can check if PostgreSQL is installed using the command ``sudo dpkg -l | grep 'postgres'``. All packages should be removed with ``sudo dpkg --purge <package>``.


