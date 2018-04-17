.. REST API Guide
.. https://docs.google.com/document/d/1JJDP7g25SWerNVCxgff02qp9msHbqA9nt3RAFx8-Qng

.. |br| raw:: html

   <br />

.. |ar| raw:: html

   <div align="right">

.. Images


.. Links


.. =============================================


********************
The FogLAMP REST API
********************

Users, admnistrators and applications interact with FogLAMP via a REST API. This section presents a full reference of the API.

.. note:: The FogLAMP REST API should not be confused with the internal REST API used by FogLAMP tasks and microservices to communicate with each other.


Introducing the FogLAMP REST API
================================

The REST API is the route into the FogLAMP appliance, it provides all user and program interaction to configure, monitor and manage the FogLAMP system. A separate specification will define the contents of the API, in summary however it is designed to allow for: 

- The complete configuration of the FogLAMP appliance
- Access to monitoring statistics for the FogLAMP appliance
- User and role management for access to the API
- Access to the data buffer contents


Port Usage
----------

In general FogLAMP components use dynamic port allocation to determine which port to use, the admin API is however an exception to this rule. The Admin API port has to be known to end-users and any user interface or management system that uses it, therefore the port on which the admin API listens must be consistent and fixed between invocations. This does not mean however that it can not be changed by the user. The user must have the option to define the port to use by the admin API to listen on. To achieve this the port will be stored in the configuration data for the admin API, using the configuration category *AdminAPI*, see Configuration. Administrators who have access to the appliance can find information regarding the port and the protocol to used (i.e. HTTP or HTTPS) in the *pid* file stored in *$FOGLAMP_DATA/var/run/*:

.. code-block:: console

  $ cat data/var/run/foglamp.core.pid
  { "adminAPI"  : { "protocol"  : "HTTP",
                    "port"      : 8081,
                    "addresses" : [ "0.0.0.0" ] },
    "processID" : 3585 }
  $


FogLAMP is shipped with a default port for the admin API to use, however the user is free to change this after installation. This can be done by first connecting to the port defined as the default and then modifying the port using the admin API. FogLamp should then be restarted to make use of this new port.


Infrastructure
--------------

There are two REST API’s that allow external access to FogLAMP, the **Administration API** and the **User API**. The User API is intended to allow access to the data in the FogLAMP storage layer which buffers sensor readings, and it is not part of this current version.

The Administration API is the first API is concerned with all aspects of managing and monitoring the FogLAMP appliance. This API is used for all configuration operations that occur beyond basic installation.


Administration API Reference
============================

This section presents the list of administrative API methods in alphabetical order.


audit
-----

The *audit* methods are used to retrieve and manage information in the audit trail, audit entries and notifications. The API interacts directly with the audit trail log tables in the storage layer with the exception of the create method which must go via the audit trail component in order that audit trail entries created via the API are treated in the same way as those created within the system.


GET Audit Entries
~~~~~~~~~~~~~~~~~

``GET /foglamp/audit`` - return a list of audit trail entries sorted with most recent first.

**Request Parameters**

- **limit** - limit the number of audit entries returned to the number specified
- **skip** - skip the first n entries in the audit table, used with limit to implement paged interfaces
- **source** - filter the audit entries to be only those from the specified source
- **severity** - filter the audit entries to only those of the specified severity


**Response Payload**

The response payload is an array of JSON objects with the audit trail entries.

+-----------+-----------+-----------------------------------------------+--------------------------------------------------------+
| Name      | Type      | Description                                   | Example                                                |
+===========+===========+===============================================+========================================================+
| timestamp | timestamp | The timestamp when the audit trail |br|       | 2018-04-16 14:33:18.215                                |
|           |           | item was written.                             |                                                        |
+-----------+-----------+-----------------------------------------------+--------------------------------------------------------+
| source    | string    | The source of the audit trail entry.          | CoAP                                                   |
+-----------+-----------+-----------------------------------------------+--------------------------------------------------------+
| severity  | string    | The severity of the event that triggered |br| | FAILURE                                                |
|           |           | the audit trail entry to be written. |br|     |                                                        |
|           |           | This will be one of SUCCESS, FAILURE, |br|    |                                                        |
|           |           | WARNING or INFORMATION.                       |                                                        |
+-----------+-----------+-----------------------------------------------+--------------------------------------------------------+
| details   | object    | A JSON object that describes the detail |br|  | { "message" : |br|                                     |
|           |           | of the audit trail event.                     | "Sensor readings discarded due to malformed payload" } |
+-----------+-----------+-----------------------------------------------+--------------------------------------------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/audit?limit=2
  { "totalCount" : 24,
    "audit"      : [ { "timestamp" : "2018-02-25 18:58:07.748",
                       "source"    : "SRVRG",
                       "details"   : { "name" : "COAP" },
                       "severity"  : "INFORMATION" },
                     { "timestamp" : "2018-02-25 18:58:07.742",
                       "source"    : "SRVRG",
                       "details"   : { "name" : "HTTP_SOUTH" },
                       "severity"  : "INFORMATION" },
                     { "timestamp" : "2018-02-25 18:58:07.390",
                       "source"    : "START",
                       "details"   : {},
                       "severity"  : "INFORMATION" }
                   ]
  }
  $ curl -s http://localhost:8081/foglamp/audit?source=SRVUN&limit=1
  { "totalCount" : 4,
    "audit"      : [ { "timestamp" : "2018-02-25 05:22:11.053",
                       "source"    : "SRVUN",
                       "details"   : { "name": "COAP" },
                       "severity"  : "INFORMATION" }
                   ]
  }
  $


POST Audit Entries
~~~~~~~~~~~~~~~~~~

``POST /foglamp/audit`` - create a new audit trail entry.

The purpose of the create method on an audit trail entry is to allow a user interface or an application that is using the FogLAMP API to utilize the FogLAMP audit trail and notification mechanism to raise user defined audit trail entries.


**Request Payload**

The request payload is a JSON object with the audit trail entry minus the timestamp..

+-----------+-----------+-----------------------------------------------+---------------------------+
| Name      | Type      | Description                                   | Example                   |
+===========+===========+===============================================+===========================+
| source    | string    | The source of the audit trail entry.          | LocalMonitor              |
+-----------+-----------+-----------------------------------------------+---------------------------+
| severity  | string    | The severity of the event that triggered |br| | FAILURE                   |
|           |           | the audit trail entry to be written. |br|     |                           |
|           |           | This will be one of SUCCESS, FAILURE, |br|    |                           |
|           |           | WARNING or INFORMATION.                       |                           |
+-----------+-----------+-----------------------------------------------+---------------------------+
| details   | object    | A JSON object that describes the detail |br|  | { "message" : |br|        |
|           |           | of the audit trail event.                     | "Internal System Error" } |
+-----------+-----------+-----------------------------------------------+---------------------------+


**Response Payload**

The response payload is the newly created audit trail entry.

+-----------+-----------+-----------------------------------------------+---------------------------+
| Name      | Type      | Description                                   | Example                   |
+===========+===========+===============================================+===========================+
| timestamp | timestamp | The timestamp when the audit trail |br|       | 2018-04-16 14:33:18.215   |
|           |           | item was written.                             |                           |
+-----------+-----------+-----------------------------------------------+---------------------------+
| source    | string    | The source of the audit trail entry.          | LocalMonitor              |
+-----------+-----------+-----------------------------------------------+---------------------------+
| severity  | string    | The severity of the event that triggered |br| | FAILURE                   |
|           |           | the audit trail entry to be written. |br|     |                           |
|           |           | This will be one of SUCCESS, FAILURE, |br|    |                           |
|           |           | WARNING or INFORMATION.                       |                           |
+-----------+-----------+-----------------------------------------------+---------------------------+
| details   | object    | A JSON object that describes the detail |br|  | { "message" : |br|        |
|           |           | of the audit trail event.                     | "Internal System Error" } |
+-----------+-----------+-----------------------------------------------+---------------------------+


**Example**

.. code-block:: console

  $ curl -X POST http://localhost:8081/foglamp/audit \
  -d '{ "severity": "FAILURE", "details": { "message": "Internal System Error" }, "source": "LocalMonitor" }'
  { "source": "LocalMonitor",
    "timestamp": "2018-04-17 11:49:55.480",
    "severity": "FAILURE",
    "details": { "message": "Internal System Error" }
  }
  $
  $ curl -X GET http://vbox-dev:8081/foglamp/audit?severity=FAILURE
  { "totalCount": 1,
    "audit": [ { "timestamp": "2018-04-16 18:32:28.427",
                 "source"   :    "LocalMonitor",
                 "details"  : { "message": "Internal System Error" },
                 "severity" : "FAILURE" }
             ]
  }
  $


category
--------

The *category* interface is part of the Configuration Management for FogLAMP. The configuration REST API interacts with the configuration manager to create, retrieve, update and delete the configuration categories and values. Specifically all updates must go via the management layer as this is used to trigger the notifications to the components that have registered interest in configuration categories. This is the means by which the dynamic reconfiguration of FogLAMP is achieved.


GET categor(ies)
~~~~~~~~~~~~~~~~

``GET /foglamp/category`` - return the list of known categories in the configuration database


**Response Payload**

The response payload is a JSON object with an array of JSON objects, one per valid category.

+-------------+--------+------------------------------------------------+------------------+
| Name        | Type   | Description                                    | Example          |
+=============+========+================================================+==================+
| key         | string | The category key, each category |br|           | network          |
|             |        | has a unique textual key the defines it.       |                  |
+-------------+--------+------------------------------------------------+------------------+
| description | string | A description of the category that may be |br| | Network Settings |
|             |        | used for display purposes.                     |                  |
+-------------+--------+------------------------------------------------+------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://vbox-dev:8081/foglamp/category 
  { "categories": [ { "key"         : "CC2650ASYN",
                      "description" : "TI SensorTag CC2650 async South Plugin" },
                    { "key"         : "CC2650POLL",
                      "description" : "TI SensorTag CC2650 polling South Plugin" },
                    { "key"         : "COAP",
                      "description" : "COAP Device" },
                    { "key"         : "HTTP_SOUTH",
                      "description" : "HTTP_SOUTH Device" },
                    { "key"         : "POLL",
                      "description" : "South Plugin polling template" },
                    { "key"         : "SCHEDULER",
                      "description" : "Scheduler configuration" },
                    { "key"         : "SEND_PR_1",
                      "description" : "OMF North Plugin Configuration" },
                    { "key"         : "SEND_PR_2",
                      "description" : "OMF North Statistics Plugin Configuration" },
                    { "key"         : "SEND_PR_3",
                      "description" : "HTTP North Plugin Configuration" },
                    { "key"         : "SEND_PR_4",
                      "description" : "OCS North Plugin Configuration" },
                    { "key"         : "SMNTR",
                      "description" : "Service Monitor configuration" },
                    { "key"         : "South",
                      "description" : "South server configuration" },
                    { "key"         : "rest_api",
                      "description" : "The FogLAMP Admin and User REST API" },
                    { "key"         : "service",
                      "description" : "The FogLAMP service configuration" } ] }
  $


GET category 
~~~~~~~~~~~~

``GET /foglamp/category/<name>`` - return the configuration items in the given category.


**Path Parameters**

- **name** is the name of one of the categories returned from the GET /foglamp/category call.


**Response Payload**

The response payload is a set of configuration items within the category, each item is a JSON object with the following set of properties.

+-------------+--------+--------------------------------------------------------------+-------------------------------+
| Name        | Type   | Description                                                  | Example                       |
+=============+========+==============================================================+===============================+
| description | string | A description of the configuration item |br|                 | The IPv4 network address |br| |
|             |        | that may be used in a user interface.                        | of the FogLAMP server         |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| type        | string | A type that may be used by a user interface |br|             | IPv4                          |
|             |        | to know how to display an item.                              |                               |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| default     | string | An optional default value for the configuration item.        | 127.0.0.1                     |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| value       | string | The current configured value of the configuration item. |br| | 192.168.0.27                  |
|             |        | This may be empty if no value has been set.                  |                               |
+-------------+--------+--------------------------------------------------------------+-------------------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://vbox-dev:8081/foglamp/category/rest_api
  { "authentication": {
        "type": "string",
        "default": "optional",
        "description": "To make the authentication mandatory or optional for API calls",
        "value": "optional" },
    "authProviders": {
        "type": "JSON",
        "default": "{\"providers\": [\"username\", \"ldap\"] }",
        "description": "A JSON object which is an array of authentication providers to use for the interface",
        "value": "{\"providers\": [\"username\", \"ldap\"] }" },
    "certificateName": {
        "type": "string",
        "default": "foglamp",
        "description": "Certificate file name",
        "value": "foglamp" },
    "enableHttp": {
        "type": "boolean",
        "default": "true",
        "description": "Enable or disable the connection via HTTP",
        "value": "true" },
    "httpPort": {
        "type": "integer",
        "default": "8081",
        "description": "The port to accept HTTP connections on",
        "value": "8081" },
    "httpsPort": {
        "type": "integer",
        "default": "1995",
        "description": "The port to accept HTTPS connections on",
        "value": "1995" },
    "allowPing": {
        "type": "boolean",
        "default": "true",
        "description": "To allow access to the ping, regardless of the authentication required and authentication header",
        "value": "true" },
    "passwordChange": {
        "type": "integer",
        "default": "0",
        "description": "Number of days which a password must be changed",
        "value": "0" }
  }
  $


GET category item
~~~~~~~~~~~~~~~~~

``GET /foglamp/category/<name>/<item>`` - return the configuration item in the given category.


**Path Parameters**

- **name** - the name of one of the categories returned from the GET /foglamp/category call.
- **item** - the the item within the category to return.


**Response Payload**

The response payload is a configuration item within the category, each item is a JSON object with the following set of properties.

+-------------+--------+--------------------------------------------------------------+-------------------------------+
| Name        | Type   | Description                                                  | Example                       |
+=============+========+==============================================================+===============================+
| description | string | A description of the configuration item |br|                 | The IPv4 network address |br| |
|             |        | that may be used in a user interface.                        | of the FogLAMP server         |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| type        | string | A type that may be used by a user interface |br|             | IPv4                          |
|             |        | to know how to display an item.                              |                               |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| default     | string | An optional default value for the configuration item.        | 127.0.0.1                     |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| value       | string | The current configured value of the configuration item. |br| | 192.168.0.27                  |
|             |        | This may be empty if no value has been set.                  |                               |
+-------------+--------+--------------------------------------------------------------+-------------------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://vbox-dev:8081/foglamp/category/rest_api/httpsPort
  { "type": "integer",
    "default": "1995",
    "description": "The port to accept HTTPS connections on",
    "value": "1995"
  }
  $


PUT category item
~~~~~~~~~~~~~~~~~

``PUT /foglamp/category/<name>/<item>`` - set the configuration item value in the given category.


**Path Parameters**

- **name** - the name of one of the categories returned from the GET /foglamp/category call.
- **item** - the the item within the category to set.


**Request Payload**

A JSON object with the new value to assign to the configuration item.

+-------------+--------+------------------------------------------+--------------+
| Name        | Type   | Description                              | Example      |
+=============+========+==========================================+==============+
| value       | string | The new value of the configuration item. | 192.168.0.27 |
+-------------+--------+------------------------------------------+--------------+


**Response Payload**

The response payload is the newly updated configuration item within the category, the item is a JSON object object with the following set of properties.

+-------------+--------+--------------------------------------------------------------+-------------------------------+
| Name        | Type   | Description                                                  | Example                       |
+=============+========+==============================================================+===============================+
| description | string | A description of the configuration item |br|                 | The IPv4 network address |br| |
|             |        | that may be used in a user interface.                        | of the FogLAMP server         |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| type        | string | A type that may be used by a user interface |br|             | IPv4                          |
|             |        | to know how to display an item.                              |                               |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| default     | string | An optional default value for the configuration item.        | 127.0.0.1                     |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| value       | string | The current configured value of the configuration item. |br| | 192.168.0.27                  |
|             |        | This may be empty if no value has been set.                  |                               |
+-------------+--------+--------------------------------------------------------------+-------------------------------+



**Example**

.. code-block:: console

  $ curl -X PUT http://vbox-dev:8081/foglamp/category/rest_api/httpsPort \
    -d '{ "value" : "1996" }'
  { "default": "1995",
    "type": "integer",
    "description": "The port to accept HTTPS connections on",
    "value": "1996"
  }
  $


DELETE category item
~~~~~~~~~~~~~~~~~~~~

``DELETE /foglamp/category/<name>/<item>/value`` - unset the value of the configuration item in the given category.

This will result in the value being returned to the default value if one is defined. If not the value will be blank, i.e. the value property of the JSON object will exist with an empty value.


**Path Parameters**

- **name** - the name of one of the categories returned from the GET /foglamp/category call.
- **item** - the the item within the category to return.


**Response Payload**

The response payload is the newly updated configuration item within the category, the item is a JSON object object with the following set of properties.

+-------------+--------+--------------------------------------------------------------+-------------------------------+
| Name        | Type   | Description                                                  | Example                       |
+=============+========+==============================================================+===============================+
| description | string | A description of the configuration item |br|                 | The IPv4 network address |br| |
|             |        | that may be used in a user interface.                        | of the FogLAMP server         |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| type        | string | A type that may be used by a user interface |br|             | IPv4                          |
|             |        | to know how to display an item.                              |                               |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| default     | string | An optional default value for the configuration item.        | 127.0.0.1                     |
+-------------+--------+--------------------------------------------------------------+-------------------------------+
| value       | string | The current configured value of the configuration item. |br| | 192.168.0.27                  |
|             |        | This may be empty if no value has been set.                  |                               |
+-------------+--------+--------------------------------------------------------------+-------------------------------+


**Example**

.. code-block:: console

  $ curl -X DELETE http://vbox-dev:8081/foglamp/category/rest_api/httpsPort/value
  { "default": "1995",
    "type": "integer",
    "description": "The port to accept HTTPS connections on",
    "value": "1995"
  }
  $

 
POST category
~~~~~~~~~~~~~

``POST /foglamp/category`` - creates a new category


**Request Payload**

A JSON object that defines the category.

+--------------------+--------+------------------------------------------------------+-------------------------------+
| Name               | Type   | Description                                          | Example                       |
+====================+========+======================================================+===============================+
| key                | string | The key that identifies the category. |br|           | backup                        |
|                    |        | If the key already exists as a category |br|         |                               |
|                    |        | then the contents of this request |br|               |                               |
|                    |        | is merged with the data stored.                      |                               |
+--------------------+--------+------------------------------------------------------+-------------------------------+
| description        | string | A description of the configuration category          | Backup configuration          |
+--------------------+--------+------------------------------------------------------+-------------------------------+
| items              | list   | An optional list of items to create in this category |                               |
+--------------------+--------+------------------------------------------------------+-------------------------------+
| |ar| *name*        | string | The name of a configuration item                     | destination                   |
+--------------------+--------+------------------------------------------------------+-------------------------------+
| |ar| *description* | string | A description of the configuration item              | The destination to which |br| |
|                    |        |                                                      | the backup will be written    |
+--------------------+--------+------------------------------------------------------+-------------------------------+
| |ar| *type*        | string | The type of the configuration item                   | string                        |
+--------------------+--------+------------------------------------------------------+-------------------------------+
| |ar| *default*     | string | An optional default value for the configuration item | /backup                       |
+--------------------+--------+------------------------------------------------------+-------------------------------+

**NOTE:** with list we mean a list of JSON objects in the form of { obj1,obj2,etc. }, to differ from the concept of *array*, i.e. [ obj1,obj2,etc. ]


**Example**

.. code-block:: console

  $ curl -X POST http://vbox-dev:8081/foglamp/category \
    -d '{ "key": "My Configuration", "description": "This is my new configuration",
        "value": { "item one": { "description": "The first item", "type": "string", "default": "one" },
                   "item two": { "description": "The second item", "type": "string", "default": "two" },
                   "item three": { "description": "The third item", "type": "string", "default": "three" } } }'
  { "description": "This is my new configuration", "key": "My Configuration", "value": {
        "item one": { "default": "one", "type": "string", "description": "The first item", "value": "one" },
        "item two": { "default": "two", "type": "string", "description": "The second item", "value": "two" },
        "item three": { "default": "three", "type": "string", "description": "The third item", "value": "three" } }
  }
  $
 

ping
----

The *ping* interface gives a basic confidence check that the FogLAMP appliance is running and the API aspect of the appliance if functional. It is designed to be a simple test that can  be applied by a user or by an HA monitoring system to test the liveness and responsiveness of the system.


GET ping
~~~~~~~~

``GET /foglamp/ping`` - return liveness of FogLAMP

*NOTE:* the GET method can be executed without authentication even when authentication is required.


**Response Payload**

The response payload is some basic health information in a JSON object.

+------------------------+---------+-----------------------------------------------------------------+-------------------+
| Name                   | Type    | Description                                                     | Example           |
+========================+=========+=================================================================+===================+
| authenticationOptional | boolean | When true, the REST API does not require authentication. |br|   | true              |
|                        |         | When false, users must successfully login in order to call |br| |                   |
|                        |         | the rest API. Default is *true*                                 |                   |
+------------------------+---------+-----------------------------------------------------------------+-------------------+
| dataPurged             | numeric | A count of the number of readings purged                        | 226               |
+------------------------+---------+-----------------------------------------------------------------+-------------------+
| dataRead               | numeric | A count of the number of sensor readings                        | 1452              |
+------------------------+---------+-----------------------------------------------------------------+-------------------+
| dataSent               | numeric | A count of the number of readings sent to PI                    | 347               |
+------------------------+---------+-----------------------------------------------------------------+-------------------+
| uptime                 | numeric | Time in seconds since FogLAMP started                           | 2113.076449394226 |
+------------------------+---------+-----------------------------------------------------------------+-------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/ping
  { "authenticationOptional": true,
  "dataPurged": 226,
  "dataRead": 1452,
  "dataSent": 347,
  "uptime": 2113.076449394226 }
  $

 
task
----

The *task* interface allow an administrative user to monitor and control FogLAMP tasks.


GET task
~~~~~~~~

``GET /foglamp/task`` - return the list of all known task running or completed


**Request Parameters**

- **name** - an optional task name to filter on, only executions of the particular task will be reported.
- **state** - an optional query parameter that will return only those tasks in the given state.


**Response Payload**

The response payload is a JSON object with an array of task objects.

+-----------+-----------+-----------------------------------------+--------------------------------------+
| Name      | Type      | Description                             | Example                              |
+===========+===========+=========================================+======================================+
| id        | string    | A unique identifier for the task.  |br| | 0a787bf3-4f48-4235-ae9a-2816f8ac76cc |
|           |           | This takes the form of a uuid and  |br| |                                      |
|           |           | not a Linux process id as the ID’s |br| |                                      |
|           |           | must survive restarts and failovers     |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| name      | string    | The name of the task                    | purge                                |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| state     | string    | The current state of the task           | Running                              |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| startTime | timestamp | The date and time the task started      | 2018-04-17 08:32:15.071              |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| endTime   | timestamp | The date and time the task ended   |br| | 2018-04-17 08:32:14.872              |
|           |           | This may not exist if the tast is  |br| |                                      |
|           |           | not completed.                          |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| reason    | string    | An optional reason string that     |br| | No destination available |br|        |
|           |           | describes why the task failed.          | to write backup                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://vbox-dev:8081/foglamp/task
  { "tasks": [ { "exitCode": 0,
                 "id": "0a787bf3-4f48-4235-ae9a-2816f8ac76cc",
                 "state": "Complete",
                 "reason": "",
                 "name": "stats collector",
                 "endTime": "2018-04-17 08:32:15.071",
                 "startTime": "2018-04-17 08:32:14.872" }.
               { "exitCode": 0,
                 "id": "8cd6258e-58cc-4812-a1a7-f044377f98b7",
                 "state": "Complete",
                 "reason": "",
                 "name": "stats collector",
                 "endTime": "2018-04-17 08:32:30.069",
                 "startTime": "2018-04-17 08:32:29.851" },
                 ... ] }
  $
  $ curl -X GET http://vbox-dev:8081/foglamp/task?name=purge
  { "tasks": [ { "exitCode": 0,
                 "id": "bddad550-463a-485d-9247-148e952452e0",
                 "state": "Complete",
                 "reason": "",
                 "name": "purge",
                 "endTime": "2018-04-17 09:32:00.203",
                 "startTime": "2018-04-17 09:31:59.847" },
               { "exitCode": 0,
                 "id": "bfe79408-9a4f-4245-bfa5-d843f171d494",
                 "state": "Complete",
                 "reason": "",
                 "name": "purge",
                 "endTime": "2018-04-17 10:32:00.188",
                 "startTime": "2018-04-17 10:31:59.850" },
                 ... ] }
  $
  $ curl -X GET http://vbox-dev:8081/foglamp/task?state=complete
  { "tasks": [ { "exitCode": 0,
                 "id": "0a787bf3-4f48-4235-ae9a-2816f8ac76cc",
                 "state": "Complete",
                 "reason": "",
                 "name": "stats collector",
                 "endTime": "2018-04-17 08:32:15.071",
                 "startTime": "2018-04-17 08:32:14.872" },
               { "exitCode": 0,
                 "id": "8cd6258e-58cc-4812-a1a7-f044377f98b7",
                 "state": "Complete",
                 "reason": "",
                 "name": "stats collector",
                 "endTime": "2018-04-17 08:32:30.069",
                 "startTime": "2018-04-17 08:32:29.851" },
                 ... ] }
   $

 
GET task latest
~~~~~~~~~~~~~~~

``GET /foglamp/task/latest`` - return the list of most recent task execution for each name.

This call is designed to allow a monitoring interface to show when each task was last run and what the status of that task was. 


**Request Parameters**

- **name** - an optional task name to filter on, only executions of the particular task will be reported.
- **state** - an optional query parameter that will return only those tasks in the given state.


**Response Payload**

The response payload is a JSON object with an array of task objects.

+-----------+-----------+-----------------------------------------+--------------------------------------+
| Name      | Type      | Description                             | Example                              |
+===========+===========+=========================================+======================================+
| id        | string    | A unique identifier for the task.  |br| | 0a787bf3-4f48-4235-ae9a-2816f8ac76cc |
|           |           | This takes the form of a uuid and  |br| |                                      |
|           |           | not a Linux process id as the ID’s |br| |                                      |
|           |           | must survive restarts and failovers     |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| name      | string    | The name of the task                    | purge                                |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| state     | string    | The current state of the task           | Running                              |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| startTime | timestamp | The date and time the task started      | 2018-04-17 08:32:15.071              |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| endTime   | timestamp | The date and time the task ended   |br| | 2018-04-17 08:32:14.872              |
|           |           | This may not exist if the tast is  |br| |                                      |
|           |           | not completed.                          |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| reason    | string    | An optional reason string that     |br| | No destination available |br|        |
|           |           | describes why the task failed.          | to write backup                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://vbox-dev:8081/foglamp/task/latest
  { "tasks": [ { "exitCode": 0,
                 "id": "a3759550-43e5-46b3-8048-e906847fc565",
                 "state": "Complete",
                 "pid": 16293,
                 "reason": "",
                 "name": "certificate checker",
                 "endTime": "2018-04-17 09:05:00.081",
                 "startTime": "2018-04-17 09:05:00.011" },
               { "exitCode": 0,
                 "id": "71bbc064-bb05-46c4-8059-5d70fc534ecf",
                 "state": "Complete",
                 "pid": 19806,
                 "reason": "",
                 "name": "purge",
                 "endTime": "2018-04-17 14:32:00.404",
                 "startTime": "2018-04-17 14:31:59.849" },
                 ... ] }
  $
  $ curl -X GET http://vbox-dev:8081/foglamp/task/latest?name=purge
  { "tasks": [ { "exitCode": 0,
                 "id": "71bbc064-bb05-46c4-8059-5d70fc534ecf",
                 "state": "Complete",
                 "pid": 19806,
                 "reason": "",
                 "name": "purge",
                 "endTime": "2018-04-17 14:32:00.404622",
                 "startTime": "2018-04-17 14:31:59.849690" ] }
   $


GET task by ID
~~~~~~~~~~~~~~

``GET /foglamp/task/<id>`` - return the task information for the given task


**Path Parameters**

- **id** - the uuid of the task whose data should be returned.


**Response Payload**

The response payload is a JSON object containing the task details.

+-----------+-----------+-----------------------------------------+--------------------------------------+
| Name      | Type      | Description                             | Example                              |
+===========+===========+=========================================+======================================+
| id        | string    | A unique identifier for the task.  |br| | 0a787bf3-4f48-4235-ae9a-2816f8ac76cc |
|           |           | This takes the form of a uuid and  |br| |                                      |
|           |           | not a Linux process id as the ID’s |br| |                                      |
|           |           | must survive restarts and failovers     |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| name      | string    | The name of the task                    | purge                                |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| state     | string    | The current state of the task           | Running                              |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| startTime | timestamp | The date and time the task started      | 2018-04-17 08:32:15.071              |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| endTime   | timestamp | The date and time the task ended   |br| | 2018-04-17 08:32:14.872              |
|           |           | This may not exist if the tast is  |br| |                                      |
|           |           | not completed.                          |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| reason    | string    | An optional reason string that     |br| | No destination available |br|        |
|           |           | describes why the task failed.          | to write backup                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://vbox-dev:8081/foglamp/task/0aadfb7d-73c1-4ac0-901c-81773b5583c1
  { "exitCode": 0,
    "id": "0aadfb7d-73c1-4ac0-901c-81773b5583c1",
    "state": "Complete",
    "reason": "",
    "name": "purge",
    "endTime": "2018-04-17 13:32:00.243",
    "startTime": "2018-04-17 13:31:59.848"
  }
  $


Cancel task by ID
~~~~~~~~~~~~~~~~~

``POST /foglamp/task/<id>/cancel`` - cancel a task


**Path Parameters**

- **id** - the uuid of the task to cancel.


**Response Payload**

The response payload is a JSON object with the details of the cancelled task.

+-----------+-----------+-----------------------------------------+--------------------------------------+
| Name      | Type      | Description                             | Example                              |
+===========+===========+=========================================+======================================+
| id        | string    | A unique identifier for the task.  |br| | 0a787bf3-4f48-4235-ae9a-2816f8ac76cc |
|           |           | This takes the form of a uuid and  |br| |                                      |
|           |           | not a Linux process id as the ID’s |br| |                                      |
|           |           | must survive restarts and failovers     |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| name      | string    | The name of the task                    | purge                                |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| state     | string    | The current state of the task           | Running                              |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| startTime | timestamp | The date and time the task started      | 2018-04-17 08:32:15.071              |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| endTime   | timestamp | The date and time the task ended   |br| | 2018-04-17 08:32:14.872              |
|           |           | This may not exist if the tast is  |br| |                                      |
|           |           | not completed.                          |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| reason    | string    | An optional reason string that     |br| | No destination available |br|        |
|           |           | describes why the task failed.          | to write backup                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+


**Example**

.. code-block:: console

  $ curl -X POST http://vbox-dev:8081/foglamp/task/0aadfb7d-73c1-4ac0-901c-81773b5583c1/cancel
  { "id": "0aadfb7d-73c1-4ac0-901c-81773b5583c1",
    "state": "Cancelled",
    "reason": "",
    "name": "purge",
    "endTime": "2018-04-17 13:32:00.243",
    "startTime": "2018-04-17 13:31:59.848"
  }
  $


User API Reference
==================

This section presents the list of user API methods in alphabetical order.



