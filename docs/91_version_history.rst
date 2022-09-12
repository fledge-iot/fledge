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

Fledge v2
==========

v2.0.0
-------

Release Date: 2022-08-03

- **Fledge Core**

    - New Features:

       - Add options for choosing the Fledge Asset name: Browser Name, Subscription Path and Full Path. Use the OPC UA Source timestamp as the User Timestamp in Fledge.
       - The storage interface used to query generic configuration tables has been improved to support tests for null and non-null column values.
       - The ability for north services to support control inputs coming from systems north of Fledge has been introduced.
       - The handling of a failed storage service has been improved. The client now attempt to re-connect and if that fails they we will down. The logging produced is now much less verbose, removing the repeated messages previously seen.
       - A new service has been added to Fledge to facilitate the routing of control messages within Fledge. This service is responsible for determined which south services to send control requests to and also for the security aspects of those requests.
       - Ensure that new Fledge data types not supported by OMF are not processed.
       - The storage service now supports a richer set of queries against the generic table interface. In particular joins between tables are now supported.
       - OPC UA Security has been enhanced. This plugin now supports Security Policies Basic256 and Basic256Sha256, with Security Modes Sign and Sign & Encrypt. Authentication types are anonymous and username/password.
       - South services that have a slow poll rate can take a long time to shutdown, this sometimes resulted in those services not shutting down cleanly. The shutdown process has been modified such that these services now shutdown promptly regardless of polling rate.
       - A new configuration item type has been added for the selection of access control lists.
       - Support has been added to the Python query builder for NULL and NOT NULL columns.
       - The Python query builder has been updated to support nested database queries.
       - The third party packages on which Fledge is built have been updated to use the latest versions to resolve issues with vulnerabilities in these underlying packages.
       - When the data stream from a south plugin included an OMF Hint of AFLocation, performance of the OMF North plugin would degrade. In addition, process memory would grow over time. These issues have been fixed.
       - The version of the PostgreSQL database used by the Postgres storage plugin has been updated to PostgreSQL 13.
       - An enhancement has been added to the North service to allow the user to specify the block size to use when sending data to the plugin. This helps tune the north services and is described in the tuning guide within the documentation.
       - The notification server would previously output warning messages when it was starting, these were not an indication of a problem and should have been information messages. This has now been resolved.
       - The backup mechanism has been improved to include some external items to be include in the backup and provide a more secure backup.
       - The purge option that controls if unsent assets cane purged or not has been enhanced to provide options for sent to any destination or sent to all destinations as well as sent to no destinations.
       - It is now possible to add control features to Python south plugins.
       - Certificate based authentication is now possible between services in a single instance. This allows for secure control messages to be implemented between services.
       - Performance improvements have been made such that the display of south service data when large numbers of assets are in use has been improved.
       - The new micro service, control dispatcher, is now available as a package that can be installed via the package manager.
       - New data types are now supported for data points within an asset and are encoded into various Python types when passed to Python plugins or scripts run within standard plugin. This includes numpy arrays for images and data buffers, 2 dimensional Python lists and others. Details of the type encoding can be found in the plugin developers guide of the online product documentation.
       - The mechanism for online update of configuration has been extended to allow for more configuration to be modified without the need to restart any services.
       - Support has been added for the Raspberry Pi Bullseye release.
       - A problem with a file descriptor leak in Python that could cause Fledge to fail has been resolved.
       - The control of logging levels has now been added to the Python code run within a service such that the advanced settings option is now honoured by the Python code.
       - Enhancements have been made to the asset tracker API to retrieve the service responsive for the ingest of a given asset.
       - A new API has been added to allow external viewing and managing of the data that various plugins persist.
       - A new REST API entry point has been added that allows all instances of a specified asset to be purged from the buffer. A further entry point has also been added to purge all data from the reading buffer. These entry points should be used with care as they will cause data to be discarded.
       - A new parameter has been added to the asset retrieval API that allows image data to be returned, images=include. By default image type datapoints will be replaced with a message, “Image removed for brevity”, in order to reduce the size of the returned payload.
       - A new API has been added to the management API that allows services to request that URL’s in the public API are proxied to the service API. This is used when extending the functionality of the system with custom microservices.
       - A new set of API calls have been added to the public REST API of the product to support the control dispatcher and for the creation and management of control scripts.
       - A new API call has been added to Fledge that allows the core package to be updated and Fledge restarted with the updated version.
       - A new API has been added to the public API that will return the latest reading for a given asset. This will return all data types including images.
       - A new API has been added that allows asset tracking records to be marked as deprecated. This allows the flushing of relationships between assets and the services that have processed them. It is useful only in development systems and should not be used in production systems.
       - A new API call has been added that allows the persisted data related to a plugin to be retrieved via the public REST API. The is intended for use by plugin writers and to allow for better tracking of data persisted between service executions.
       - A new query parameter has been added to the API used to fetch log messages from the system log, nontotals. This will increase the performance of the call at the expense of not returning the total number of logs that match the search criteria.
       - New API entry points have been added for the management of Python packages.
       - Major performance improvements have been made to the code for retrieving log messages from the system log. This is mainly an issue on systems with very large log files.
       - The storage service API has been extended to support the creation of private schemas for the use of optional micro services registered to a Fledge instance.
       - Filtering by service type has now been added to the API that retrieve service information via the public REST API.
       - A number of new features have been added to the user interface to aid developers creating data pipelines and plugins. These features allow for manual purging of data, deprecating the relationship between the services and the assets they have ingested and viewing the persisted data of the plugins. These are all documented in the section on developing pipelines within the online documentation.
       - A new section has been added to the documentation which discusses the process and best practices for building data pipelines in Fledge.
       - A glossary has been added to the documentation for the product.
       - The documentation that describes the writing of asynchronous Python plugins has been updated in line with the latest code changes.
       - The documentation has been updated to reflect the new tabs available in the Fledge user interface for editing the configuration of services and tasks.
       - A new introduction section has been added to the Fledge documentation that describes the new features and some typical use cases of Fledge.
       - A new section has been added to the Fledge Tuning guide that discusses the tuning of North services and tasks. Also scheduler tuning has been added to the tuning guide along with the tuning of the service monitor which is used to detected failures of services within Fledge.
       - The Tuning Fledge section of the documentation has been updated to include information on tuning the Fledge service monitor that is used to monitor and restart Fledge services. A section has also been added that describes the tuning of north services and tasks. A new section describes the different storage plugins available, when they should be used and how to tune them.
       - Added an article on Developing with Windows Subsystem for Linux (WSL2) to the Plugin Developer Guide. WSL2 allows you to run a Linux environment directly on Windows without the overhead of Windows Hyper-V. You can run Fledge and develop plugins on WSL2.
       - Documentation has been added for the purge process and the new options recently added.
       - Documentation has been added to the plugin developer guides that explain what needs to be done to allow the packaging mechanism to be able to package a plugin.
       - Documentation has been added to the Building Pipelines section of the documentation for the new UI feature that allows Python packages to be installed via the user interface.
       - Documentation has been updated to show how to build Fledge using the requirements.sh script.
       - The documentation ordering has been changed to make the section order more logical.
       - The plugin developers guide has been updated to include information on the various flags that are used to communicate the options implemented by a plugin.
       - Updated OMF North plugin documentation to include current OSIsoft product names.
       - Fixed a typo in the quick start guide.
       - Improved north plugin developers documentation is now available.

    - Bug Fix:

       - The Fledge control script has options for purge and reset that requires a confirmation before it will continue. The message that was produced if this confirmation was not given was unclear. This has now been improved.
       - An issue that could cause a north service or task that had been disabled for a long period of time to fail to send data when it was re-enabled has been resolved.
       - S2OPCUA Toolkit changes required an update in build procedures for the S2OPCUA South Plugin.
       - Previously it has not been possible to configure the advanced configuration of a south service until it has been run at least once. This has now been resolved and it is possible to add a south service in disable mode and edit the advanced configuration.
       - The diagnostics when a plugin fails to load have been improved.
       - The South Plugin shutdown problem was caused by errors in the plugin startup procedure which would throw an exception for any error. The plugin startup has been fixed so errors are reported properly. The problem of plugin shutdown when adding a filter has been resolved.
       - The S2OPCUA South Plugin would throw an exception for any error during startup. This would cause the core system to shut down the plugin permanently after a few retries. This has been fixed. Error messages has been recategorized to properly reflect informational, warning and error messages.
       - The update process has been optimised to remove an unnecessary restart if no new version of the software are available.
       - The OMF North plugin was unable to process configuration changes or shut down if the PI Web API hostname was not correct. This has been fixed.
       - S2OPC South plugin builds have been updated to explicitly reference S2OPC Toolkit Version 1.2.0.
       - An issue that could on rare occasions cause the SQLite plugin to silently discard a readings has been resolved.
       - An issue with the automatic renewal of authentication certificates has been resolved.
       - Deleting a service which had a filter pipeline could cause some orphaned configuration information to be left stored. This prevented creating filters of the same name in the future. This has now been resolved.
       - The error reporting has been improved when downloading backups from the system.
       - An issue that could cause north plugins to occasionally fail to shutdown correctly has now been resolved.
       - The documentation has been updated to correct a statement regarding running the south side as a task.


