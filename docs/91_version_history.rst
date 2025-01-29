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

v2.6.0
-------

Release Date: 2024-10-24

- **Fledge Core**

    - New Features:

       - Monitoring of the available space on the disk that holds the SQLite buffer for readings ingested by Fledge has been added. Entries will be written to the error log to predict the expiration of the disk space and also logs when the spaces left available fall below 10% and 5%.
       - Failures to send data north via the north service raise an alert, this is now cleared if the flow of data north later resumes.
       - An issue that could cause high CPU utilisation when a north service was unable to send data to the upstream system has been resolved. The user is also made more aware of failed attempts to send data upstream using the alerting feature. An alert will be created and shown in the GUI status bar.
       - It is now possible to create allow and block lists for IP addresses that are allowed access or explicitly denied access to the API port of the instance.
       - The configuration items within the configuration category now have the ability to limit the user roles that are allowed to update the configuration item.
       - Configuration items can now be given a permission property that can be used to control which user roles have access to the configuration item.
       - Performance monitors have been improved.
       - A new section relating to all aspects of monitoring within Fledge has been added to the documentation.
       - The tuning documentation has been updated to discuss the use of the configuration cache size tuning parameter and to add a discussion on tuning the log level for the various services.

    - Bug Fix:

       - An issue that caused incorrect payloads to be sent north when choosing the audit log as the data source has been resolved.
       - An issue that incorrectly prevented some authorised users from executing a control endpoint has been resolved.
       - An issue with backup and restore when using Postgres as the storage engine to store the configuration data has been resolved.
       - The manual purge, in the developer features of the user interface, was not working for assets containing ' #',  ‘+' or '&’ characters in asset name.
       - An issue with north services that have been misconfigured not cleanly shutting down has been resolved.
       - An issue that could cause a backup file to not download has been resolved.
       - An issue that could allow an unauthorised user to change the password of another user has been resolved.
       - After restart of Fledge, the sent count in the Fledge GUI dashboard would increase by few readings after every restart of Fledge, even if no south plugins were running. This has been fixed. This was an error in the increment of the counter; there were never any additional readings sent.
       - An issue with an incorrect audit entry being created when adding new properties to a configuration item has been resolved.
       - A security issue that could allow one user to see the profile of another has been resolved.
       - Users now need to have administration permissions to see the user names and roles of other users.
       - The handling of errors during pipeline creation has been enhanced to give better reporting of filter plugin exceptions.
       - The notification service has been updated to allow sub-second retriever times for notifications to be specified.
       - The documentation for deleting users via the REST API has been corrected.


- **GUI**

    - New Features:

       - The rendering of lists in the configuration options has been improved.
       - The ordering of the tabs in the configuration user interface is no longer alphabetical but controlled by the configuration category itself.
       - The user interface now hides configuration options the user does not have permission to change.
       - The rendering of the developer menu has been brought into line with other sub-menu rendering.


    - Bug Fix:

       - An issue with the user interface incorrectly displaying a timestamp has been resolved.
       - An issue with list type configuration items occasionally not rendering correctly for filters has been resolved.
       - An issue related to improper length validation for certain entries in the configuration items has been resolved.
       - An issue with forcible session disconnection sometimes failing has been resolved.
       - The performance related to management of services and plugins has been improved.
       - An issue that prevents export of persisted data in developer mode has been resolved.
       - An issue that prevented deletion of persisted data for plugins in developer mode has been resolved.
       - An issue with the filter plugin that involved underscores in the name has been resolved.


- **Plugins**

    - New Features:

       - fledge-filter-asset now supports to allow regular expressions to be used in the asset name to match when applying the filter.
       - fledge-filter-delta has been enhanced to give greater control over the action when one or more datapoints in an asset reading are detected as changing.
       - fledge-notify-operation now supports data substitution as with the other control-related notification delivery plugins.
       - fledge-north-OMF *action* code in the HTTP header is normally set to *update* for OMF Data messages. This causes old values to be updated if the timestamps match and new data to be properly compressed by the PI Data Archive.
         If the AVEVA PI Buffer Subsystem is configured, however, the *update* action code is converted to an internal PI storage mode that causes new data to bypass compression, which can result in unnecessarily storing too many data values. To workaround this issue, the OMF North plugin now allows you to change the OMF Data action code to *create*. This should only be done when the AVEVA PI Buffer Subsystem is configured.
       - fledge-south-s2opcua now supports for the OPC UA Data Change Filter has been added. This filter type is defined in the `OPC UA Specification, Part 4, Section 7.22.2 <https://reference.opcfoundation.org/Core/Part4/v105/docs/7.22.2>`_. The Data Change Filter allows OPC UA clients (such as this plugin) to request that the OPC UA server send data value updates only if the server's data values have changed significantly. With careful tuning, you can reduce the data traffic from OPC UA server to the client without significant loss of fidelity. This plugin has been upgraded to use Systerel's `S2OPC Toolkit Version 1.5.0 <https://gitlab.com/systerel/S2OPC/-/releases/S2OPC_Toolkit_1.5.0>`_.

    - Bug Fix:

       - An issue that could cause a crash during purge operations has been resolved.
       - fledge-south-modbusc plugin that could cause it to fail if the IP address of the MODBUS device was changed incorrectly and then changed back to the correct address has been resolved.
       - fledge-south-mqtt-sparkplug now supports various data types, including string, integer, float and boolean.
       - fledge-south-randomwalk has been improved to give a more random result.
       - fledge-south-s2opcua would sometimes fail to connect to an OPC UA server with a large number of available endpoints on a distant or noisy network. This has been fixed.


v2.5.0
-------

Release Date: 2024-06-26

- **Fledge Core**

    - New Features:

       - A new parameter has been added to the storage service to configure the number of threads that will be used to interact with the buffered reading data. This limits that impact on heavily loaded systems and also allows for the threads to be pre-created, which slightly reduces the latency.
       - A new tuning option has been added to the core that tunes the size of the cache maintained by the configuration manager. Increasing this cache size can speed up the startup of the system when large numbers of services are used within the system.
       - A new tuning option has been added to the north service to control the frequency of updating the stream position when writing data to the north. More details are available in the tuning section of the documentation.
       - A new tuning option has been added to the north service that allows the number of buffers that are prefetched to be tuned.
       - A small performance enhancement has been made in the south service such that the rate of storing statistics is not dependent on the ingest rate of the service. This will improve the performance of south services with high ingest rates.
       - A performance enhancement has been added to all SQLite storage plugins that results in higher throughput and lower latency in all cases when using SQLite as a storage engine.
       - The storage performance monitors have been updated to include the table name in the monitor name. This allows tracking of which tables are being heavily used within the system.
       - A new security option has been added to allow for a password policy to be set. This policy defines characters that must appear within a user password.
       - Password encryption has been made more secure.
       - Some changes have been done to the way the API handles passwords to make them more secure.
       - The system now tracks failed login attempts and can block accounts that have excessive failed attempts to login.
       - A new security feature has been added to disconnect idle sessions after a configurable time.
       - Support for adding list names to configuration category items of type list has been added.
       - Support bundles and backups have been updated to require extra privileges to access.
       - The documentation on securing Fledge has been updated.
       - The documentation for the SQLite storage plugin has been improved and some duplication removed.
       - The configuration category documentation has been updated to include more explanation and examples of the use of the various list type configuration items.
       - Documentation has been added to the 'Tuning Fledge' section to describe the performance counters in the storage layer and also give some general tips on the subject of using the performance counters to tune the Fledge installation.


    - Bug Fix:

       - A typo in the statistics description for “Readings Sent North” has been fixed.
       - An issue that may occasionally cause the storage service to fail during purge when using the default SQLite storage engine for readings data storage has been resolved.
       - A problem with integer overflow in the SQLite storage engine has been resolved.
       - An issue with one of the API entry points that could allow for command injection into the underlying operating system has been resolved.


