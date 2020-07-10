.. Version History presents a list of versions of Fledge released.

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. |1.1 requirements| raw:: html

   <a href="https://github.com/fledge-iot/Fledge/blob/1.1/python/requirements.txt" target="_blank">check here</a>


.. =============================================


***************
Version History
***************

Fledge v1
==========

v1.8.1
-------

Release Date: 2020-07-08

- **Fledge Core**

    - New Features:

       - Support has been added for the deployment on Moxa gateways running a variant of Debian 9 Stretch.
       - The purge process has been improved to also purge the statistics history and audit trail of the system. New configuration parameters have been added to manage the amount of data to be retain for each of these.
       - An issue with installing on the Mendel Day release on Google’s Coral boards has been resolved.
       - The REST API has been expanded to allow an API call to be made to set the repository from which new packages will be pulled when installing plugins via the API and GUI.
       - A problem with the service discovery failing to respond correctly after it had been running for a short while has been rectified. This allows external micro services to now correctly discover the core micro service.
       - Details for making contributions to the Fledge project have been added to the source repository.
       - The support bundle has been improved to include more information needed to diagnose issues with sending data to PI Servers
       - The REST API has been extended to add a new call that will return statistics in terms of rates rather than absolute values. 
       - The documentation has been updated to include guidance on setting up package repositories for installing the software and plugins.


    - Bug Fix:

       - If JSON type configuration parameters were marked as mandatory there was an issue that prevented the update of the parameters. This has now been resolved.
       - After changing storage engine from sqlite to Postgres using the configuration option in the GUI or via the API, the new storage engine would incorrectly report itself as sqlite in the API and user interface. This has now been resolved.
       - External micro-services that restarted without a graceful shutdown would fail to register with the service registry as nothing was able to unregister the failed service. This has now been relaxed to allow the recovered service to be correctly registered.
       - The configuration of the storage system was previously not available via the GUI. This has now been resolved and the configuration can be viewed in the Advanced category of the configuration user interface. Any changes made to the storage configuration will only take effect on the next restart of Fledge. This allows administrators to change the storage plugins used without the need to edit the storage.json configuration file.


- **GUI**

    - Bug Fix:

       - An improvement to the user experience for editing password in the GUI has been implemented that stops the issue with passwords disappearing if the input field is clicked.
       - Password validation was not correctly occurring in the GUI wizard that adds south plugins. This has now be rectified.


- **Plugins**

    - New Features:

       - The Modbus plugin did not gracefully handle interrupted reads of data from modes TCP devices during the bulk transfer of data. This would result in assets missing certain data points and subsequent issues in the north systems that received those assets getting changes in the asset data type. This was a particular issue when dealign with the PI Web API and would result in excessive types being created. The Modbus plugin now detects the issues and takes action to ensure complete assets are read.
       - A new plugin to support Siemens S7 PLC’s has been added. The plugin uses the S7 communications protocol to pull data from the PLC.
       - A new image processing plugin, south human detector, that uses the Google Tensor Flow machine learning platform has been added to the Fledge-iot project.
       - A new Python plugin has been added that can send data north to a Kafka system.
       - A new south plugin has been added for the Dynamic Ratings B100 Electronic Temperature Monitor used for monitoring the condition of electricity transformers.
       - A new plugin has been contributed to the project by Nexcom that implements the SAE J1708 protocol for accessing the ECU's of heavy duty vehicles. 
       - An issue with missing dependencies on the Coral Mendel platform prevent 1.8.0 packages installing correctly without manual intervention. This has now been resolved.
       - The image recognition plugin, south-human-detector, has been updated to work with the Google Coral board running the Mendel Day release of Linux.


    - Bug Fix:

       - An issue with non-integer data types in the Beckhoff ADS south plugin has been rectified.
       - A missing dependency in v1.8.0 release for the package fledge-south-human-detector meant that it could not be installed without manual intervention. This has now been resolved.
       - Support has been added to the south-human-detector plugin for the Coral Camera module in addition to the existing support for USB connected cameras.
       - An issue with installation of the external shared libraries required by the USB4704 plugin has been resolved.