- **GUI**

    - New Features:

        - A new *Developer* item has been added to the user interface to allow for the management of Python packages via the UI. This is enabled by turning on developer features in the user interface *Settings* page.
        - A control has been added that allows the display of assets in the *South* screen to be collapsed or expanded. This allows for more services to be seen when services ingest multiple assets.
        - A new feature has been added to the south page that allows the relationship between an asset and a service to be deprecated. This is a special feature enabled with the Developer Features option. See the documentation on building pipelines for a full description.
        - A new feature has been added to the Assets and Readings page that allows for manual purging of named assets or all assets. This is a developer only feature and should not be used on production systems. The feature is enabled, along with other developer features via the Settings page.
        - A new feature has been added to the South and North pages for each service that allows the user to view, import, export and delete the data persisted by a plugin. This is a developer only feature and should not be used on production systems. It is enabled via the Setting page.
        - A new configuration type, Access Control List, is now supported ints user interface. This allows for selection of an ACL from those already created.
        - A new tabbed layout has been adopted for the editing of south and north services and tasks. Configuration, Advanced and Security tabs are supported as our tabs for developer features if enabled.
        - The user interface for displaying system logs has been modify to improve the performance of log viewing.
        - The User Interface has been updated to use the latest versions of a number of packages it depends upon in due to vulnerabilities reported in those packages.
        - The new FogLAMP Bucket Storage service in now included in the service status display on the GUI.
        - With the introduction of image data types to the readings supported by the system the user interface has been updated to add visualisation features for these images. A new feature also allows the latest reading for a given asset to be shown.
        - A new feature has been added to the south and north pages that allows the user to view the logs for the service.
        - The service status display now includes the Control Dispatcher service if it has been installed.
        - The user interface now supports the new control dispatcher service. This includes the graphical creation and editing of control scripts and access control lists used by control features.
        - An option has been added to the Asset and Readings page to show just the latest values for a given asset.
        - The notification user interface now links to the relevant sections of the online documentation allowing users to navigate to the help based on the current context.
        - Some timezone inconsistencies in the user interface have been resolved.

    - Bug Fix:

        - An issue that would cause the GUI to not always allow JSON data to be saved has been resolved.
        - An issue with the auto refresh in the systems log page that made selecting the service to filter difficult has been resolved.
        - The sorting of services and tasks in the South and North pages has been improved such that enabled services appear above disabled services.
        - An issue the prevented gaps in the data from appearing int he groans displayed by the GUI has now been resolved.
        - Entering times in the GUI could sometimes be difficult and result in unexpected results. This has now been improved to ease the entry of time values.