- **GUI**

    - New Features:

       - An option to use the flow editor interface for notifications has been added.
       - An option has been added to the graph display to scroll to the latest readings available.
       - A facility to read a JSON configuration item from a file and insert the contents into a configuration item has been added to the user interface.
       - Support has been added to the GUI for key/value lists in configuration items.
       - The ability to create and manage backups has become a privileged operation. Likewise support bundles can only be created by administrators.
       - The user management screen now shows if a user has been blocked due to excessive failed login attempts.
       - The documentation on viewing data has been updated in line with a number of recent changes to the user interface.
       

    - Bug Fix:

       - A missing health icon in the north service flow editor has been added.
       - An issue when deleting a disabled notification service could result in an error has been resolved.
       - An issue that could result in two identical audit logs when deleting a filter from a pipeline has been resolved.
       - The north flow editor page was not showing branches in pipelines, this has now been resolved.


- **Services & Plugins**

    - New Features:

       - The build mechanism has been updated to support profiled builds.
       - fledge-north-opcua: In the hierarchy map, forward-slash-separated string tokens in the meta-data and the Asset Name are now parsed and used to construct an object hierarchy in the OPC UA Server's Address Space. Since some South plugins and filters send path information to Fledge that is split between a path Datapoint and the Asset Name, path segments found in the Asset Name will be added to the end of the path Datapoint. The plugin supports the entire path being present in the Asset Name.
       - OMF North plugin: The default naming convention of PI tags created is Asset name and Datapoint name separated by a dot (.) delimiter. It is now possible to choose any single character as the delimiter except characters that are not allowed in OMF field names.
       - Support has been added to automatically detect new storage engines upon restart of Fledge.


    - Bug Fix:

       - A memory leak in the scale filter plugin has been fixed.
       - A Python compatibility issue with the fledge-south-s7-python plugin has been resolved.
       - An issue with reordering filters in a control pipeline has been resolved.
       - An issue that could cause the failure of the service if configuring a regular expression in the fledge-filter-omfhint with an invalid regular expression has been resolved.
       - A problem that could cause the dispatcher service to fail when deleting a filter from a control pipeline has been resolved.
       - A problem that could cause the control dispatcher to become unresponsive when adding a filter to an active control pipeline has been resolved.
       - An issue that meant the notification service could not find the control dispatcher if the control dispatcher was started with a non-default name has now been resolved.


v2.4.0
-------

Release Date: 2024-04-10

- **Fledge Core**

    - New Features:

       - A new feature has been added that allows for internal alerts to be raised. These are used to inform users of any issue internally that may require attention, they are not related to specific data that is flowing through the Fledge data pipelines. Examples of alerts that may be raised are that updates to the software are available, a service is repeatedly failing or an exceptional issue has occurred.
       - A new task (update checker) has been added that will run periodically and raise an alert if there are software updates available.
       - The internal service monitor has been updated to use the new alerts mechanism to alert a user if services are failing.
       - A new storage configuration option has been added that allows the server request timeout value to be modified.
       - The ability to tune the cache flushing frequency of the asset tracker has been added to the advanced configuration options of the south and north services.
       - The reporting of south service send latency has been updated to give more detail regarding continue send latency issues.
       - A new tuning parameter has been added to the purge process to control the number of readings purged within single blocks. This can be used to tune the intention between the purge process and the ingestion of new data in highly loaded systems.
       - A new list type has been added to the types supported in the configuration category. This allows for improved configuration interactions.
       - Support has been added in the C++ configuration manager code to allow for the new list, key/value list and object list types in configuration categories. Also some convenience functions have been added for use by plugins that wish to traverse the lists.
       - In the hierarchy map, forward-slash-separated string tokens in the meta-data are now parsed and used to construct an object hierarchy in the OPC UA Server's Address Space.
       - The scheduler has been enhanced to provide the capability to order the startup of services when Fledge is started.
       - A performance improvement, courtesy of a community member, for the JSON escaping code has been added. This improves performance of the PostgreSQL storage plugin and other areas of the system.
       - A new section has been added to the documentation that describes how storage plugins are built.
       - The plugin developers guide has been updated with information and examples of the new list handling facilities added to configuration items within Fledge.
       - The tuning section of the documentation has been updated to include details of the service startup ordering enhancement.
       - The plugin documentation has been updated to include cross referencing between plugins. A new See Also section will be included that will link the set to other plugins that might be useful or relate to the plugin that is being viewed.
       - The plugin developers guide has been updated to add some additional guidance to the developer as to how to decide if features should be added to a plugin or not and also to document common problems that cause problems with plugins.
       - Documentation that describes what firewall settings are needed to install Fledge has been added to the quick start guide.


    - Bug Fix:

       - An issue that prevented configuration categories items called messages has been resolved.
       - An issue that could cause data to be repeated in a north service when using a pipeline in the north that adds new readings to the pipeline has been resolved.
       - An issue that could cause the order of filters in a control pipeline API to be modified has been fixed.
       - An issue that could result in series that are already installed being shown in the list of services available to be installed has been resolved.
       - An issue that could cause some north plugins to fail following a restart when using the SQLite in-memory storage plugin has been fixed.      
       - An issue that could prevent a plugin being updated in some circumstances has been resolved.
       - An issue requiring a restart before the change in log level for the storage service took effect has been resolved.
       - An issue causing the database to potentially not initialize correctly when switching the readings plugin from SQLite to PostgreSQL has been resolved.
       - An issue in the control pipeline API related to the type of one of the parameters of the pipeline has been resolved. This issue could manifest itself as an inability to edit a control pipeline.
       - The return type of plugin_shutdown was incorrectly documented in the plugin developers guide for north plugins. This has now been resolved.


- **GUI**

    - New Features:

       - A new page has been added for managing additional services within an instance.
       - Support for entering simple lists for configuration items has been added.
       - Support has been added for manipulating key/value lists using the new available list configuration type that is available.
       - Navigation buttons have been added to the tabs in the south and north services to facilitate easier navigation between tabs.
       - A preview of the new flow editor for the north side has been added. This may be enabled via the GUI settings page.
       - The GUI now shows the internal alerts via an icon in the navigation bar at the top of the screen.


    - Bug Fix:

       - An issue with creating an operation in a control script with no parameters in the GUI has been resolved.
       - An issue with the Next button not being enabled when changing the name of a service in the service creation wizard has been resolved.
       - An issue that could result in a filter not being added to a control pipeline when the user does not click on the see button has been addressed by adding a check before navigating off the page.
       - An issue that could result in the JSON code editor being incorrectly displayed for non-JSON code has been resolved.
       - An issue with the visibility of the last item on the side menu when scrolling in a small window has been resolved.


