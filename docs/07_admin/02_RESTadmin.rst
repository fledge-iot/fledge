.. REST API Guide
.. https://docs.google.com/document/d/1JJDP7g25SWerNVCxgff02qp9msHbqA9nt3RAFx8-Qng

.. |br| raw:: html

   <br />

.. |ar| raw:: html

   <div align="right">

.. Images


.. Links


.. =============================================


****************************
Administration API Reference
****************************

This section presents the list of administrative API methods in alphabetical order.


Audit Trail
===========

The audit trail API is used to interact with the audit trail log tables in the storage microservice. In FogLAMP, log information is stored in the system log where the microservice is hosted. All the relevant information used for auditing are instead stored inside FogLAMP and they are accessible through the Admin REST API. The API allows the reading but also the addition of extra audit logs, as if such logs are created within the system.


audit
-----

The *audit* methods implement the audit trail, they are used to create and retrieve audit logs.


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

|br|


POST Audit Entries
~~~~~~~~~~~~~~~~~~

``POST /foglamp/audit`` - create a new audit trail entry.

The purpose of the create method on an audit trail entry is to allow a user interface or an application that is using the FogLAMP API to utilize the FogLAMP audit trail and notification mechanism to raise user defined audit trail entries.


**Request Payload**

The request payload is a JSON object with the audit trail entry minus the timestamp.

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
  $ curl -X GET http://localhost:8081/foglamp/audit?severity=FAILURE
  { "totalCount": 1,
    "audit": [ { "timestamp": "2018-04-16 18:32:28.427",
                 "source"   :    "LocalMonitor",
                 "details"  : { "message": "Internal System Error" },
                 "severity" : "FAILURE" }
             ]
  }
  $

|br|


Configuration Management
========================

Configuration management in an important aspect of the REST API, however due to the discoverable form of the configuration of FogLAMP the API itself is fairly small.

The configuration REST API interacts with the configuration manager to create, retrieve, update and delete the configuration categories and values. Specifically all updates must go via the management layer as this is used to trigger the notifications to the components that have registered interest in configuration categories. This is the means by which the dynamic reconfiguration of FogLAMP is achieved.


category
--------

The *category* interface is part of the Configuration Management for FogLAMP and it is used to create, retrieve, update and delete configuration categories and items.


GET categor(ies)
~~~~~~~~~~~~~~~~

``GET /foglamp/category`` - return the list of known categories in the configuration database


**Response Payload**

The response payload is a JSON object with an array of JSON objects, one per valid category.

+-------------+--------+------------------------------------------------+------------------+
| Name        | Type   | Description                                    | Example          |
+=============+========+================================================+==================+
| key         | string | The category key, each category |br|           | network          |
|             |        | has a unique textual key that defines it.      |                  |
+-------------+--------+------------------------------------------------+------------------+
| description | string | A description of the category that may be |br| | Network Settings |
|             |        | used for display purposes.                     |                  |
+-------------+--------+------------------------------------------------+------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://localhost:8081/foglamp/category
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
                    { "key"         : "SEND_PR_4",
                      "description" : "OCS North Plugin Configuration" },
                    { "key"         : "SMNTR",
                      "description" : "Service Monitor configuration" },
                    { "key"         : "South",
                      "description" : "South Service configuration" },
                    { "key"         : "rest_api",
                      "description" : "The FogLAMP Admin and User REST API" },
                    { "key"         : "service",
                      "description" : "The FogLAMP service configuration" } ] }
  $

|br|


GET category
~~~~~~~~~~~~

``GET /foglamp/category/{name}`` - return the configuration items in the given category.


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

  $ curl -X GET http://localhost:8081/foglamp/category/rest_api
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

|br|


GET category item
~~~~~~~~~~~~~~~~~

``GET /foglamp/category/{name}/{item}`` - return the configuration item in the given category.


**Path Parameters**

- **name** - the name of one of the categories returned from the GET /foglamp/category call.
- **item** - the item within the category to return.


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

  $ curl -X GET http://localhost:8081/foglamp/category/rest_api/httpsPort
  { "type": "integer",
    "default": "1995",
    "description": "The port to accept HTTPS connections on",
    "value": "1995"
  }
  $

|br|


PUT category item
~~~~~~~~~~~~~~~~~

``PUT /foglamp/category/{name}/{item}`` - set the configuration item value in the given category.


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

  $ curl -X PUT http://localhost:8081/foglamp/category/rest_api/httpsPort \
    -d '{ "value" : "1996" }'
  { "default": "1995",
    "type": "integer",
    "description": "The port to accept HTTPS connections on",
    "value": "1996"
  }
  $

|br|


DELETE category item
~~~~~~~~~~~~~~~~~~~~