- **Plugins**

    - New Features:

       - A new notification delivery fledge-notify-control plugin has been added that allows notifications to be delivered via the control dispatcher service. This allows the full features of the control dispatcher to be used with the edge notification path.
       - Support has been added for proxy servers in the north HTTP-C plugin.
       - The OPCUA north plugin has been updated to include the ability for systems outside of Fledge to write to the server that Fledge advertises. These write are taken as control input into the Fledge system.
       - The HTTPC North plugin has been enhanced to add an optional Python script that can be used to format the payload of the data sent in the HTTP REST request.
       - The SQLite storage plugins have been updated to support service extension schemas. This is a mechanism that allows services within the Fledge system to add new schemas within the storage service that are exclusive to that service.
       - The Python35 filter has been updated to use the common Python interpreter. This allows for packages such as numpy to be used. The resilience and error reporting of this plugin have also been improved.
       - A set of developer only features designed to aid the process of developing data pipelines and plugins has been added in this release. These features are turned on and off via a toggle setting on the Settings page.
       - A new option has been added to the Python35 filter that changes the way datapoint names are used in the JSOn readings. Previously there had to be encoded and decode by use of the b’xxx' mechanism. There is now a toggle that allows for either this to be required or simple text string use to be enabled.
       - The API of the storage service has been updated to allow for custom schemas to be created by services that extend the core functionality of the system.
       - New image type datapoints can now be sent between instances using the http north and south plugins.
       - A new watchdog notification rule plugin has been added that allows notifications to be send if data stops being ingress for specified assets.
       - The ability to define response headers in the http south plugin has been added to aid certain circumstances where CORS provided data flows.
       - The documentation of the Python35 filter has been updated to included a fuller description of how to make use of the configuration data block supported by the plugin.
       - The documentation describing how to run services under the debugger has been improved along with other improvements to the documentation aimed at plugin developers.
       - Documentation has been added for the Azure north plugin.
       - Documentation has now been added for fledge-north-harperdb.
       - Documentation has been added for the Video4Linux plugin.
       - Documentation has been added for the custom asset notification plugin.
       - The documentation has been updated to include the new watchdog notification rule.


    - Bug Fix:

       - Build procedures were updated to accommodate breaking changes in the S2OPC OPCUA Toolkit.
       - Occasionally switching from the sqlite to the sqlitememory plugin for the storage of readings would cause a fatal error in the storage layer. This has now been fixed and it is possible to change to sqlitememory without an error.
       - A race condition within the modbus south plugin that could cause unfair scheduling of read verses write operations has been resolved. This could cause write operations to be delayed in some circumstances. The scheduling of set point write operations is now fairly interleaved between the read operations in all cases.
       - A problem that caused the HTTPC North plugin to fail if the path component of the URL was omitted has been resolved.
       - The modbus-c south plugin documentation has been enhanced to include details of the function codes used to read modbus data.
       - An incorrect error message in the modbus-c south plugin has been fixed and others have been improved to aid resolving configuration issues. The documentation has been updated to include descriptive text for the error messages that may occur.
       - The Python35 filter plugin has been updated such that if no data is to be passed onwards it may now simply return the None Python constant or an empty list.
       - The Python35 plugin which allows simple Python scripts to be added into filter pipelines has had a number of updates to improve the robustness of the plugin in the event of incorrect script code being provided by the user. The behaviour of the plugin has also been updated such that any errors run the script will prevent data being passed onwards the filter pipeline.
       - The Average rule has been updated to improve the user interaction during the configuration of the rule.
       - The first time a plugin that persisted data is executed erroneous errors and warnings would be written to the system log. This has now been resolved.
       - Python35 filter code that failed to return a properly formed asset in the response would previously crash rather than fail gracefully. An error explaining the exact cause of the failure is now logged in the system log.
       - An issue with the Kafka north plugin not sending data in certain circumstances has been resolved.
       - Adding some notification plugins would cause incorrect errors to be logged to the system log. The functioning of the notifications was not affected. This has now been resolved and the error logs no longer appear.
       - The documentation for the fledge-rule-delta plugin has been corrected.
       - The documentation for the Python35 filter has been updated to discuss Python package imports and issues when removing previously used imports.