- **Services & Plugins**

    - New Features:
       
       - Improvements have been made to the buffering strategy of the OMF north plugin to reduce the overhead in creating outgoing OMF messages.
       - The control pipelines mechanism has been enhanced to allow pipelines to change the name of the operation that is performed as well as the parameters.
       - The documentation of the expression filter has been updated to document the restriction on asset and datapoint names.


    - Bug Fix:

       - An issue with the dynamic reconfiguration of filters in control pipelines has been resolved.
       - An issue that could cause the control dispatcher service to fail when changing the destination of a control pipeline has been resolved.
       - An issue with the control dispatcher that prevents operations with no parameters from being correctly passed via control pipelines has been resolved.
       - An issue in the control dispatcher that could cause a crash if a control pipeline completely removed the request has now been resolved.
       - An issue that could cause an error to be logged when installing the control dispatcher has been resolved. The error did not prevent the dispatcher from executing.
       - An issue when using the PostgreSQL storage plugin and data containing double quotes within JSON data has been resolved.
       - An issue that could cause an error in the south plugin written in Python that supports control operations has been resolved.
       - A memory consumption issue in the fledge-filter-asset when using the flatten option has been resolved.
       - The fledge-filter-asset issue causing deadlock in pipelines with two instances has been resolved.
       - An issue that limited the number of variables the fledge-south-s2opcua plugin could subscribed to has been resolved.
       - An issue that could result in the sent count being incorrectly incremented when using the fledge-north-kafka (C based) plugin has been resolved.
       - An issue that could cause excessive messages regarding connection loss and regain to be raised in the OMF north plugin has been resolved.
       - An issue that caused the fledge-north-kafka (C based) plugin to fetch data when it was disabled has been resolved.
       - If you set the User Authentication Policy to username, you must select a Security Policy other than None to communicate with the OPC UA Server. Allowing username authentication with None would mean that usernames and passwords would be passed from the plugin to the server as clear text which is a serious security risk. This is explained in the `OPC UA Specification <https://reference.opcfoundation.org/Core/Part4/v104/docs/7.36.4>`_. In addition, OPC UA defines a Security Policy for a "UserIdentityToken". When configuring the fledge-south-s2opcua plugin, the Security Policy selected in your configuration must match a supported "UserIdentityToken" Security Policy.  To help troubleshoot configuration problems, log messages for the endpoint search have been improved. The documentation includes a new section called "Username Authentication".
       - If a datapoint or asset name contains a reserved mathematical symbol then the fledge-filter-expression plugin was previously unable to use this as a variable in an expression. A mechanism has been added to allow these names.
       - The Notification service would create Rule and Delivery support objects even if the notification was disabled. When the notification was later enabled, the original objects would remain. This has been fixed.
       - If the OMF North plugin gets an exception when POSTing data to the PI Web API, the plugin would declare the connection to PI broken when it wasn't. This would result in endless connection loss and reconnection messages. This has been fixed. The plugin will now ping the PI Web API every 60 seconds and will determine that connection has been lost only if this ping fails. The OMFHint LegacyType has been deprecated because a Container cannot be changed after it is created in the PI System. This means there is no way to process the LegacyType hint when readings are processed. If the LegacyType hint appears in any reading, a warning message will be written saying that this hint type has been deprecated.
       - This fix applies when configuring OMF North to create an Asset Framework (AF) structure. The first time an AF Element holding an AF Attribute pointing to a PI Point (i.e. the Container) is created, it will appear in Asset Framework as a normal AF Element. If the path is then changed using an "AFLocation hint", a reference to the AF Element should appear in the hint's location. The original AF Element's location should remain unchanged. This feature was not working correctly but has been fixed. Before this fix, the hint's path would be created as expected but no reference to the original data location was created.
       - The storage service with the SQLite in-memory plugin does consume large amounts of memory while running at higher data rates. Analysis has determined this is not caused by a memory leak but rather by legitimately storing large amounts of data in memory while operating. The reason for the high load on the storage service appears to be database purging but this is a subject for further study.
       - An issue in the control pipeline documentation that stated that services could only be the source of control pipelines has been fixed to now show that they may be the source or the destination.
       - It is not possible to change the numeric data type of OMF Container (which maps to a PI Point) after it has been created. This means it is not possible to enable or disable an integer OMFHint or change the numeric data type in the Fledge GUI after the Container has been created. It is possible to manually correct the problem if it is necessary. OMF North plugin documentation has been updated with the procedure.


v2.3.0
-------

Release Date: 2023-12-28

- **Fledge Core**

    - New Features:

       - A new REST API has been added to the public API to allow performance counters to be fetched and reset. This API is intended for diagnostic purposes only.
       - Improvements have been made to the way load issues on the storage service are logged. 
       - Documentation has been added that describes how to extend the API to include custom URLs for executing control functions. This documentation also shows how these are then called using the graphical user interface.

    - Bug Fix:

       - An issue with the PostgreSQL storage plugin when very large numbers of readings are ingested, more than 4294967296, has now been resolved.
       - An issue with services shutting down rather than restarting when they fail to get a valid bearer token has been resolved.
       - The user interface for creating write API endpoints was incorrectly requiring both a constant and a variable when only one is required. This is now resolved.
       - A problem that meant parameters to set point control operations were not correctly sent to south plugins written in Python has been resolved.


- **GUI**

    - New Features:

       - The user interface has been upgraded to use Angular version 16.
       - The configuration section of the user interface that allows for instance wide configuration has been improved with a single tree navigation item and improved visual feedback.
       - A link to the documentation has been added to the Control API pages of the user interface.


    - Bug Fix:

       - An issue that could cause some datapoint to display incorrectly in the user interface graph when multiple assets are displayed and those assets have data points with the same name in both assets has been resolved.
       - An issue in the user interface that meant exporting data as a CSV file created incorrect files if any of the data point names contained a comma has been fixed.
       - An issue with the user interface not always correctly showing the information for the dispatcher service has been resolved.
       - A broken link to the documentation in the control pipeline user interface page of the user interface has been fixed.