v1.8.0
-------

Release Date: 2020-05-08

- **Fledge Core**

    - New Features:

       - Documentation has been added for the use of the SQLite In Memory storage plugin.
       - The support bundle functionality has been improved to include more detail in order to aid tracking down issues in installations.
       - Improvements have been made to the documentation of the OMF plugin in line with the enhancements to the code. This includes the documentation of OCS and EDS support as well as PI Web API.
       - An issue with forwarding data between two Fledge instances in different time zones has been resolved.
       - A new API entry point has been added to the Fledge REST API to allow the removal of plugin packages.
       - The notification service has been updated to allow for the delivery of multiple notifications in parallel.
       - Improvements have been made to the handling of asset codes within the buffer in order to improve the ingest performance of Fledge. This is transparent to all services outside of the storage service and has no impact on the public APIs.
       - Extra information has been added to the notification trigger such that trigger time and the asset that triggered the notification is included.
       - A new configuration item type of “northTask” has been introduced. It allows the user to enter the name of a northTask in the configuration of another category within Fledge.
       - Data on multiple assets may now be requested in a single call to the asset growing API within Fledge.
       - An additional API has been added to the asset browser to allow time bucketed data to be returned for multiple data points of multiple assets in a single call.
       - Support has been added for nested readings within the reading data.
       - Messages about exceeding the configured latency of the south service may be repeated when the latency is above the configured value for a period of time. These have now been replaced with a single message when the latency is exceeded and another when the condition is cleared.
       - The feedback provided to the user when a configuration item is set to an invalid value has been improved.
       - Configuration items can now be marked as mandatory, this improves the user experience when configuring plugins.
       - A new configuration item type, code, has been added to improve the user experience when adding code snippets in configuration data.
       - Improvements have been made to the caching of configuration data within the core of Fledge.
       - The logging of package installation has been improved.
       - Additions have been added to the public API to allow multiple audit log sources to be extracted in a single API call.
       - The audit trail has been improved to show all package additions and updates in the audit trail.
       - A new API has been added to allow notification plugin packages to be updated.
       - A new API has been added to allow filter code versions to be updated.
       - A new API call has been added to allow retrieval of reading data over a period of time which is averaged into time buckets within that time period.
       - The notification service now supports rule plugins implemented in Python as well as C++.
       - Improvements have been made to the checking of configuration items such that minimum, maximum values and string lengths are now checked.
       - The plugin developers documentation has been updated to include a description building C/C++ south plugins.


    - Bug Fix:

       - Improvements have been made to the generation of the support bundle.
       - An issue in the reporting of the task names in the fledge status script has been resolved.
       - The purge by size (number of readings) would remove all data if the number of rows to retain was less than 1000, this has now been resolved.
       - On occasions plugins would disappear from the list of available plugins, this has now been resolved.
       - Improvements have been made to the management of the certificate store to ensure the correct files are uploaded to the store.
       - An expensive and unnecessary test was being performed in the asset browsing API of Fledge. This slowed down the user interface and put load n the server. This has now been removed and has improved the performance of examining the buffered data within the Fledge instance.
       - The FogBench utility used to send data to Fledge has been updated in line with new Python packages for the CoAP protocol.
       - Configuration category relationships were not always correctly cleaned up when a filter is deleted, this has now been resolved.
       - The support bundle functionality has been updated to provide information on the Python processes.
       - The REST API incorrectly allowed configuration categories with a blank name to be created. This has now been prevented.
       - Validation of minimum and maximum configuration item values was not correctly performed in the REST API, this has now been resolved.
       - Nested objects within readings could cause the storage engine to fail and those readings to not be stored. This has now been resolved.
       - On occasion shutting down a service may fail if the filters for that service have not been activated, this has now been resolved.
       - An issue that cause notifications for asset whose names contain special characters has been resolved.
       - The asset tracker was not correctly adding entries to the asset tracker, this has now been resolved.
       - An intermittent issue that prevented the notification service being enabled on the Buster release on Raspberry Pi has been resolved.
       - An intermittent problem that would prevent the north sending process to fail has been resolved.
       - Performance improvements have been made to the installation of new packages from the package repository from within the Fledge API and user interface.
       - It is now possible to reuse the name of a north process after deleting one with the same name.
       - The incorrect HTTP error code is returned by the asset summary API call if an asset does not exist, this has now been resolved.
       - Deleting and recreating a south service may cause errors in the log to appear. These have now been resolved.
       - The SQLite and SQLiteInMemory storage engines have been updated to enable a purge to be defined that reduces the number of readings to a specified value rather than simply allowing a purge by the age of the data. This is designed to allow tighter controls on the size of the buffer database when high frequency data in particular is being stored within the Fledge buffer.