Fledge v1
==========


v1.9.2
-------

Release Date: 2021-09-29

- **Fledge Core**

    - New Features:

       - The ability for south plugins to persist data between executions of south services has been added for plugins written in C/C++. This follows the same model as already available for north plugins.              
       - Notification delivery plugins now also receive the data that caused the rule to trigger. This can be used to deliver values in the notification delivery plugins.
       - A new option has been added to the sqlite storage plugin only that allows assets to be excluded from consideration in the purge process.
       - A new purge process has been added to control the growth of statistics history and audit trails. This new process is known as the "System Purge" process.
       - The support bundle has been updated to include details of the packages installed.
       - The package repository API endpoint has been updated to support Ubuntu 20.04 repository end point.
       - The handling of updates from RPM package repositories has been improved.       
       - The certificate store has been updated to support more formats of certificates, including DER, P12 and PFX format certificates.     
       - The documentation has been updated to include an improved & detailed introduction to filters.
       - The OMF north plugin documentation has been re-organised and updated to include the latest features that have been introduced to this plugin.
       - A new section has been added to the documentation that discusses the tuning of the edge based control path.


    - Bug Fix:
       - A rare race condition during ingestion of readings would cause the south service to terminate and restart. This has now been resolved.       
       - In some circumstances it was seen that north services could send the same data more than once. This has now been corrected.
       - An issue that caused an intermittent error in the tracking of data sent north has been resolved. This only impacted north services and not north tasks.
       - An optimisation has been added to prevent north plugins being sent empty data sets when the filter chain removes all the data in a reading set.
       - An issue that prevented a north service restarting correctly when certain combinations of filters were present has been resolved.
       - The API for retrieving the list of backups on the system has been improved to honour the limit and offset parameters.
       - An issue with the restore operation always restoring the latest backup rather than the chosen backup has been resolved.
       - The support package failed to include log data if binary data had been written to syslog. This has now been resolved.
       - The configuration category for the system purge was in the incorrect location with the configuration category tree, this has now been correctly placed underneath the “Utilities” item.
       - It was not possible to set a notification to always retrigger as there was a limitation that there must always be 1 second between notification triggers. This restriction has now been removed and it is possible to set a retrigger time of zero.
       - An error in the documentation for the plugin developers guide which incorrectly documented how to build debug binaries has been corrected.