- **Services & Plugins**

    - New Features:

       - The benchmark south plugin has been enhanced to increase the load that can be placed during testing.
       - The fldege-south-s2opcua south plugin has been enhanced to allow filtering of nodes using regular expressions on the Browse Name of the nodes.
       - The OMF north plugin has been updated to improve both the time and space efficiency of the lookup data used to map to PI Server objects.
       - OMF North plugin documentation has been updated to show which version of the OMF specification the plugin will adopt when communicating with different versions of AVEVA products: PI Web API, Edge Data Store (EDS) and AVEVA Data Hub (ADH).


    - Bug Fix:

       - A memory leak in the SQLite in-memory storage plugin has been resolved.
       - A memory leak in the OMF north plugin has been resolved.
       - An issue that could cause data to fail to send using the OMF plugin when the names of data points contain special characters has now been resolved.
       - When the "Send full structure" configuration boolean was false, OMF North would create an AF structure anyways. All AF Elements were at the root of the AF database, with every AF Element having a single AF Attribute mapped to a PI Point. Creation of this AF structure would take a long time for large databases which would lead to PI Web API POST timeouts. This has been fixed. If the configuration boolean is false, OMF North will create PI Points only. In the configuration page, Send full structure has been renamed to "Create AF Structure".
       - The OMF North plugin was unable to connect to AVEVA Data Hub (ADH) and OSIsoft Cloud Services (OCS) endpoints. This has been fixed.
       - An issue with using an OMF Hint that defines a specific name to use with a tag has been resolved. The issue would show itself as the data not being sent to PI or ADH in some circumstances.
       - An issue that meant some OPC UA nodes stored in the root of the hierarchy were not correctly ingested in the fldege-south-s2opcua south plugin has been resolved.
       - The SQLite storage plugin had an issue that caused it to create overflow tables multiple times. This was not a problem in itself, but did cause the database to become locked for excessive periods of time, creating contention and delays for data ingestions in progress at the time.
       - A problem that, in rare circumstances, could result in data being added to the incorrect asset in the SQLite plugin has been resolved. 
       - An issue with assets containing bracket characters not being stored in the PostgreSQL storage plugin has been resolved.
       - An issue with string type parameters to control operations having extra pairs of quotes added has been resolved.
       - A problem that caused the dispatcher service to log messages regarding incorrect bearer tokens has been resolved.
       - The control dispatcher service was previously advertising itself before it had completed initialisation. This meant that a request could be received when it was partially configured, resulting in a crash of the service. Registration now takes place only once the service is completely ready to accept requests.
       - The control dispatcher was not always using the correct source information when looking for matching pipelines. This has now been resolved.
       - Control pipelines were previously still being executed if the entire pipeline was disabled, this has now been resolved.


v2.2.0
-------

Release Date: 2023-10-17

- **Fledge Core**

    - New Features:

       - New audit logs have been added to reflect the creation, update and deletion of access control lists.
       - New public API Entry Points have been added to allow for the creation and manipulation of control pipelines.
       - A new user role has been added for those users able to update the control features of the platform.
       - A new tuning parameter has been added to the PostgreSQL storage plugin to allow the maximum number of readings inserted into the database in a single insert to be limited. This is useful when high data rates or large bursts of readings are received as it limits the memory consumption of the plugin and reduces the lock contention on the database.
       - The asset tracker component has been optimized in order to improve the ingress and egress performance of Fledge.
       - The mechanism used by the south and north services to interact with the audit log has been optimized. This improves the ingress and egress performance of the product at the cost of a small delay before the audit log is updated.
       - A number of optimizations have been made to improve the performance of Python filters within a pipeline.
       - A number of optimizations to the SQLite in-memory storage plugin and the SQLiteLB storage plugin have been added that increase the rate at which readings can be stored with these plugins.
       - The support bundle creation process has been updated to include any performance counters available in the system.
       - The ability to monitor performance counters has been added to Fledge. The South and North services now offer performance counters that can be captured by the system. These are designed to provide information useful for tuning the respective services.
       - The process used to extract log information from the system logs has been updated to improve performance and reduce the system overhead required to extract log data.
       - A number of changes have been made to improve the performance of sending data north from the system.
       - The performance of the statistics history task has been improved. It now makes fewer calls to the storage subsystem, improving the overall system performance.
       - The performance of the asset tracker system has been improved, resulting in an improvement in the ingress performance of the system.
       - Changes have been made to the purge process in the SQLiteLB and SQLite in-memory plugins in order to improve performance.       
       - The audit log entries have been updated to include more information when schedules are updated.
       - Audit logs have been added to the user API of the public REST interface.
       - The plugin developers guide has been updated to include the mechanism for adding audit trail entries from C++ plugins.
       - Plugins that run within the south and north services and north tasks now have access to the audit logging system.
       - The public API has been updated to include the ability to make control requests.
       - The public API of the system has been updated to allow selection of readings from the storage buffer for given time intervals.      
       - The public API that is used to retrieve reading data from the storage layer has been updated to allow data for multiple assets to be retrieved in a single call.
       - The SQLite in-memory storage plugin now has an option that allows the data to be persisted when shutting the system down and reloaded on startup.
       - The SQLite storage plugins have been updated to improve the error reporting around database contention issues.
       - A change has been made to the configuration of the storage plugin such that rather than having to type correct names for storage plugins the user may now select the plugins to use from a drop down list. Note however that the system must still be restarted for the new storage plugin to take effect.
       - The storage service has been updated to allow other services to subscribe the notifications of inserts into the generic tables.
       - A change has been made to prevent the schedules used to start services from being renamed as this could cause the services to fail.
       - The default interval for running the purge process has been reduced, the purge process will now run every 10 minutes. This change only affects new installations, the purge process will run as before on systems that are upgraded.       
       - The ingestion of data from asynchronous south services paid no attention to the advanced configuration option "Throttle". This meant that very fast asynchronous south plugins could build extremely large queues of data within the south service, using system resources and taking a long time to shutdown. This has now been rectified, with asynchronous south services now subject to flow control if the "Throttle" option is set for the service. Unconstrained input is still available if the "Throttle" option is not checked.
       - The south plugin now supports three different modes of polling. Polling at fixed intervals from the time started, polling at fixed times or polling on demand via the control mechanisms.
       - Support has been added to allow filters to ingest passed data onwards during a shutdown of the filter. This allows any buffered data to be flushed to the next filter in the pipeline.
       - A numeric list data type has been added to the reading ingestion code of the system.
       - A Python package, used by the system, found to have a security vulnerability. This has been updated.
       - The format of Python traceback has been improved to use multiple lines within the log. This makes the trace easier to understand and prevents the truncation that can occur.
       - The setting of log levels from a service is now also reflected in any Python code loaded by the service.
       - The reporting of issues related to failure to load plugins has been improved.
       - When upgrading the version of a plugin any new configuration items are added to the relevant configuration categories. However the operation was not correctly reported as a configuration change in the audit log. This behavior has now been corrected.
       - An issue which could occasionally result in the bearer token used for authentication between the various services expiring before the completion of the renewal process has been resolved. This could result in the failure of services to communicate with each other.
       - The configuration category C++ API has been enhanced in the retrieval and setting of all the attributes of a configuration item.       
       - The support bundle has been updated to include a list of the Python packages installed on the machine.
       - The documentation regarding handling and updating certificates used for authentication has been updated. 
       - Added documentation for the performance counters in the tuning guide.


    - Bug Fix:

       - An issue with the SQLite in-memory and the SQLiteLB storage plugins that could result in incorrect data being stored has been resolved.
       - An erroneous message was being produced when starting the system using the SQLite in-memory storage plugin. This has now been resolved.
       - Support has been improved for switching between different storage plugins that allows for correct schema creation when using different SQLite plugin variants for configuration and readings storage.
       - An issue that could cause health metrics to not be correctly returned when using the Postgres storage engine has been resolved.
       - An issue in one of the storage plugins that caused spurious warnings to appear in the logs during a backup has been resolved.
       - A memory leak in one of the storage plugins has been fixed. This caused the storage service to consume large amounts of memory over time which could result in the operating system killing the service.
       - An update has been done to the default SQLite storage plugin to enable it to handle a large number of distinct asset codes in the readings. Previously the plugin was limited in the number of assets it could support. When the number of asset codes gets large the performance of the plugin will be reduced slightly, however it will continue to ingest data.
       - An issue with memory usage in Python plugins used in south services has been resolved.
       - A number of issues regarding the usage of memory have been resolved, including some small memory leaks. The overall memory footprint of north services should also be reduced in some circumstances. 
       - An issue that causes log messages to not be recorded has been resolved.
       - An issue that could cause the statistics to be displayed with a timestamp in the wrong timezone has been resolved.
       - A bug in the statistics rate API that would result in incorrect data being returned has been fixed.
       - An empty statistics entry would erroneously be added for an asset or a service if the advanced parameter to control the statistics was modified from the default before the service was started. This has now been resolved.
       - A problem with statistics counter overflow that could cause a crash in the statistics collector has been resolved.
       - An issue that caused the retrieval of system logs for services with white space in the name of the service has been resolved.
       - The control dispatcher now has access to the audit logging system.
       - An issue that required the north service to be restarted if the source of data to send was changed in a running service has been resolved. Changing the data source no longer requires a restart of the north service.
       - An issue that could sometimes cause a running north service to fail if the configuration for that service is updated has been resolved.
       - A problem that prevents an updated service from restarting after an upgrade if HTTPS is used for the interface between services has been resolved.
       - An issue that limited the update of additional services to just the notification service has been resolved. The update mechanism can now update any service that is added to the base system installation.       
       - The Python south plugin mechanism has been updated to fix an issue with ingestion of nested data point values.       
       - When switching a south plugin from a slow poll rate to a faster one the new poll rate does not take effect until the end of the current poll cycle. This could be a very long time. This has now been changed so that the south service will take the new poll rate as soon as possible rather than wait for the end of the current poll cycle.
       - A bug that prevented notification rules from being executed for readings with asset codes starting with numeric values has been resolved.
       - The data sent to notification rules that register for audit information has been updated to include the complete audit record. This allows for notification rules to be written that trigger on the particular auditable operations within the system.
       - The notification service would sometimes shutdown without removing all of the subscriptions it holds with the storage service. This could cause issues for the storage service. Subscriptions are now correctly removed.
       - The command line interface to view the status of the system has been updated to correctly show the statistics history collection task when it is running.      
       - The issue of incorrect timestamps in reading graphs due to inconsistent timezones in API calls has been resolved. All API calls now return timestamps in UTC unless explicitly specified in the response.
       - An issue with the code update mechanism that could cause multiple updates to occur has been resolved. Only a single update should be executed and then the flag allowing for updates to be applied should be removed. This prevents the update mechanism triggering on each restart of the system.
       - A problem that prevented the fledge-south-modbus plugin from being updated in the same way as other plugins has been resolved.
       - An issue with trying to create a new user that shares the same user name with a previous user that was removed from the system failing has been resolved.
       - A problem with converting very long integers from JSON has been resolved. This would have manifested itself as a crash when handling datapoints that contain 64 bit integers above a certain value.     
       - An update has been made to prevent the creation of service with empty service name.