- **GUI**

    - New Features:

       - The user interface for viewing logs has been improve to allow filtering by service and task.  A search facility has also been added.
       - The requirement that a key file is uploaded with every certificate file has been removed from the graphical user interface as this is not always true.
       - The performance of adding a new notification via the graphical user interface has been improved.
       - The feedback in the graphical user interface has been improved when installation of the notification service fails.
       - Installing the Fledge graphical user interface on OSX platforms fails due to the new version of the brew package manager. This has now been resolved.
       - Improve script editing has been added to the graphical user interface.
       - Improvements have been made to the user interface for the installations and enabling of the notification service.
       - The notification audit log user interface has been improved in the GUI to allow all the logs relating to notifications to be viewed in a single screen.
       - The user interface has been redesigned to make better use of the screen space when editing south and north services.
       - Support has been added to the graphical user interface to determine when configuration items are not valid based on the values of other items These items that are not valid in the current configuration are greyed out in the interface.
       - The user interface now shows the version of the code in the settings page.
       - Improvements have been made to the user interface layout to force footers to stay at the bottom of the screen.


    - Bug Fix:

       - Improvements have been made to the zoom and pan options within the graph displays.
       - The wizard used for the creation of new notifications in the graphical user interface would loose values when going back and forth between pages, this has now been resolved.
       - A memory leak that was affecting the performance of the graphical user interface has been fixed, improving performance of the interface.
       - Incorrect category names may be displayed int he graphical user interface, this has now be resolved.
       - Issues with the layout of the graphical user interface when viewed on an Apple iPad have been resolved.
       - The asset graph in the graphical user interface would sometimes not resize to fit the screen correctly, this has now been resolved.
       - The “Asset & Readings” option in the graphical user interface was initially slow to respond, this has now been improved.
       - The pagination of audit logs has bene improved when multiple sources are displayed.
       - The counts in the user interface for notifications have been corrected.
       - Asset data graphs are not able to handle correctly the transition between one day and the next. This is now resolved.