- **GUI**

    - New Features:

       - The user interface has been updated to improve the filtering of logs when a large number of services have been defined within the instance.
       - The user interface input validation for hostnames and port has been improved in the setup screen. A message  is now displayed when an incorrect port or address is entered.
       - The user interface now prompts to accept a self signed certificate if one is configured.


    - Bug Fix:

       - If a south or north plugin included a script type configuration item the GUI failed to allow the service or task using this plugin to be created correctly. This has now been resolved.
       - The ability to paste into password fields has been enabled in order to allow copy/paste of keys, tokens etc into configuration of the south and north services.
       - An issue that could result in filters not being correctly removed from a pipeline of 2 or more filters has been resolved.


- **Plugins**

    - New Features:

       - A new OPC/UA south plugin has been created based on the Safe and Secure OPC/UA library. This plugin supports authentication and encryption mechanisms.
       - Control features have now been added to the modbus south plugin that allows the writing of registers and coils via the south service control channel.      
       - The modbus south control flow has been updated to use both 0x06 and 0x10 function codes. This allows items that are split across multiple modbus registers to be written in a single write operation.
       - The OMF plugin has been updated to support more complex scenarios for the placement of assets with the PI Asset Framework.
       - The OMF north plugin hinting mechanism has been extended to support asset framework hierarchy hints.
       - The OMF north plugin now defaults to using a concise naming scheme for tags in the PI server.      
       - The Kafka north plugin has been updated to allow timestamps of higher granularity than 1 second, previously timestamps would be truncated to the previous second.
       - The Kafka north plugin has been enhanced to give the option of sending JSON objects as strings to Kafka, as previously the default, or sending them as JSON objects.
       - The HTTP-C north plugin has been updated to allow the inclusion of customer HTTP headers.
       - The Python35 Filter plugin did not correctly handle string type data points. This has now been resolved.
       - The OMF Hint filter documentation has been updated to describe the use of regular expressions when defining the asset name to which the hint should be applied.


    - Bug Fix:

       - An issue with string data that had quote characters embedded within the reading data has been resolved. This would cause data to be discarded with a bad formatting message in the log.       
       - An issue that could result in the configuration for the incorrect plugin being displayed has now been resolved.       
       - An issue with the modbus south plugin that could cause resource starvation in the threads used for set point write operations has been resolved.
       - A race condition in the modbus south that could cause an issue if the plugin configuration is changed during a set point operation.
       - The CSV playback south plugin installation on CentOS 7 platforms has now been corrected.
       - The error handling of the OMF north plugin has been improved such that assets that contain data types that are not supported by the OMF endpoint of the PI Server are removed and other data continues to be sent to the PI Server.
       - The Kafka north plugin was not always able to reconnect if the Kafka service was not available when it was first started. This issue has now been resolved. 
       - The Kafka north plugin would on occasion duplicate data if a connection failed and was later reconnected. This has been resolved.
       - A number of fixes have been made to the Kafka north plugin, these include; fixing issues caused by quoted data in the Kafka payload, sending timestamps accurate to the millisecond, fixing an issue that caused data duplication and switching the the user timestamp.
       - A problem with the quoting of string type data points on the North HTTP-C plugin has been fixed.
       - String type variables in the OPC/UA north plugin were incorrectly having extra quotes added to them. This has now been resolved.
       - The delta filter previously did not manage calculating delta values when a datapoint changed from being an integer to a floating point value or vice versa. This has now been resolved and delta values are correctly calculated when these changes occur.
       - The example path shown in the DHT11 plugin in the developers guide was incorrect, this has now been fixed.


