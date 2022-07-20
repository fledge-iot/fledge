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

The audit trail API is used to interact with the audit trail log tables in the storage microservice. In Fledge, log information is stored in the system log where the microservice is hosted. All the relevant information used for auditing are instead stored inside Fledge and they are accessible through the Admin REST API. The API allows the reading but also the addition of extra audit logs, as if such logs are created within the system.


audit
-----

The *audit* methods implement the audit trail, they are used to create and retrieve audit logs.


GET Audit Entries
~~~~~~~~~~~~~~~~~

``GET /fledge/audit`` - return a list of audit trail entries sorted with most recent first.

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

  $ curl -s http://localhost:8081/fledge/audit?limit=2
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
  $ curl -s http://localhost:8081/fledge/audit?source=SRVUN&limit=1
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

``POST /fledge/audit`` - create a new audit trail entry.

The purpose of the create method on an audit trail entry is to allow a user interface or an application that is using the Fledge API to utilize the Fledge audit trail and notification mechanism to raise user defined audit trail entries.


**Request Payload**

The request payload is a JSON object with the audit trail entry minus the timestamp.

+-----------+-----------+-----------------------------------------------+---------------------------+
| Name      | Type      | Description                                   | Example                   |
+===========+===========+===============================================+===========================+
| source    | string    | The source of the audit trail entry.          | LOGGN                     |
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
| source    | string    | The source of the audit trail entry.          | LOGGN                     |
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

  $ curl -X POST http://localhost:8081/fledge/audit \
  -d '{ "severity": "FAILURE", "details": { "message": "Internal System Error" }, "source": "LOGGN" }'
  { "source": "LOGGN",
    "timestamp": "2018-04-17 11:49:55.480",
    "severity": "FAILURE",
    "details": { "message": "Internal System Error" }
  }
  $
  $ curl -X GET http://localhost:8081/fledge/audit?severity=FAILURE
  { "totalCount": 1,
    "audit": [ { "timestamp": "2018-04-16 18:32:28.427",
                 "source"   :    "LOGGN",
                 "details"  : { "message": "Internal System Error" },
                 "severity" : "FAILURE" }
             ]
  }
  $

|br|


Configuration Management
========================

Configuration management in an important aspect of the REST API, however due to the discoverable form of the configuration of Fledge the API itself is fairly small.

The configuration REST API interacts with the configuration manager to create, retrieve, update and delete the configuration categories and values. Specifically all updates must go via the management layer as this is used to trigger the notifications to the components that have registered interest in configuration categories. This is the means by which the dynamic reconfiguration of Fledge is achieved.


category
--------

The *category* interface is part of the Configuration Management for Fledge and it is used to create, retrieve, update and delete configuration categories and items.


GET categor(ies)
~~~~~~~~~~~~~~~~

``GET /fledge/category`` - return the list of known categories in the configuration database


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
| displayName | string | Name of the category that may be |br|          | Network Settings |
|             |        | used for display purposes.                     |                  |
+-------------+--------+------------------------------------------------+------------------+

**Example**

.. code-block:: console

  $ curl -X GET http://localhost:8081/fledge/category
  {
    "categories":
    [
      {
        "key": "SCHEDULER",
         "description": "Scheduler configuration",
         "displayName": "Scheduler"
      },
      {
        "key": "SMNTR",
        "description": "Service Monitor",
        "displayName": "Service Monitor"
      },
      {
        "key": "rest_api",
        "description": "Fledge Admin and User REST API",
        "displayName": "Admin API"
      },
      {
        "key": "service",
        "description": "Fledge Service",
        "displayName": "Fledge Service"
      },
      {
        "key": "Installation",
        "description": "Installation",
        "displayName": "Installation"
      },
      {
        "key": "General",
        "description": "General",
        "displayName": "General"
      },
      {
        "key": "Advanced",
        "description": "Advanced",
        "displayName": "Advanced"
      },
      {
        "key": "Utilities",
        "description": "Utilities",
        "displayName": "Utilities"
      }
    ]
  }
  $

|br|


GET category
~~~~~~~~~~~~

``GET /fledge/category/{name}`` - return the configuration items in the given category.


**Path Parameters**

- **name** is the name of one of the categories returned from the GET /fledge/category call.


**Response Payload**