``DELETE /foglamp/category/{name}/{item}/value`` - unset the value of the configuration item in the given category.

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

  $ curl -X DELETE http://localhost:8081/foglamp/category/rest_api/httpsPort/value
  { "default": "1995",
    "type": "integer",
    "description": "The port to accept HTTPS connections on",
    "value": "1995"
  }
  $

|br|


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

  $ curl -X POST http://localhost:8081/foglamp/category \
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

|br|


Task Management
===============

The task management API’s allow an administrative user to monitor and control the tasks that are started by the task scheduler either from a schedule or as a result of an API request.


task
----

The *task* interface allows an administrative user to monitor and control FogLAMP tasks.


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

  $ curl -X GET http://localhost:8081/foglamp/task
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
  $ curl -X GET http://localhost:8081/foglamp/task?name=purge
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
  $ curl -X GET http://localhost:8081/foglamp/task?state=complete
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

|br|


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

  $ curl -X GET http://localhost:8081/foglamp/task/latest
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
  $ curl -X GET http://localhost:8081/foglamp/task/latest?name=purge
  { "tasks": [ { "exitCode": 0,
                 "id": "71bbc064-bb05-46c4-8059-5d70fc534ecf",
                 "state": "Complete",
                 "pid": 19806,
                 "reason": "",
                 "name": "purge",
                 "endTime": "2018-04-17 14:32:00.404622",
                 "startTime": "2018-04-17 14:31:59.849690" ] }
   $

|br|


GET task by ID
~~~~~~~~~~~~~~

``GET /foglamp/task/{id}`` - return the task information for the given task


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

  $ curl -X GET http://localhost:8081/foglamp/task/0aadfb7d-73c1-4ac0-901c-81773b5583c1
  { "exitCode": 0,
    "id": "0aadfb7d-73c1-4ac0-901c-81773b5583c1",
    "state": "Complete",
    "reason": "",
    "name": "purge",
    "endTime": "2018-04-17 13:32:00.243",
    "startTime": "2018-04-17 13:31:59.848"
  }
  $

|br|


Cancel task by ID
~~~~~~~~~~~~~~~~~

``PUT /foglamp/task/{id}/cancel`` - cancel a task


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

  $ curl -X PUT http://localhost:8081/foglamp/task/0aadfb7d-73c1-4ac0-901c-81773b5583c1/cancel
  { "id": "0aadfb7d-73c1-4ac0-901c-81773b5583c1",
    "state": "Cancelled",
    "reason": "",
    "name": "purge",
    "endTime": "2018-04-17 13:32:00.243",
    "startTime": "2018-04-17 13:31:59.848"
  }
  $

|br|


Other Administrative API calls
==============================


ping
----

The *ping* interface gives a basic confidence check that the FogLAMP appliance is running and the API aspect of the appliance is functional. It is designed to be a simple test that can  be applied by a user or by an HA monitoring system to test the liveness and responsiveness of the system.


GET ping
~~~~~~~~

``GET /foglamp/ping`` - return liveness of FogLAMP

*NOTE:* the GET method can be executed without authentication even when authentication is required. This behaviour is configurable via a configuration option.


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


statistics
----------

The *statistics* interface allows the retrieval of live statistics and statistical history for the FogLAMP device.


GET statistics
~~~~~~~~~~~~~~

``GET /foglamp/statistics`` - return a general set of statistics


**Response Payload**

The response payload is a JSON document with statistical information (all numerical), these statistics are absolute counts since FogLAMP started.

+------------------------+-----------------------------------------------------------------------------+
| Key                    | Description                                                                 |
+========================+=============================================================================+
| BUFFERED               | The number of readings currently in the FogLAMP buffer                      |
+------------------------+-----------------------------------------------------------------------------+
| DISCARDED              | The number of readings discarded at the input side by FogLAMP,       |br|   |
|                        | i.e. discarded before being  placed in the buffer. This may be due   |br|   |
|                        | to some error in the readings themselves.                                   |
+------------------------+-----------------------------------------------------------------------------+
| PURGED                 | The number of readings removed from the buffer by the *Purge* task          |
+------------------------+-----------------------------------------------------------------------------+
| READINGS               | The number of readings received by FogLAMP since startup                    |
+------------------------+-----------------------------------------------------------------------------+
| SENT_1                 | The number of readings sent to the PI system via the OMF plugin             |
+------------------------+-----------------------------------------------------------------------------+
| SENT_2                 | The number of statistics sent to the PI system via the OMF plugin           |
+------------------------+-----------------------------------------------------------------------------+
| SENT_4                 | The number of readings sent to the OSIsoft Cloud Service via the OCS plugin |
+------------------------+-----------------------------------------------------------------------------+
| UNSENT                 | The number of readings filtered out in the send process                     |
+------------------------+-----------------------------------------------------------------------------+
| UNSNPURGED             | The number of readings that were purged from the buffer before being sent   |
+------------------------+-----------------------------------------------------------------------------+
| *ASSET-CODE*           | The number of readings received by FogLAMP since startup               |br| |
|                        | with name *asset-code*                                                      |
+------------------------+-----------------------------------------------------------------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/statistics
  [ { "description" : "The number of readings currently in the FogLAMP buffer",
      "key"         : "BUFFERED",
      "value"       : 0 },
  ...
    { "description" : "The number of readings received by FogLAMP since startup for sensor FOGBENCH/ACCELEROMETER",
      "key"         : "FOGBENCH/ACCELEROMETER",
      "value"       : 2 },
  ... ]
  $


GET statistics/history
~~~~~~~~~~~~~~~~~~~~~~

``GET /foglamp/statistics/history`` - return a historical set of statistics. This interface is normally used to check if a set of sensors or devices are sending data to FogLAMP, by comparing the recent statistics and the number of readings received for an asset.


**Reguest Parameters**

- **limit** - limit the result set to the *N* most recent entries.


**Response Payload**

A JSON document containing an array of statistical information, these statistics are delta counts since the previous entry in the array. The time interval between values is a constant defined that runs the gathering process which populates the history statistics in the storage layer.

+---------------------------+-----------------------------------------------------------------------------+
| Key                       | Description                                                                 |
+===========================+=============================================================================+
| interval                  | The interval in seconds between successive statistics values                |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].BUFFERED     | The number of readings currently in the FogLAMP buffer                      |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].DISCARDED    | The number of readings discarded at the input side by FogLAMP,       |br|   |
|                           | i.e. discarded before being  placed in the buffer. This may be due   |br|   |
|                           | to some error in the readings themselves.                                   |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].PURGED       | The number of readings removed from the buffer by the *Purge* task          |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].READINGS     | The number of readings received by FogLAMP since startup                    |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].SENT_1       | The number of readings sent to the PI system via the OMF plugin             |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].SENT_2       | The number of statistics sent to the PI system via the OMF plugin           |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].SENT_4       | The number of readings sent to the OSIsoft Cloud Service via the OCS plugin |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].UNSENT       | The number of readings filtered out in the send process                     |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].UNSNPURGED   | The number of readings that were purged from the buffer before being sent   |
+---------------------------+-----------------------------------------------------------------------------+
| statistics[].*ASSET-CODE* | The number of readings received by FogLAMP since startup               |br| |
|                           | with name *asset-code*                                                      |
+---------------------------+-----------------------------------------------------------------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/statistics/history?limit=2
  { "interval"   : 15,
    "statistics" : [ { "READINGS": 0,
                       "FOGBENCH/LUXOMETER": 0,
                       "DISCARDED": 0,
                       "FOGBENCH/HUMIDITY": 0,
                       "FOGBENCH/ACCELEROMETER": 0,
                       "UNSENT": 0,
                       "SENT_2": 0,
                       "SENT_4": 0,
                       "FOGBENCH/TEMPERATURE": 0,
                       "FOGBENCH/GYROSCOPE": 0,
                       "UNSNPURGED": 0,
                       "BUFFERED": 0,
                       "FOGBENCH/MOUSE": 0,
                       "FOGBENCH/MAGNETOMETER": 0,
                       "PURGED": 0,
                       "FOGBENCH/WALL CLOCK": 0,
                       "SENT_1": 0,
                       "FOGBENCH/PRESSURE": 0,
                       "FOGBENCH/SWITCH": 0,
                       "history_ts": "2018-05-15 22:39:10.374" },
                     { "READINGS": 0,
                       "FOGBENCH/LUXOMETER": 0,
                       "DISCARDED": 0,
                       "FOGBENCH/HUMIDITY": 0,
                       "FOGBENCH/ACCELEROMETER": 0,
                       "UNSENT": 0,
                       "SENT_2": 0,
                       "SENT_4": 0,
                       "FOGBENCH/TEMPERATURE": 0,
                       "FOGBENCH/GYROSCOPE": 0,
                       "UNSNPURGED": 0,
                       "BUFFERED": 0,
                       "FOGBENCH/MOUSE": 0,
                       "FOGBENCH/MAGNETOMETER": 0,
                       "PURGED": 0,
                       "FOGBENCH/WALL CLOCK": 0,
                       "SENT_1": 0,
                       "FOGBENCH/PRESSURE": 0,
                       "FOGBENCH/SWITCH": 0,
                       "history_ts": "2018-05-15 22:38:55.653" } ]
  $