v1.9.1
-------

Release Date: 2021-05-27

- **Fledge Core**

    - New Features:

       - Support has been added for Ubuntu 20.04 LTS.
       - The core components have been ported to build and run on CentOS 8
       - A new option has been added to the command line tool that controls the system. This option, called purge, allows all readings related data to be purged from the system whilst retaining the configuration. This allows a system to be tested and then reset without losing the configuration.
       - A new service interface has been added to the south service that allows set point control and operations to be performed via the south interface. This is the first phase of the set point control feature in the product.
       - The documentation has been improved to include the new control functionality in the south plugin developers guide.
       - An improvement has been made to the documentation layout for default plugins to make the GUI able to find the plugin documentation.
       - Documentation describing the installation of PostgreSQL on CentOS has been updated.
       - The documentation has been updated to give more detail around the topic of self-signed certificates.


    - Bug Fix:

       - A security flaw that allowed non-privileged users to update the certificate store has been resolved.
       - A bug that prevented users being created with certificate based authentication rather than password based authentication has been fixed.
       - Switching storage plugins from SQLite to PostgreSQL caused errors in some circumstances. This has now been resolved.
       - The HTTP code returned by the ping command has been updated to correctly report 401 errors if the option to allow ping without authentication is turned off.
       - The HTTP error code returned when the notification service is not available has been corrected.
       - Disabling and re-enabling the backup and restore task schedules sometimes caused a restart of the system. This has now been resolved.
       - The error message returned when schedules could not be enabled or disabled has been improved.
       - A problem related to readings with nested data not correctly getting copied has been resolved.
       - An issue that caused problems if a service was deleted and then a new service was recreated using the name of the previously deleted service has been resolved.


- **GUI**

    - New Features:

       - Links to the online help have been added on a number of screens in the user interface.
       - Improvements have been made to the user management screens of the GUI.


- **Plugins**

    - New Features:

       - North services now support Python as well as C++ plugins.
       - A new delivery notification plugin has been added that uses the set point control mechanism to invoke an action in the south plugin.
       - A new notification delivery mechanism has been implemented that uses the set point control mechanism to assert control on a south service. The plugin allows you to set the values of one or more control items on the notification triggered and set a different set of values when the notification rule clears.
       - Support has been added in the OPC/UA north plugin for array data. This allows FFT spectrum data to be represented in the OPC/UA server.
       - The documentation for the OPC/UA north plugin has been updated to recommend running the plugin as a service.
       - A new storage plugin has been added that uses SQLite. This is designed for situations with low bandwidth sensors and stores all the readings within a single SQLite file.
       - Support has been added to use RTSP video streams in the person detection plugin.
       - The delta filter has been updated to allow an optional set of asset specific tolerances to be added in addition to the global tolerance used by the plugin when deciding to forward data.
       - The Python script run by the MQTT scripted plugin now receives the topic as well as the message.
       - The OMF plugin has been updated in line with recommendations from the OMF group regarding the use of SCRF Defense.
       - The OMFHint plugin has been updated to support wildcarding of asset names in the rules for the plugin.
       - New documentation has been added to help in troubleshooting PI connection issues.
       - The pi_server and ocs north plugins are deprecated in favour of the newer and more feature rich OMF north plugin. These deprecated plugins cannot be used in north services and are only provided for backward compatibility when run as north tasks. These plugins will be removed in a future release.


    - Bug Fix:

       - The OMF plugin has been updated to better deal with nested data.
       - Some improvements to error handling have been added to the InfluxDB north plugin for version 1.x of InfluxDB.
       - The Python 35 filter stated it used the Python version 3.5 always, in reality it uses whatever Python 3 version is installed on your system. The documentation has been updated to reflect this.
       - Fixed a bug that treated arrays of bytes as if they were strings in the OPC/UA south plugin.
       - The HTTP North C plugin would not correctly shutdown, this effected reconfiguration when run as an always on service. This issue has now been resolved.
       - An issue with the SQLite In Memory storage plugin that caused database locks under high load conditions has been resolved.