The response payload is a set of configuration items within the category, each item is a JSON object with the following set of properties.

.. list-table::
    :widths: 20 20 50 50
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - description
      - string
      - A description of the configuration item that may be used in a user interface.
      - The IPv4 network address of the Fledge server
    * - type
      - string
      - A type that may be used by a user interface to know how to display an item.
      - IPv4
    * - default
      - string
      - An optional default value for the configuration item.
      - 127.0.0.1
    * - displayName
      - string
      - Name of the category that may be used for display purposes.
      - IPv4 address
    * - order
      - integer
      - Order at which category name will be displayed.
      - 1
    * - value
      - string
      - The current configured value of the configuration item. This may be empty if no value has been set.
      - 192.168.0.27


**Example**

.. code-block:: console

  $ curl -X GET http://localhost:8081/fledge/category/rest_api
  {
    "enableHttp": {
       "description": "Enable HTTP (disable to use HTTPS)",
       "type": "boolean",
       "default": "true",
       "displayName": "Enable HTTP",
       "order": "1",
       "value": "true"
    },
    "httpPort": {
       "description": "Port to accept HTTP connections on",
       "type": "integer",
       "default": "8081",
       "displayName": "HTTP Port",
       "order": "2",
       "value": "8081"
    },
    "httpsPort": {
       "description": "Port to accept HTTPS connections on",
       "type": "integer",
       "default": "1995",
       "displayName": "HTTPS Port",
       "order": "3",
       "validity": "enableHttp==\"false\"",
       "value": "1995"
    },
    "certificateName": {
      "description": "Certificate file name",
      "type": "string",
      "default": "fledge",
      "displayName": "Certificate Name",
      "order": "4",
      "validity": "enableHttp==\"false\"",
			"value": "fledge"
    },
    "authentication": {
      "description": "API Call Authentication",
      "type": "enumeration",
      "options": [
        "mandatory",
        "optional"
      ],
      "default": "optional",
      "displayName": "Authentication",
       "order": "5",
       "value": "optional"
    },
    "authMethod": {
      "description": "Authentication method",
      "type": "enumeration",
      "options": [
        "any",
        "password",
        "certificate"
      ],
      "default": "any",
      "displayName": "Authentication method",
      "order": "6",
      "value": "any"
    },
    "authCertificateName": {
      "description": "Auth Certificate name",
      "type": "string",
      "default": "ca",
      "displayName": "Auth Certificate",
      "order": "7",
      "value": "ca"
    },
    "allowPing": {
      "description": "Allow access to ping, regardless of the authentication required and authentication header",
      "type": "boolean",
      "default": "true",
      "displayName": "Allow Ping",
      "order": "8",
      "value": "true"
    },
    "passwordChange": {
      "description": "Number of days after which passwords must be changed",
      "type": "integer",
      "default": "0",
      "displayName": "Password Expiry Days",
      "order": "9",
      "value": "0"
    },
    "authProviders": {
       "description": "Authentication providers to use for the interface (JSON array object)",
       "type": "JSON",
       "default": "{\"providers\": [\"username\", \"ldap\"] }",
       "displayName": "Auth Providers",
       "order": "10",
       "value": "{\"providers\": [\"username\", \"ldap\"] }"
    }
	}
  $

|br|


GET category item
~~~~~~~~~~~~~~~~~

``GET /fledge/category/{name}/{item}`` - return the configuration item in the given category.


**Path Parameters**

- **name** - the name of one of the categories returned from the GET /fledge/category call.
- **item** - the item within the category to return.


**Response Payload**

The response payload is a configuration item within the category, each item is a JSON object with the following set of properties.

.. list-table::
    :widths: 20 20 50 50
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - description
      - string
      - A description of the configuration item that may be used in a user interface.
      - The IPv4 network address of the Fledge server
    * - type
      - string
      - A type that may be used by a user interface to know how to display an item.
      - IPv4
    * - default
      - string
      - An optional default value for the configuration item.
      - 127.0.0.1
    * - displayName
      - string
      - Name of the category that may be used for display purposes.
      - IPv4 address
    * - order
      - integer
      - Order at which category name will be displayed.
      - 1
    * - value
      - string
      - The current configured value of the configuration item. This may be empty if no value has been set.
      - 192.168.0.27


**Example**