- **GUI**

    - New Features:

       - New controls have been added in the menu pane of the GUI to allow nested commands to be collapsed or expanded, resulting in a smaller menu display.
       - A new user interface option has been added to the control menu to create control pipelines.
       - The user interface has been updated such that if the backend system is not available then the user interface components are made non-interactive & blur.
       - The interface for updating the filters has been improved when multiple filters are being updated at once.
       - New controls have been added to the asset browser to pause the automatic refresh of the data and to allow shuffling back and forth along the timeline.
       - The ability to move backwards and forwards in the timeline of the asset browser graph has been added.
       - The facility that pauses the automatic update of the asset browser graph has been added.
       - The ability to graph multiple readings on a single graph has been added to the asset browser graph.
       - A facility to allow a user to define the default time duration shown in the asset browser graph has been added to the user interface settings page.
       - The date format has been made more flexible in the asset and readings graph.
       - The display of image attributes for image type data points has been added to the latest reading display. 
       - The ability to select an area on the graph shown in the asset browser and zoom into the time period defined by that area has been added.
       - The reading graph time granularity has been improved in the asset browser.       


    - Bug Fix:

       - The user interface for configuring plugins has been improved to make it more obvious when mandatory items are missing.
       - An issue that allowed view users to update configuration when logged in using certificate based authentication has been resolved.
       - An issue which prevented the file upload/value update for script type configuration item, unless the name also was script has been resolved.
       - An issue with editing large scripts or JSON items in the configuration has been resolved.
       - An issue that caused services with quotes in the name to disappear from the user interface has been resolved.
       - The latest reading display issue that resulted in non image data not being shown when one or more image data points are in the reading has been resolved.
       - A text wrapping issue in the system log viewer has been resolved.
       - An occasional error that appeared on the Control Script and ACL pages has been resolved.