v1.9.0
-------

Release Date: 2021-02-19

- **Fledge Core**

    - New Features:

       - Support has been added in the Python north sending process for nested JSON reading payloads.
       - A new section has been added to the documentation to document the process of writing a notification delivery plugin. As part of this documentation a new delivery plugin has also been written which delivers notifications via an MQTT broker.
       - The plugin developers guide has been updated with information regarding installation and debugging of new plugins.
       - The developer documentation has been updated to include details for writing both C++ and Python filter plugins.
       - An always on north service has been added. This compliments the current north task and allows a choice of using scheduled windows to send data north or sending data as soon as it is available.
       - The Python north sending process required the JQ filter information to be mandatory in north plugins. JQ filtering has been deprecated and will be removed in the next major release.
       - Storage plugins may now have configuration options that are controllable via the API and the graphical interface.
       - The ping API call has been enhanced to return the version of the core component of the system.
       - The SQLite storage plugin has been enhanced to distribute readings for multiple assets across multiple databases. This improves the ingest performance and also improves the responsiveness of the system when very large numbers of readings are buffered within the instance.
       - Documentation has been added for configuration of the storage service.


    - Bug Fix:

       - The REST API for the notification service was missing the re-trigger time information for configured notification in the retrieval and update calls. This has now been added.
       - If the SQLite storage plugin is configured to use managed storage Fledge fails to restart. This has been resolved, the SQLite storage service no longer uses the managed option and will ignore it if set.
       - An upgraded version of the HTTPS library has been applied, this solves an issue with large payloads in HTTPS exchanges.
       - A number of Python source files contained incorrect references to the readthedocs page. This has now been resolved.
       - The retrieval of log information was incorrectly including debug log output if the requested level was information and higher. This is now correctly filtered out.
       - If a south plugin generates bad data that can not be inserted into the storage layer, that plugin will buffer the bad data forever and continually attempt to insert it. This causes the queue to build on the south plugin and eventually will exhaust system memory. To prevent this if data can not be inserted for a number of attempts it will be discarded in the south service. This allows the bad data to be dropped and newer, good data to be handled correctly.
       - When a statistics value becomes greater than 2,147,483,648 the storage layer would fail, this has now been fixed.
       - During installation of plugins the user interface would occasionally flag the system as down due to congestion in the API layer. This has now been resolved and the correct status of the system should be reflected.
       - The notification service previously logged errors if no rule/delivery notification plugins had been installed. This is no longer the case.
       - An issue with JSON configuration options that contained escaped strings within the JSON caused the service with the associated configuration to fail to run. This has now been resolved.
       - The Postgres storage engine limited the length of asset codes to 50 characters, this has now been increased to 255 characters.
       - Notifications based on asset names that contain the character '.' in the name would not receive any data. This has now been resolved.

    - Known Issues:

       - Known issues with Postgres storage plugins. During the final testing of the 1.9.0 release a problem has been found with switching to the PostgreSQL storage plugin via the user interface. Until this is resolved switching to PostgreSQL is only supported by manual editing the storage.json as per version 1.8.0. A patch to resolve this is likely to be released in the near future.


- **GUI**

    - New Features:

       - The user interface now shows the retrigger time for a notification.
       - The user interface now supports adding a north service as well as a north task.
       - A new help menu item has been added to the user interface which will cause the readthedocs documentation to be displayed. Also the wizard to add the south and north services has been enhanced to give an option to display the help for the plugins.


    - Bug Fix:

       - The user interface now supports the ability to filter on all severity levels when viewing the system log.


