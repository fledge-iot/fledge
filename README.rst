FogLAMP
-------

This is the FogLAMP project.

FogLAMP is an open source platform for the **Internet of Things**, it acts as an edge gateway between sensor devices and cloud storage systems, the FOG and other implmentsations of FogLAMP in an hierarchical environment. FogLAMP provides a means of buffering data coming from sensors and forwarding that data onto high level storage systems. It assumes the underlying network layer is not always connected or may not be reliable in industrial envionments. Data from sensors may be stored within FogLAMP for a number of days before being purged from the FogLAMP storage. During this time it may be sent to one or more historians and also accessed via a REST API for use by *local* analytical applications.

FogLAMP has been designed to run in a Linux environment and make uae of Linux services.

Architecture
------------

FogLAMP is built using a microservices architecture for major component areas, these services consist of
- a core service responsible for the management of the other services, the external REST API's, scheduling and monitoring of activities.
- a device service responsible for the communication between FogLAMP and the sensors/actuators
- a storage layer responsible for the persistance of configuration and metrics and the buffering of sensor data 

FogLAMP makes extensive use of plugin components in order to increase the flexibility of the implementation
- device plugins are used to allow for the easy expansion of FogLAMP to deal with new devices and device connection buses
- translator plugins are used to allow for connection to different historians
- datastore plugins are used to allow FogLAMP to use different storage mechanisms for persisting meta data and the sensor data
- authentication provider plugins are used to allow the authentication mechanism to be matched with enterprise requirements or provided internally by FogLAMP.

The other paradigm that is used extensively within FogLAMP is the idea of scheduling processes to perform specific operations. The FogLAMP core contains a scheduler which can execute processes based on time based or event based schedules. This is used to start processes when an event occurs, such as FogLAMP starting, or based on a time trigger.

Scheduled processes are used to send data from FogLAMP to the historian, to purge data from the FogLAMP data buffer, to gather statistics for historical analysis and perform backups of the FogLAMP environment.