- **Plugins**

    - New Features:

       - The existing set of OMF north plugins have been rationalised and replaced by a single OMF north plugin that is able to support the connector rely, PI Web API, EDS and OCS.
       - A new notification rule plugin has been added that will trigger periodically if data is observed for a given asset. The trigger interval is defined in seconds. The plugin is primarily designed to be used with conditional forwarding as a means to sample data, although other uses might include a watchdog implementation for particular data streams.
       - When a Modbus TCP connection is closed by the remote end we fail to read a value, we then reconnect and move on to read the next value. On device with short timeout values, smaller than the poll interval, we fail the same reading every time and never get a value for that reading. The behaviour has been modified to allow us to retry reading the original value after re-establishing the connection.
       - The OMF north plugin has been updated to support the released version of the OSIsoft EDS product as a destination for data.
       - New functionality has been added to the north data to PI plugin when using PI Web API that allows the location in the PI Server AF hierarchy to be defined. A default location can be set and an override based on the asset name or metadata within the reading. The data may also be placed in multiple locations within the AF hierarchy.
       - A new notification delivery plugin has been added that allows a north task to be triggered to send data for a period of time either side of the notification trigger event. This allows conditional forwarding of large amounts of data when a trigger event occurs.
       - The asset notification delivery plugin has been updated to allow creation of new assets both for notifications that are triggered and/or cleared.
       - The rate filter now allows the termination of sending full rate data either by use of an expression or by specifying a time in milliseconds.
       - A new downsampling filter has been written that allows the rate of data to be reduced using one of a number of different algorithms.
       - A new plugin that support the Digiducer 333D01 vibration sensor has been added.
       - A new simple Python filter has been added that calculates an exponential moving average,
       - Some typos in the OPCUA south and north plugin configuration have been fixed.
       - The OPCUA north plugin has been updated to support nested reading objects correctly and also to allow a name to be set for the OPCUA server. These have also been some stability fixes in the underlying OPCUA layer used by this and the south OPCUA plugin.
       - The modbus map configuration now supports byte swapping and word swapping by use of the {{swap}} property of the map. This may take the values {{bytes}}, {{words}} or {{both}}.
       - The people detection machine learning plugin now supports RTSP streams as input.
       - The option list items in the OMF plugin have been updated to make them more user friendly and descriptive.
       - The threshold notification rule has been updated such that the unused fields in the configuration now correctly grey out in the GUI dependent upon the setting of the window type or single item asset validation.
       - The configuration of the OMF north plugin for connecting to the PI Server has been improved to give the user better feedback as to what elements are valid based on choice of connection method and security options chosen.
       - Support has been added for simple Python code to be entered into a filter that does not require all of the support code. This is designed to allow a user to very quickly develop filters with limited programming.
       - Support has been added for filters written entirely in Python, these are full featured filters as supported by the C++ filtering mechanism and include dynamic reconfiguration.
       - The fledge-filter-expression filter has been modified to better deal with streams which contain multiple assets. It is now possible to use the syntax <assetName>.<datapointName> in an expression in addition to the previous <datapointName>. The result is that if two assets in the data stream have the same data point names it is now possible to differentiate between them.
       - A new plugin to collect variables from Beckhoff PLC's has been written. The plugin uses the TwinCAT 2 or TwinCAT 3 protocols to collect specified variable from the running PLC.


    - Bug Fix:

       - An issue in the sending of data to the PI server with large values has been resolved.
       - The playback south plugin was not correctly replaying timestamps within the file, this has now been resolved.
       - Use of the asset filter in a north task could result in the north task terminating. This has now resolved.
       - A small memory leak in the south service statistics handling code was impacting the performance of the south service, this is now resolved.
       - An issue has been discovered in the Flir camera plugin with the validity attribute of the spot temperatures, this has now been resolved.
       - It was not possible to send data for the same asset from two different Fledge’s into the PI Server using PI Web API, this has now been resolved.
       - The filter Fledge RMS Trigger was not able to be dynamically reconfigured, this has now been resolved.
       - If a filter in the north sending process increased the number of readings it was possible that the limit of the number of readings sent in a single block . The sending process will now ensure this can not happen.
       - RMS filter plugin was not able to be dynamically reconfigured, this has now been resolved.
       - The HTTP South plugin that is used to receive data from another Fledge instance may fail with some combinations of filters applied to the service. This issue has now been resolved.
       - The rule filter may give errors if expressions have variables not satisfied in the reading data. Under some circumstances it has been seen that the filter fails to process data after giving this error. This has been resolved by changes to make the rate filter more robust.
       - Blank values for asset names in the south service may cause the service to become unresponsive. Blank asset names have now been correctly detected, asset names are required configuration values.
       - A new version of the driver software for the USB-4704 Data Acquisition Module has been released, the plugin has been updated to use this driver version.
       - The OPCUA North plugin might report incorrect counts for sent readings on some platforms, this has now been resolved.
       - The simple Python filter plugin was not adding correct asset tracking data, this has now been updated.
       - An issue with the asset filter failing when incorrect configuration was present has bene resolved.
       - The benchmark plugin now enforces a minimum number of asset of 1.
       - The OPCUA plugins are now available on the Raspberry Pi Buster platform.
       - Errors that prevented the use of the Postgres storage plugin have been resolved.