- **Plugins**

    - New Features:

       - The OPC/UA south plugin has been updated to allow the definition of the minimum reporting time between updates. It has also been updated to support subscription to arrays and DATE_TIME type with the OPC/UA server.
       - AWS SiteWise requires the SourceTimestamp to be non-null when reading from an OPC/UA server. This was not always the case with the OPC/UA north plugin and caused issues when ingesting data into SiteWise. This has now been corrected such that SourceTimestamp is correctly set in addition to server timestamp.
       - The HTTP-C north plugin has been updated to support primary and secondary destinations. It will automatically failover to the secondary if the primary becomes unavailable. Fail back will occur either when the secondary becomes unavailable or the plugin is restarted.


    - Bug Fix:

       - An issue with different versions of the libmodbus library prevented the modbus-c plugin building on Moxa gateways, this has now been resolved.
       - An issue with building the MQTT notification plugin on CentOS/RedHat platforms has been resolved. This plugin now builds correctly on those platforms.
       - The modbus plugin has been enhanced to support Modbus over IPv6, also request timeout has been added as a configuration option. There have been improvements to the error handling also.
       - The DNP3 south plugin incorrectly treated all data as strings, this meant it was not easy to process the data with generic plugins. This has now been resolved and data is treated as floating point or integer values.
       - The OMF north plugin previously reported the incorrect version information. This has now been resolved.
       - A memory issue with the python35 filter integration has been resolved.
       - Packaging conflicts between plugins that used the same additional libraries have been resolved to allow both plugins to be installed on the same machine. This issue impacted the plugins that used MQTT as a transport layer.
       - The OPC/UA north plugin did not correctly handle the types for integer data, this has now been resolved.
       - The OPCUA south plugin did not allow subscriptions to integer node ids. This has now been added.
       - A problem with reading multiple modbus input registers into a single value has been resolved in the ModbusC plugin.
       - OPC/UA north nested objects did not always generate unique node IDs in the OPC/UA server. This has now been resolved.


v1.8.2
-------

Release Date: 2020-11-03

- **Fledge Core**

    - Bug Fix:

      - Following the release of a new version of a Python package the 1.8.1 release was no longer installable. This issue is resolved by the 1.8.2 patch release of the core package. All plugins from the 1.8.1 release will continue to work with the 1.8.2 release.


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
       - A new image processing plugin, south human detector, that uses the Google Tensor Flow machine learning platform has been added to the Fledge-iot project.
       - A new Python plugin has been added that can send data north to a Kafka system.
       - A new south plugin has been added for the Dynamic Ratings B100 Electronic Temperature Monitor used for monitoring the condition of electricity transformers.
       - A new plugin has been contributed to the project by Nexcom that implements the SAE J1708 protocol for accessing the ECU's of heavy duty vehicles. 
       - An issue with missing dependencies on the Coral Mendel platform prevent 1.8.0 packages installing correctly without manual intervention. This has now been resolved.
       - The image recognition plugin, south-human-detector, has been updated to work with the Google Coral board running the Mendel Day release of Linux.


    - Bug Fix:

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
       - When a Modbus TCP connection is closed by the remote end we fail to read a value, we then reconnect and move on to read the next value. On device with short timeout values, smaller than the poll interval, we fail the same reading every time and never get a value for that reading. The behaviour has been modified to allow us to retry reading the original value after re-establishing the connection.
       - The OMF north plugin has been updated to support the released version of the OSIsoft EDS product as a destination for data.
       - New functionality has been added to the north data to PI plugin when using PI Web API that allows the location in the PI Server AF hierarchy to be defined. A default location can be set and an override based on the asset name or metadata within the reading. The data may also be placed in multiple locations within the AF hierarchy.
       - A new notification delivery plugin has been added that allows a north task to be triggered to send data for a period of time either side of the notification trigger event. This allows conditional forwarding of large amounts of data when a trigger event occurs.
       - The asset notification delivery plugin has been updated to allow creation of new assets both for notifications that are triggered and/or cleared.
       - The rate filter now allows the termination of sending full rate data either by use of an expression or by specifying a time in milliseconds.
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
       - The Modbus RTU/TCP south plugin is now available on CentOS 7 and RHEL 7.
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