.. code-block:: console

  $ curl -X GET http://localhost:8081/fledge/category/rest_api/httpsPort
  {
      "description": "Port to accept HTTPS connections on",
      "type": "integer",
      "default": "1995",
      "displayName": "HTTPS Port",
      "order": "3",
      "validity": "enableHttp==\"false\"",
      "value": "1995"
  }

  $

|br|


PUT category item
~~~~~~~~~~~~~~~~~

``PUT /fledge/category/{name}/{item}`` - set the configuration item value in the given category.


**Path Parameters**

- **name** - the name of one of the categories returned from the GET /fledge/category call.
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

.. list-table::
    :widths: 20 20 50 50
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - description
      - string
      - A description of the configuration item that may be used in a user interface.
      - The IPv4 network address of the Fledge server
    * - type
      - string
      - A type that may be used by a user interface to know how to display an item.
      - IPv4
    * - default
      - string
      - An optional default value for the configuration item.
      - 127.0.0.1
    * - displayName
      - string
      - Name of the category that may be used for display purposes.
      - IPv4 address
    * - order
      - integer
      - Order at which category name will be displayed.
      - 1
    * - value
      - string
      - The current configured value of the configuration item. This may be empty if no value has been set.
      - 192.168.0.27


**Example**

.. code-block:: console

  $ curl -X PUT http://localhost:8081/fledge/category/rest_api/httpsPort \
    -d '{ "value" : "1996" }'
  {
    "description": "Port to accept HTTPS connections on",
    "type": "integer",
    "default": "1995",
    "displayName": "HTTPS Port",
    "order": "3",
    "validity": "enableHttp==\"false\"",
    "value": "1996"
  }
  $

|br|


DELETE category item
~~~~~~~~~~~~~~~~~~~~

``DELETE /fledge/category/{name}/{item}/value`` - unset the value of the configuration item in the given category.

This will result in the value being returned to the default value if one is defined. If not the value will be blank, i.e. the value property of the JSON object will exist with an empty value.


**Path Parameters**

- **name** - the name of one of the categories returned from the GET /fledge/category call.
- **item** - the the item within the category to return.


**Response Payload**

The response payload is the newly updated configuration item within the category, the item is a JSON object object with the following set of properties.

.. list-table::
    :widths: 20 20 50 50
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - description
      - string
      - A description of the configuration item that may be used in a user interface.
      - The IPv4 network address of the Fledge server
    * - type
      - string
      - A type that may be used by a user interface to know how to display an item.
      - IPv4
    * - default
      - string
      - An optional default value for the configuration item.
      - 127.0.0.1
    * - displayName
      - string
      - Name of the category that may be used for display purposes.
      - IPv4 address
    * - order
      - integer
      - Order at which category name will be displayed.
      - 1
    * - value
      - string
      - The current configured value of the configuration item. This may be empty if no value has been set.
      - 127.0.0.1


**Example**

.. code-block:: console

  $ curl -X DELETE http://localhost:8081/fledge/category/rest_api/httpsPort/value
  {
    "description": "Port to accept HTTPS connections on",
    "type": "integer",
    "default": "1995",
    "displayName": "HTTPS Port",
    "order": "3",
    "validity": "enableHttp==\"false\"",
    "value": "1995"
  }
  $

|br|


POST category
~~~~~~~~~~~~~

``POST /fledge/category`` - creates a new category


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

  $ curl -X POST http://localhost:8081/fledge/category
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

The *task* interface allows an administrative user to monitor and control Fledge tasks.


GET task
~~~~~~~~