- **Services & Plugins**

    - New Features:

       - An update has been done to the OMF north plugin to correctly handle the set of reserved characters in PI tag names when using the new linked data method for inserting data in the PI Server.
       - The OMF north plugin has been updated to make an additional test for the server hostname when it is configured. This will give clearer feedback in the error log if a bad hostname is entered or the hostname can not be resolved. This will also confirm that IP addresses entered are in the correct format.
       - Some enhancements have been made to the OMF north plugin to improve the performance when there are large numbers of distinct assets to send to the PI Server.
       - There have been improvements to the OMF north plugin to prevent an issue that could cause the plugin to stop sending data if the type of an individual datapoint changed repeatedly between integer and floating point values. The logging of the plugin has also been improved, with clearer messages and less repetition of error conditions that persist for long periods.
       - Support for multiple data centers for OSIsoft Cloud Services (OCS) has been added in the OMF north plugin. OCS is hosted in the US-West and EU-West regions.
       - When processing data updates from the PI Server at high rates, the PI Server Update Manager queue might overflow. This is caused by the PI Server not retrieving data updates until all registrations were complete. To address this, the PI Server South plugin has been updated to interleave registration and retrieval of data updates so that data retrieval begins immediately.
       - Macro substitution has been added to the OMFHint filter allowing the contents of datapoints and metadata to be incorporated into the values of the OMF Hint, for example in the Asset Framework location can now include data read from the data source in the location.
       - The fledge-filter-asset has been updated to allow it to split assets into multiple assets, with the different data points in the original asset being assigned to one or more of the new assets created.
       - The fledge-filter-asset has been enhanced to allow it to flatten a complex asset structure. This allows nested data to be moved to the root level of the asset.
       - The fledge-filter-asset has been enhanced to allow it to remove data points from readings.
       - Windowed averages in the notification service preserve the type of the input data when creating the averages. This does not work well for integer values and has been changed such that integer values are promoted to floating point when using windowed averages for notification rule input.
       - The notification mechanism has been updated to accept raw statistics and statistics rates as an input for notification rules. This allows alerts to be raised for pipeline flows and other internal tasks that generate statistics.
       - Notifications can now register for audit log entries to be sent to notification rules. This allows notification to be made based on internal state changes of the system.
       - The fledge-north-opcuaclient has been updated to support multiple values in a single write.
       - The fledge-north-opcuaclient plugin has been updated to support OPC UA security mode and security policies.
       - The fledge-north-httpc plugin now supports sending audit log data as well as readings and statistics.
       - The fledge-north-kafka plugin has been updated to allow for username and password authentication to be supplied when connecting to the Kafka server.
       - Compression functionality has been added to the fledge-north-kafka.
       - The average and watchdog rules have been updated to allow selection of data sources other than the readings to be sent to the rules.
       - The fledge-notify-email notification delivery plugin has been updated to hide the password from view and also allow custom alert messages to be created.
       - Some devices were not compatible with the optimized block reading of registers performed by the fledge-south-modbus plugin. The plugin has been updated to provide controls that can determine how it reads data from the modbus device. This allows single register reads, single object reads and the current optimized block reads.
       - The fledge-south-s2opcua now supports an optional datapoint in its Readings that shows the full path of the OPC UA Variable in the server's namespace. It has also to support large numbers of Monitored Items.
       - The option to configure and use a username and password for authentication to the MQTT broker has been added to the fledge-south-mqtt plugin.
       - The North service could crash if it retrieved invalid JSON while processing a reconfiguration request. This was addressed by adding an exception handler to prevent the crash.
       - The audit logger has been made available to plugins running within the notification service.
       - The notification service documentation has been updated to include examples of notifications based on statistics and audit logs.
       - Documentation of the AF Location OMFHint in the OMF North plugin page has been updated to include an outline of differences in behaviors between Complex Types and the new Linked Types configuration.
       - The documentation of the OMF North plugin has been updated to conform with the latest look and feel of the configuration user interface. It also contains notes regarding the use of complex types versus the OMF 1.2 linked types.
       - The documentation for the asset filter has been improved to include more examples and explanations for the various uses of the plugin and to include all the different operations that can be performed with the filter.
       - The documentation for the control notification plugin has been updated to include examples for all destinations of control requests.


    - Bug Fix:

       - The OMF North plugin that is used to send Data to the AVEVA PI Server has been updated to improve the performance of the plugin.
       - The OMF North plugin sent basic data type definitions to AVEVA Data Hub (ADH) that could not be processed resulting in a loss of all time series data. This has been fixed.
       - Recent changes in the OMF North plugin caused the data streaming to the Edge Data Store (EDS) to fail. This has been fixed. The fix has been tested with EDS 2020 (Version 1.0.0.609).
       - The fledge-north-opcuaclient plugin has been updated to support higher data transfer rates.
       - An issue with the fledge-south-s2opcua that allowed a negative value to be entered for the minimum reporting interval has been resolved. The plugin has also been updated to use the new tab format for configuration item grouping.
       - An issue with NULL string data being returned from OPC UA servers has been resolved. NULL strings will not be represented in the readings, no data point will be created for the NULL string.
       - The fledge-south-s2opcua plugin would become unresponsive if the OPC UA server was unavailable or if the server URL was incorrect. The only way to stop the plugin in this state was to shut down Fledge. This has been fixed.
       - An issue with fledge-notify-setpoint plugin to control operations occurring before a south plugin is fully ready has been resolved.
       - An issue with reconfiguring a fledge-north-kafka plugin has been resolved, this now behaves correctly in all cases.
       - An issue with sending data to Kafka that included image data points has been resolved. There is no support in Kafka for images and they will be removed while allowing the remainder of the data to be sent to Kafka.
       - An issue with the fledge-south-modbustcp & S7 plugins which caused the polling to fail has been resolved.
       - A problem with the fledge-south-j1708 & fledge-south-j1939 plugins that caused them to fail if added disabled and then later enabling them has been resolved.
       - A problem that caused the fledge-north-azure-iot plugin to fail to send data has been corrected.
       - A product version check was made incorrectly if the OMF endpoint type was not PI Web API. This has been fixed.       
       - The notification sent an audit log entry was created even when the delivery failed. It should only be created on successful delivery, this has been fixed.
       - A problem with the fledge-notify-asset delivery plugin that would sometimes result in stopping the notification service and also it was not previously creating entries in the asset tracker have been resolved.
       - An issue that could cause notification to not trigger correctly when used with conditional forwarding has been resolved.
       - An issue with using multiple Python based plugins in a north conditional forwarding pipeline has been resolved.
       - Changing the name of an asset in a notification rule plugins could sometimes cause an error to be incorrectly logged. This has now been resolved.
       - An issue related to using averaging with the statistics history input to the notification rules has been fixed.
       - If a query for AF Attributes includes a search string token that does not exist, PI Web API returns an HTTP 400 error. PI Server South now retrieves error messages if this occurs and logs them.
       - Various filters summarize data over time, these have been standardized to use the times of the summary calculation.
       - The fledge-filter-threshold interface has been tidied up, removing duplicate information.
       - A problem with installation of the fledge-south-person-detection plugin on Ubuntu 20 has been resolved.
       - The control map configuration item of the fledge-south-modbus plugin was incorrectly described, this has now been resolved.


v2.1.0
-------

Release Date: 2022-12-26

- **Fledge Core**

    - New Features:

       - North plugins run as a task rather than a service would be run by the Python sending task rather than the C++ sending task. This resulted in filter pipelines not being applied to the task. This has now been resolved.
       - A new mechanism has been introduced that allows configuration items within a category to have a group associated with them. This allows items that relate to a particular mechanism be recognised as related by clients of the API and display decisions to be taken based on these groups.
       - The asset browser APIs have been enhanced to allow for a window of data in the past to be returned. In conjunction a new timespan entry point has been added to allow the oldest and newest date for which an asset exists within the reading buffer to be returned.
       - An option has been added to the advanced configuration of south services that allow the statistics that are generated by the south service to be tailored. Statistics may be kept for the service as a whole, each asset ingested by the service or both. This setting relates to a given service and may be different in different south services. Full details are available in the tuning guide within the documentation.
       - Two new types of user are now available in Fledge; users that can view the configuration only and users that can view the data only.


    - Bug Fix:
      
       - The reset and purge scripts have been improved such that if the reading plugin is different from the storage plugin the data will be removed from the appropriate plugins.
       - A problem that prevented items from being disabled in the user interface when they were not valid for the current configuration has been resolved.
       - An issue that would sometimes cause the error `Not all updates in a transaction succeeded` to be logged when updating the users access token has been resolved.
       - An issue that could cause properties of configuration items to be lost or incorrectly updated has been resolved.


- **GUI**

    - New Features:

       - The graphical user interface for viewing the configuration of the south and north services and tasks has now been updated to display the configuration items in multiple tabs.
       - The user interface now supports two types of view only users; those that can view the configuration and those that can view the data only.


    - Bug Fix:

       - An issue that could leave two menu items selected in the menu pane of the user interface has been resolved.
       - The tab view of tabular data in the user interface has been updated to show the date as well as the time related to readings.