v1.7.0
-------

Release Date: 2019-08-15

- **Fledge Core**

    - New Features:

       - Added support for Raspbian Buster
       - Additional, optional flow control has been added to the south service to prevent it from overwhelming the storage service. This is enabled via the throttling option in the south service advanced configuration.
       - The mechanism for including JSON configuration in C++ plugins has been improved and the macros for the inline coding moved to a standard location to prevent duplication.
       - An option has been added that allows the system to be updated to the latest version of the system packages prior to installing a new plugin or component.
       - Fledge now supports password type configuration items. This allows passwords to be hidden from the user in the user interface.
       - A new feature has been added that allows the logs of plugin or other package installation to be retrieved.
       - Installation logs for package installations are now retained and available via the REST API.
       - A mechanism has been added that allows plugins to be marked as deprecated prior to the removal of these plugins in future releases. Running a deprecated plugin will result in a warning being logged, but otherwise the plugin will operate as normal.
       - The Fledge REST API has been updated to add a new entry point that will allow a plugin to be updated from the package repository.
       - An additional API has been added to fetch the set of installed services within a Fledge installation.
       - An API has been added that allows the caller to retrieve the list of plugins that are available in the Fledge package repository.
       - The /fledge/plugins REST API has been extended to allow plugins to be installed from an APT/RPM repository.
       - Addition of support for hybrid plugins. A hybrid plugin is a JSON file that defines another plugin to load along with some default configuration for that plugin. This gives a means to create a new plugin by customising the configuration of an existing plugin. An example might be a plugin for a specific modbus device type that uses the generic modbus plugin and a predefined modbus map.
       - The notification service has been improved to allow the re-trigger time of a notification to be defined by the user on a per notification basis.
       - A new environment variable, FLEDGE_PLUGIN_PATH has been added to allow plugins to be stored in multiple locations or locations outside of the usual Fledge installation directory.
       - Added support for FLEDGE_PLUGIN_PATH environment variable, that would be used for searching additional directory paths for plugins/filters to use with Fledge.
       - Fledge packages for the Google Coral Edge TPU development board have been made available.
       - Support has been added to the OMF north plugin for the PI Web API OMF endpoint. The PI Server functionality to support this is currently in beta test.

    - Bug Fix/Improvements:

       - An issue with the notification service becoming unresponsive on the Raspberry Pi Buster release has been resolved.
       - A debug message was being incorrectly logged as an error when adding a Python south plugin. The message level has now been corrected.
       - A problem whereby not all properties of configuration items are updated when a new version of a configuration category is installed has been fixed.
       - The notification service was not correctly honouring the notification types for one shot, toggled and retriggered notifications. This has now be bought in line with the documentation.
       - The system log was becoming flooded with messages from the plugin discovery utility. This utility now logs at the correct level and only logs errors and warning by default.
       - Improvements to the REST API allow for selective sets of statistic history to be retrieved. This reduces the size of the returned result set and improves performance.
       - The order in which filters are shutdown in a pipeline of filters has been reversed to resolve an issue regarding releasing Python interpreters, under some circumstances shutdowns of later filters would fail if multiple Python filters were being used.
       - The output of the `fledge status` command was corrupt, showing random text after the number of seconds for which fledge has been up. This has now been resolved.