``GET /fledge/task`` - return the list of all known task running or completed


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
|           |           | This may not exist if the task is  |br| |                                      |
|           |           | not completed.                          |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| exitCode  | integer   | Exit Code of the task.             |br| | 0                                    |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| reason    | string    | An optional reason string that     |br| | No destination available |br|        |
|           |           | describes why the task failed.          | to write backup                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://localhost:8081/fledge/task
  {
  "tasks": [
    {
      "id": "a9967d61-8bec-4d0b-8aa1-8b4dfb1d9855",
      "name": "stats collection",
      "processName": "stats collector",
      "state": "Complete",
      "startTime": "2020-05-28 09:21:58.650",
      "endTime": "2020-05-28 09:21:59.155",
      "exitCode": 0,
      "reason": ""
    },
    {
      "id": "7706b23c-71a4-410a-a03a-9b517dcd8c93",
      "name": "stats collection",
      "processName": "stats collector",
      "state": "Complete",
      "startTime": "2020-05-28 09:22:13.654",
      "endTime": "2020-05-28 09:22:14.160",
      "exitCode": 0,
      "reason": ""
    },
    ... ] }
  $
  $ curl -X GET http://localhost:8081/fledge/task?name=purge
  {
  "tasks": [
    {
      "id": "c24e006d-22f2-4c52-9f3a-391a9b17b6d6",
      "name": "purge",
      "processName": "purge",
      "state": "Complete",
      "startTime": "2020-05-28 09:44:00.175",
      "endTime": "2020-05-28 09:44:13.915",
      "exitCode": 0,
      "reason": ""
    },
    {
      "id": "609f35e6-4e89-4749-ac17-841ae3ee2b31",
      "name": "purge",
      "processName": "purge",
      "state": "Complete",
      "startTime": "2020-05-28 09:44:15.165",
      "endTime": "2020-05-28 09:44:28.154",
      "exitCode": 0,
      "reason": ""
    },
  ... ] }
  $
  $ curl -X GET http://localhost:8081/fledge/task?state=complete
  {
  "tasks": [
    {
      "id": "a9967d61-8bec-4d0b-8aa1-8b4dfb1d9855",
      "name": "stats collection",
      "processName": "stats collector",
      "state": "Complete",
      "startTime": "2020-05-28 09:21:58.650",
      "endTime": "2020-05-28 09:21:59.155",
      "exitCode": 0,
      "reason": ""
    },
    {
      "id": "7706b23c-71a4-410a-a03a-9b517dcd8c93",
      "name": "stats collection",
      "processName": "stats collector",
      "state": "Complete",
      "startTime": "2020-05-28 09:22:13.654",
      "endTime": "2020-05-28 09:22:14.160",
      "exitCode": 0,
      "reason": ""
    },
    ... ] }
   $

|br|


GET task latest
~~~~~~~~~~~~~~~

``GET /fledge/task/latest`` - return the list of most recent task execution for each name.

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
|           |           | This may not exist if the task is  |br| |                                      |
|           |           | not completed.                          |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| exitCode  | integer   | Exit Code of the task.             |br| | 0                                    |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| reason    | string    | An optional reason string that     |br| | No destination available |br|        |
|           |           | describes why the task failed.          | to write backup                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| pid       | integer   | Process ID of the task.            |br| | 17481                                |
+-----------+-----------+-----------------------------------------+--------------------------------------+

**Example**

.. code-block:: console

  $ curl -X GET http://localhost:8081/fledge/task/latest
  {
  "tasks": [
    {
      "id": "ea334d3b-8a33-4a29-845c-8be50efd44a4",
      "name": "certificate checker",
      "processName": "certificate checker",
      "state": "Complete",
      "startTime": "2020-05-28 09:35:00.009",
      "endTime": "2020-05-28 09:35:00.057",
      "exitCode": 0,
      "reason": "",
      "pid": 17481
    },
    {
      "id": "794707da-dd32-471e-8537-5d20dc0f401a",
      "name": "stats collection",
      "processName": "stats collector",
      "state": "Complete",
      "startTime": "2020-05-28 09:37:28.650",
      "endTime": "2020-05-28 09:37:29.138",
      "exitCode": 0,
      "reason": "",
      "pid": 17926
    }
    ... ] }
  $
  $ curl -X GET http://localhost:8081/fledge/task/latest?name=purge
  {
  "tasks":  [
    {
      "id": "609f35e6-4e89-4749-ac17-841ae3ee2b31",
      "name": "purge",
      "processName": "purge",
      "state": "Complete",
      "startTime": "2020-05-28 09:44:15.165",
      "endTime": "2020-05-28 09:44:28.154",
      "exitCode": 0,
      "reason": "",
      "pid": 20914
    }
  	]
  }
  $

|br|


GET task by ID
~~~~~~~~~~~~~~

``GET /fledge/task/{id}`` - return the task information for the given task


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
|           |           | This may not exist if the task is  |br| |                                      |
|           |           | not completed.                          |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| exitCode  | integer   | Exit Code of the task.             |br| | 0                                    |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| reason    | string    | An optional reason string that     |br| | No destination available |br|        |
|           |           | describes why the task failed.          | to write backup                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+