- **Services & Plugins**

    - New Features:

       - A new north plugin, fledge-north-opcuaclient, has been created to send data with OPC UA Client to an OPC UA Server.
       - The asset filter has been updated to support the ability to map datapoint names for an asset.
       - The OMF north plugin now supports all ADH regions.
       - The OMF north plugin has been updated to allow support for OMF 1.2 features. This allows for better control of types within OMF resulting in the OMF plugin now dealing more cleanly with assets with different datapoints in different readings. Any assets that are already being sent to an OMF endpoint will continue to use the previous type mechanism. A number of new OMF hints are also supported.
       - The S2OPCUA south plugin has been updated to allow the timestamp for readings to be taken from the OPC UA server itself rather than the time that it was received by Fledge.



    - Bug Fix:

       - An issue with building of the DNP3 plugin on the Raspberry Pi platform has been resolved.
       - The S2OPCUA south plugin has been updated to resolve an issue with duplicate browse names causing data from two OPC UA variables being stored in the same Fledge datapoint. The plugin has also been updated to give more options for how the assets are structured. The option of a single asset for all datapoints and an asset put OPC UA object have been added. It is also possible to use the OPC UA object name as the prefix for asset names in the case of a single variable per asset as well as the current option of a fixed prefix for the browse name of the variable.

   
v2.0.1
-------

Release Date: 2022-10-20

- **Fledge Core**

    - New Features:

       - A new option, healthcheck has been added to the command line script used to start, stop and monitor the instance. This runs a number of checks against the system to detect common misconfigurations and issues with the environment that have been observed to cause issues with the system.
       - A third source of data is now available for sending to the north plugins, the internal audit log. This contains information such as configuration changes, services failures and other significant events within the Fledge instance. Note that a plugin must indicate it is able to handle audit data before it will be available within the plugin, currently the OPCUA north plugin is able to accept audit data.
       - The SQLite storage plugins have been updated to periodically reclaim free storage. This is useful for installations that experience short term peaks in storage demand as it will release the storage used during those peaks back to the operating system.
       - The API to fetch audit log entries has been enhanced to allow a time based filter to be applied. This allows only audit log entries since a given date to be returned to the caller.
       - A new API has been added that will fetch the list of packages that are available to be updated on the system.
       - Two new API entry points have been added that return health data for the logging subsystems and the storage service. These are used by the healthcheck option of the fledge command script.
       - The nesting of JSON objects that represent readings was previously limited to two levels within JSON, this limitation has now been lifted in line with the internal representation of nested objects. This is particularly important when handling audit log data in north plugins and now allows full audit log entries to be transmitted via north plugins.
       - Improvements have been made to error logs to diagnose certain storage faults. Also the ability to recover from some storage faults connected to gathering of statistics has been added.
       - Some improvements to the diagnostics for control operations within the system have been made to aid in the development of control pipelines within the system.
       - The public REST API documentation has been updated to cover more of the entry points supported and also to include examples of calling the asset browsing and statistics APIs using Grafana.


    - Bug Fix:
       
       - An issue with incorrectly formed JSON when control operations are triggered from the north service has been resolved.
       - A fix has been added to prevent a crash when the incorrect number of arguments is given to get_plugin_info. Also the function name to extract has been defaulted to be plugin_info.
       - An issue with control operation parameters which had embedded quotes within the parameter values has been resolved. This previously caused some control operations from north services to not be processed by the control dispatcher service.
       - When modifying a schedule the audit log entry, SCHCH for that changed, was previously added twice. This has now been resolved.
       - An issue that prevented a change to the units used for reading rate, e.g. per second, per minute or per hour, not being actioned until a service was restarted has now been fixed. If the rate was also changed then this change would be actioned.
       - It was possible to set a reading rate of 0 readings, this would cause the south service to fail. It is now not possible to set a rate of 0.


- **Services & Plugins**

    - New Features:

       - Support has been added to the OMF north plugin that allows the AVEVA Data Hub to be specified as a destination.
       - Documentation has been added for the GCP Pub/Sub north plugin.


    - Bug Fix:
      
       - The service dispatcher was previously looking at the wrong service type when sending operation messages to south service, this has now been resolved.
       - A bug in the scale-set filter that caused integer values to remain as integers when scaled to a value that could not be represented in an integer, e.g. scaling down or scaling by a non-integer factor, has been resolved.
       - The S2OPCUA south plugin provides a configuration option, minimum reporting interval that is used to slow the rate of reporting down for busy items. No reports of changes will be recorded when the change happens more frequently than the value set. In the case of the S2OPCUA plugin this was being ignored. It is now actioned correctly within the plugin.


v2.0.0
-------

Release Date: 2022-09-09

- **Fledge Core**

    - New Features:

       - Add options for choosing the Fledge Asset name: Browser Name, Subscription Path and Full Path. Use the OPC UA Source timestamp as the User Timestamp in Fledge.
       - The storage interface used to query generic configuration tables has been improved to support tests for null and non-null column values.
       - The ability for north services to support control inputs coming from systems north of Fledge has been introduced.
       - The handling of a failed storage service has been improved. The client now attempt to re-connect and if that fails they will down. The logging produced is now much less verbose, removing the repeated messages previously seen.
       - A new service has been added to Fledge to facilitate the routing of control messages within Fledge. This service is responsible for determining which south services to send control requests to and also for the security aspects of those requests.
       - Ensure that new Fledge data types not supported by OMF are not processed.
       - The storage service now supports a richer set of queries against the generic table interface. In particular, joins between tables are now supported.
       - OPC UA Security has been enhanced. This plugin now supports Security Policies Basic256 and Basic256Sha256, with Security Modes Sign and Sign & Encrypt. Authentication types are anonymous and username/password.
       - South services that have a slow poll rate can take a long time to shutdown, this sometimes resulted in those services not shutting down cleanly. The shutdown process has been modified such that these services now shutdown promptly regardless of polling rate.
       - A new configuration item type has been added for the selection of access control lists.
       - Support has been added to the Python query builder for NULL and NOT NULL columns.
       - The Python query builder has been updated to support nested database queries.
       - The third party packages on which Fledge is built have been updated to use the latest versions to resolve issues with vulnerabilities in these underlying packages.
       - When the data stream from a south plugin included an OMF Hint of AFLocation, performance of the OMF North plugin would degrade. In addition, process memory would grow over time. These issues have been fixed.
       - The version of the PostgreSQL database used by the Postgres storage plugin has been updated to PostgreSQL 13.
       - An enhancement has been added to the North service to allow the user to specify the block size to use when sending data to the plugin. This helps tune the north services and is described in the tuning guide within the documentation.
       - The notification service would previously output warning messages when it was starting. These were not an indication of a problem and should have been information messages. This has now been resolved.
       - The backup mechanism has been improved to include some external items in the backup and provide a more secure backup.
       - The purge option that controls if unsent assets can be purged or not has been enhanced to provide options for sent to any destination or sent to all destinations as well as sent to no destinations.
       - It is now possible to add control features to Python south plugins.
       - Certificate based authentication is now possible between services in a single instance. This allows for secure control messages to be implemented between services.
       - Performance improvements have been made such that the display of south service data when large numbers of assets are in use.
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
       - A new section has been added to the Fledge Tuning guide that discusses the tuning of North services and tasks. Also scheduler tuning has been added to the tuning guide along with the tuning of the service monitor which is used to detect failures of services within Fledge.
       - The Tuning Fledge section of the documentation has been updated to include information on tuning the Fledge service monitor that is used to monitor and restart Fledge services. A section has also been added that describes the tuning of north services and tasks. A new section describes the different storage plugins available, when they should be used and how to tune them.
       - Added an article on Developing with Windows Subsystem for Linux (WSL2) to the Plugin Developer Guide. WSL2 allows you to run a Linux environment directly on Windows without the overhead of Windows Hyper-V. You can run Fledge and develop plugins on WSL2.
       - Documentation has been added for the purge process and the new options recently added.
       - Documentation has been added to the plugin developer guides that explain what needs to be done to allow the packaging mechanism to be able to package a plugin.
       - Documentation has been added to the Building Pipelines section of the documentation for the new UI feature that allows Python packages to be installed via the user interface.
       - Documentation has been updated to show how to build Fledge using the requirements.sh script.
       - The documentation ordering has been changed to make the section order more logical.
       - The plugin developers guide has been updated to include information on the various flags that are used to communicate the options implemented by a plugin.
       - Updated OMF North plugin documentation to include current OSIsoft (AVEVA) product names.
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
       - An issue that could on rare occasions cause the SQLite plugin to silently discard readings has been resolved.
       - An issue with the automatic renewal of authentication certificates has been resolved.
       - Deleting a service which had a filter pipeline could cause some orphaned configuration information to be left stored. This prevented creating filters of the same name in the future. This has now been resolved.
       - The error reporting has been improved when downloading backups from the system.
       - An issue that could cause north plugins to occasionally fail to shutdown correctly has now been resolved.
       - Some fixes are made in Package update API that allows the core package to be updated.
       - The documentation has been updated to correct a statement regarding running the south side as a task.