- **GUI**

    - New Features:

       - A new log option has been added to the GUI to show the logs of package installations.
       - It is now possible to edit Python scripts directly in the GUI for plugins that load Python snippets.
       - A new log retrieval option has been added to the GUI that will show only notification delivery events. This makes it easier for a user to see what notifications have been sent by the system.
       - The GUI asset graphs have been improved such that multiple tabs are now available for graphing and tabular display of asset data.
       - The GUI menu has been reordered to move the Notifications entry below the South and North entries.
       - Support has been added to the Fledge GUI for entry of password fields. Data is obfuscated as it is entered or edited.
       - The GUI now shows plugin name and version for each north task defined.
       - The GUI now shows the plugin name and version for each south service that is configured.
       - The GUI has been updated such that it can install new plugins from the Fledge package repository for south services and north tasks. A list of available packages from the repository is displayed to allow the user to pick from that list. The Fledge instance must have connectivity tot he package repository to allow this feature to succeed.
       - The GUI now supports using certificates to authenticate with the Fledge instance.

    - Bug Fix/Improvements:

       - Improved editing of JSON configuration entities in the configuration editor.
       - Improvements have been made to the asset browser graphs in the GUI to make better use of the available space to show the graph itself.
       - The GUI was incorrectly showing Fledge as down in certain circumstances, this has now been resolved.
       - An issue in the edit dialog for the north plugin which sometimes prevented the enabled state from being correctly modified has been resolved.
       - Exported CSV data from the GUI would sometimes be missing column headers, these are now always present.
       - The exporting of data as a CSV file in the GUI has been improved such that it no longer outputs the readings as a block of JSON, but rather individual columns. This allows the data to be imported into a spreadsheet with ease.
       - Missing help text has been added for notification trigger and enabled elements.
       - A number of issues in the filter configuration editor have been resolved. These issues meant that sometimes new values were not honoured or when changes were made with multiple filters in a chain only one filter would be updated.
       - Under some rare circumstances the GUI asset graph may show incorrect dates, this issue has now been resolved.
       - The Fledge GUI build and start commands did not work on Windows platforms and preventing the running on those platforms. This has now been resolved and the Fledge GUI can be built and run on Windows platforms.
       - The GUI was not correctly interpreting the value of the readonly attribute of configuration items when the value was anything other than true. This has been resolved.
       - The Fledge GUI RPM package had an error that caused installation to fail on some systems, this is now resolved.