**Example**

.. code-block:: console

  $ curl -X GET http://localhost:8081/fledge/task/ea334d3b-8a33-4a29-845c-8be50efd44a4
  {
    "id": "ea334d3b-8a33-4a29-845c-8be50efd44a4",
    "name": "certificate checker",
    "processName": "certificate checker",
    "state": "Complete",
    "startTime": "2020-05-28 09:35:00.009",
    "endTime": "2020-05-28 09:35:00.057",
    "exitCode": 0,
    "reason": ""
  }
  $

|br|


Cancel task by ID
~~~~~~~~~~~~~~~~~

``PUT /fledge/task/{id}/cancel`` - cancel a task


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
|           |           | This may not exist if the task is  |br| |                                      |
|           |           | not completed.                          |                                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+
| reason    | string    | An optional reason string that     |br| | No destination available |br|        |
|           |           | describes why the task failed.          | to write backup                      |
+-----------+-----------+-----------------------------------------+--------------------------------------+


**Example**

.. code-block:: console

  $ curl -X PUT http://localhost:8081/fledge/task/ea334d3b-8a33-4a29-845c-8be50efd44a4/cancel
  {"id": "ea334d3b-8a33-4a29-845c-8be50efd44a4", "message": "Task cancelled successfully"}
  $

|br|


Other Administrative API calls
==============================

shutdown
--------

The *shutdown* option will causes all fledge services to be shutdown cleanly. Any data held in memory buffers within the services will be sent to the storage layer and the Fledge plugins will persist any state required when they restart.

.. code-block:: console

   $ curl -X PUT /fledge/shutdown

.. note::

   If an in memory storage layer is configured this will **not** be stored to any permanant storage and the contents of the memory storage layer will be lost.

restart
-------

The *restart* option will causes all fledge services to be shutdown cleanly and then restarted. Any data held in memory buffers within the services will be sent to the storage layer and the Fledge plugins will persist any state required when they restart.

.. code-block:: console

   $ curl -X PUT /fledge/restart

.. note::

   If an in memory storage layer is configured this will **not** be stored to any permanant storage and the contents of the memory storage layer will be lost.

ping
----

The *ping* interface gives a basic confidence check that the Fledge appliance is running and the API aspect of the appliance is functional. It is designed to be a simple test that can  be applied by a user or by an HA monitoring system to test the liveness and responsiveness of the system.


GET ping
~~~~~~~~

``GET /fledge/ping`` - return liveness of Fledge

*NOTE:* the GET method can be executed without authentication even when authentication is required. This behaviour is configurable via a configuration option.


**Response Payload**

The response payload is some basic health information in a JSON object.

.. list-table::
    :widths: 20 20 80 20
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - uptime
      - numeric
      - Time in seconds since Fledge started
      - 2113.076449394226
    * - dataRead
      - numeric
      - A count of the number of sensor readings
      - 1452
    * - dataSent
      - numeric
      - A count of the number of readings sent to PI
      - 347
    * - dataPurged
      - numeric
      - A count of the number of readings purged
      - 226
    * - authenticationOptional
      - boolean
      - When true, the REST API does not require authentication. When false, users must successfully login in order to call the rest API. Default is *true*
      - true
    * - serviceName
      - string
      - Name of service
      - Fledge
    * - hostName
      - string
      - Name of host machine
      - fledge
    * - ipAddresses
      - list
      - IPv4 and IPv6 address of host machine
      - ["10.0.0.0","123:234:345:456:567:678:789:890"]
    * - health
      - string
      - Health of Fledge services
      - "green"
    * - safeMode
      - boolean
      - True if Fledge is started in safe mode (only core and storage services will be started)
      - 2113.076449394226


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/ping
  {
    "uptime": 276818,
    "dataRead": 0,
    "dataSent": 0,
    "dataPurged": 0,
    "authenticationOptional": true,
    "serviceName": "Fledge",
    "hostName": "fledge",
    "ipAddresses": [
      "x.x.x.x",
      "x:x:x:x:x:x:x:x"
    ],
    "health": "green",
    "safeMode": false
  }
  $