- **GUI**

    - New Features:

        - A new *Developer* item has been added to the user interface to allow for the management of Python packages via the UI. This is enabled by turning on developer features in the user interface *Settings* page.
        - A control has been added that allows the display of assets in the *South* screen to be collapsed or expanded. This allows for more services to be seen when services ingest multiple assets.
        - A new feature has been added to the south page that allows the relationship between an asset and a service to be deprecated. This is a special feature enabled with the Developer Features option. See the documentation on building pipelines for a full description.
        - A new feature has been added to the Assets and Readings page that allows for manual purging of named assets or all assets. This is a developer only feature and should not be used on production systems. The feature is enabled, along with other developer features via the Settings page.
        - A new feature has been added to the South and North pages for each service that allows the user to view, import, export and delete the data persisted by a plugin. This is a developer only feature and should not be used on production systems. It is enabled via the Setting page.
        - A new configuration type, Access Control List, is now supported in user interface. This allows for selection of an ACL from those already created.
        - A new tabbed layout has been adopted for the editing of south and north services and tasks. Configuration, Advanced and Security tabs are supported as our tabs for developer features if enabled.
        - The user interface for displaying system logs has been modified to improve the performance of log viewing.
        - The User Interface has been updated to use the latest versions of a number of packages it depends upon, due to vulnerabilities reported in those packages.
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

       - A new fledge-notify-control plugin has been added that allows notifications to be delivered via the control dispatcher service. This allows the full features of the control dispatcher to be used with the edge notification path.
       - A new fledge-notify-customasset notification delivery plugin that creates an event asset in readings.
       - A new fledge-rule-delta notification rule plugin that triggers when a data point value changes.
       - A new fledge-rule-watchdog notification rule plugin that allows notifications to be send if data stops being ingress for specified assets.
       - Support has been added for proxy servers in the north HTTP-C plugin.
       - The OPCUA north plugin has been updated to include the ability for systems outside of Fledge to write to the server that Fledge advertises. These write are taken as control input into the Fledge system.
       - The HTTPC North plugin has been enhanced to add an optional Python script that can be used to format the payload of the data sent in the HTTP REST request.
       - The SQLite storage plugins have been updated to support service extension schemas. This is a mechanism that allows services within the Fledge system to add new schemas within the storage service that are exclusive to that service.
       - The Python35 filter has been updated to use the common Python interpreter. This allows for packages such as numpy to be used. The resilience and error reporting of this plugin have also been improved.
       - A set of developer only features designed to aid the process of developing data pipelines and plugins has been added in this release. These features are turned on and off via a toggle setting on the Settings page.
       - A new option has been added to the Python35 filter that changes the way datapoint names are used in the JSON readings. Previously there had to be encoded and decode by use of the b’xxx' mechanism. There is now a toggle that allows for either this to be required or simple text string use to be enabled.
       - The API of the storage service has been updated to allow for custom schemas to be created by services that extend the core functionality of the system.
       - New image type datapoints can now be sent between instances using the http north and south plugins.
       - The ability to define response headers in the http south plugin has been added to aid certain circumstances where CORS provided data flows.
       - The documentation of the Python35 filter has been updated to include a fuller description of how to make use of the configuration data block supported by the plugin.
       - The documentation describing how to run services under the debugger has been improved along with other improvements to the documentation aimed at plugin developers.
       - Documentation has been added for fledge-north-azure plugin.
       - Documentation has now been added for fledge-north-harperdb plugin.


    - Bug Fix:

       - Build procedures were updated to accommodate breaking changes in the S2OPC OPCUA Toolkit.
       - Occasionally switching from the sqlite to the sqlitememory plugin for the storage of readings would cause a fatal error in the storage layer. This has now been fixed and it is possible to change to sqlitememory without an error.
       - A race condition within the modbus south plugin that could cause unfair scheduling of read versus write operations has been resolved. This could cause write operations to be delayed in some circumstances. The scheduling of set point write operations is now fairly interleaved between the read operations in all cases.
       - A problem that caused the HTTPC North plugin to fail if the path component of the URL was omitted has been resolved.
       - The modbus-c south plugin documentation has been enhanced to include details of the function codes used to read modbus data. Also incorrect error message and others have been improved to aid resolving configuration issues. The documentation has been updated to include descriptive text for the error messages that may occur.
       - The Python35 filter plugin has been updated such that if no data is to be passed onwards it may now simply return the None Python constant or an empty list. Also it allows simple Python scripts to be added into filter pipelines has had a number of updates to improve the robustness of the plugin in the event of incorrect script code being provided by the user. The behaviour of the plugin has also been updated such that any errors run the script will prevent data being passed onwards the filter pipeline. An error explaining the exact cause of the failure is now logged in the system log. Also its documentation has been updated to discuss Python package imports and issues when removing previously used imports.
       - The Average rule has been updated to improve the user interaction during the configuration of the rule.
       - The first time a plugin that persisted data is executed erroneous errors and warnings would be written to the system log. This has now been resolved.
       - An issue with the Kafka north plugin not sending data in certain circumstances has been resolved.
       - Adding some notification plugins would cause incorrect errors to be logged to the system log. The functioning of the notifications was not affected. This has now been resolved and the error logs no longer appear.
       - The documentation for the fledge-rule-delta plugin has been corrected.


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
       - An issue with the SQLite in-memory storage plugin that caused database locks under high load conditions has been resolved.


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

       - Documentation has been added for the use of the SQLite in-memory storage plugin.
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