- **Plugins**

    - New Features:

       - A new filter has been created that looks for changes in values and only sends full rate data around the time of those changes. At other times the filter can be configured to send reduced rate averages of the data.
       - A new rule plugin has been implemented that will create notifications if the value of a data point moves more than a defined percentage from the average for that data point. A moving average for each data point is calculated by the plugin, this may be a simple average or an exponential moving average.
       - A new south plugin has been created that supports the DNP3 protocol.
       - A south plugin has been created based on the Google TensorFlow people detection model. It uses a live feed from a video camera and returns data regarding the number of people detected and the position within the frame.
       - A south plugin based on the Google TensorFlow demo model for people recognition has been created. The plugin reads an image from a file and returns the people co-ordinates of the people it detects within the image.
       - A new north plugin has been added that creates an OPCUA server based on the data ingested by the Fledge instance.
       - Support has been added for a Flir Thermal Imaging Camera connected via Modbus TCP. Both a south plugin to gather the data and a filter plugin, to clean the data, have been added.
       - A new south plugin has been created based on the Google TensorFlow demo model that accepts a live feed from a Raspberry Pi camera and classifies the images.
       - A new south plugin has been created based on the Google TensorFlow demo model for object detection. The plugin return object count, name position and confidence data.
       - The change filter has been made available on CentOS and RedHat 7 releases.

    - Bug Fix/Improvements:

       - Support  for reading floating point values in a pair of 16 bit registers has been added to the modbus plugin.
       - Improvements have been made to the performance of the modbus plugin when large numbers of contiguous registers are read. Also the addition of support for floating point values in modbus registers.
       - Flir south service has been modified to support the Flir camera range as currently available, i.e. a maximum of 10 areas as opposed to the 20 that were previously supported. This has improved performance, especially on low performance platforms.
       - The python35 filter plugin did not allow the Python code to add attributes to the data. This has now been resolved.
       - The playback south plugin did not correctly take the timestamp data from he CSV file. An option is now available that will allow this.
       - The rate filter has been enhanced to accept a list of assets that should be passed through the filter without having the rate of those assets altered.
       - The filter plugin python35 crashed on the Buster release on the Raspberry Pi, this has now been resolved.
       - The FFT filter now enforces that the number of samples must be a power of 2.
       - The ThingSpeak north plugin was not updated in line with changes to the timestamp handling in Fledge, this resulted in a crash when it tried to send data to ThingSpeak. This has been resolved and the cause of the crash also fixed such that now an error will be logged rather than the task crashing.
       - The configuration of the simple expression notification rule plugin has been simplified.
       - The DHT 11 plugin mistakenly had a dependency on the Wiring PI package. This has now been removed.
       - The system information plugin was missing a dependency that would cause it to fail to install on systems that did not already have the package it was depend on installed. This has been resolved.
       - The phidget south plugin reconfiguration method would crash the service on occasions, this has now been resolved.
       - The notification service would sometimes become unresponsive after calling the notify-python35 plugin, this has now been resolved.
       - The configuration options regarding notification evaluation of single items and windows has been improved to make it less confusing to end users.
       - The OverMax and UnderMin notification rules have been combined into a single threshold rule plugin.
       - The OPCUA south plugin was incorrectly reporting itself as the upcua plugin. This is now resolved.
       - The OPCUA south plugin has been updated to support subscriptions both using browse names and Node Id’s. Node ID is now the default subscription mechanism as this is much higher performance than traversing the object tree looking at browse names.
       - Shutting down the OPCUA service when it has failed to connect to an OPCUA server, either because of an incorrect configuration or the OPCUA server being down resulted in the service crashing. The service now shuts down cleanly.
       - In order to install the fledge-south-modbus package on RedHat Enterprise Linux or CentOS 7 you must have configured the epel repository by executing the command:

         `sudo yum install epel-release`

       - A number of packages have been renamed in order to obtain better consistency in the naming and to facilitate the upgrade of packages from the API and graphical interface to Fledge. This will result in duplication of certain plugins after upgrading to the release. This is only an issue of the plugins had been previously installed, these old plugin should be manually removed form the system to alleviate this problem.

         The plugins involved are,

          * fledge-north-http Vs fledge-north-http-north

          * fledge-south-http Vs fledge-south-http-south

          * fledge-south-Csv Vs fledge-south-csv

          * fledge-south-Expression Vs fledge-south-expression

          * fledge-south-dht Vs fledge-south-dht11V2

          * fledge-south-modbusc Vs fledge-south-modbus


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
    - RMS: Generate new asset with Root Mean Squared and Peak calculations across data streams
    - FFT (beta): execute a Fast Fourier Transform across a data stream. Valuable for Vibration Analysis
    - Many others


- **Event Notification Engine (beta)**
 
    - Run rules to detect conditions and generate events at the edge
    - Default Delivery Mechanisms: email, external script
    - Fully pluggable, so custom Rules and Delivery Mechanisms can be easily created


- **Debian Packages for All Repo's**


v1.4.1
------

Release Date: 2018-10-10



v1.4.0
------

Release Date: 2018-09-25



v1.3.1
------

Release Date: 2018-07-13


Fixed Issues
~~~~~~~~~~~~

- **Open File Descriptors**

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

  - **coap**: coap south plugin was moved into its own repository https://github.com/fledge-iot/fledge-south-coap
  - **http**: http south plugin was moved into its own repository https://github.com/fledge-iot/fledge-south-http


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


