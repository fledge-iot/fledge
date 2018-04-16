.. REST API Guide
.. https://docs.google.com/document/d/1JJDP7g25SWerNVCxgff02qp9msHbqA9nt3RAFx8-Qng

.. |br| raw:: html

   <br />

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

``GET /foglamp/audit`` - returns a list of audit trail entries sorted with most recent first.

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

+-----------+-----------+-----------------------------------------------+-----------------------------+
| Name      | Type      | Description                                   | Example                     |
+===========+===========+===============================================+=============================+
| source    | string    | The source of the audit trail entry.          | LocalMonitor                |
+-----------+-----------+-----------------------------------------------+-----------------------------+
| severity  | string    | The severity of the event that triggered |br| | FAILURE                     |
|           |           | the audit trail entry to be written. |br|     |                             |
|           |           | This will be one of SUCCESS, FAILURE, |br|    |                             |
|           |           | WARNING or INFORMATION.                       |                             |
+-----------+-----------+-----------------------------------------------+-----------------------------+
| details   | object    | A JSON object that describes the detail |br|  | { "message" : |br|          |
|           |           | of the audit trail event.                     | "Engine oil pressure low" } |
+-----------+-----------+-----------------------------------------------+-----------------------------+


**Response Payload**

The response payload is the newly created audit trail entry.

+-----------+-----------+-----------------------------------------------+-----------------------------+
| Name      | Type      | Description                                   | Example                     |
+===========+===========+===============================================+=============================+
| timestamp | timestamp | The timestamp when the audit trail |br|       | 2018-04-16 14:33:18.215     |
|           |           | item was written.                             |                             |
+-----------+-----------+-----------------------------------------------+-----------------------------+
| source    | string    | The source of the audit trail entry.          | LocalMonitor                |
+-----------+-----------+-----------------------------------------------+-----------------------------+
| severity  | string    | The severity of the event that triggered |br| | FAILURE                     |
|           |           | the audit trail entry to be written. |br|     |                             |
|           |           | This will be one of SUCCESS, FAILURE, |br|    |                             |
|           |           | WARNING or INFORMATION.                       |                             |
+-----------+-----------+-----------------------------------------------+-----------------------------+
| details   | object    | A JSON object that describes the detail |br|  | { "message" : |br|          |
|           |           | of the audit trail event.                     | "Engine oil pressure low" } |
+-----------+-----------+-----------------------------------------------+-----------------------------+


**Example**

.. code-block:: console

  $ curl -X POST http://localhost:8081/foglamp/audit \
  -H 'Content-Type: application/json' \
  -d '{ "severity": "FAILURE", "details": { "message": "Engine oil pressure low" }, "source": "LocalMonitor" }'
  $ curl -X GET http://vbox-dev:8081/foglamp/audit?severity=FAILURE
  { "totalCount": 1,
    "audit": [ { "timestamp": "2018-04-16 18:32:28.427",
                 "source"   :    "LocalMonitor",
                 "details"  : { "message": "Engine oil pressure low" },
                 "severity" : "FAILURE" }
             ]
  }
  $


ping
----

The *ping* interface gives a basic confidence check that the FogLAMP appliance is running and the API aspect of the appliance if functional. It is designed to be a simple test that can  be applied by a user or by an HA monitoring system to test the liveness and responsiveness of the system.


GET ping
~~~~~~~~

``GET /foglamp/ping`` - returns liveness of FogLAMP

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


< END OF DOC> |br| |br| |br| |br| |br| |br| |br| |br|        


























audit
-----

The audit methods are used to retrieve and manage information in the audit trail, audit entries and notifications. The API interacts directly with the audit trail log tables in the storage layer with the exception of the create method which must go via the audit trail component in order that audit trail entries created via the API are treated in the same way as those created within the system.


GET Audit Entries
~~~~~~~~~~~~~~~~~

``GET /foglamp/audit`` - returns a list of audit trail entries sorted with most recent first.

**Request Parameters**

- **limit** - limit the number of audit entries returned to the number specified
- **skip** - skip the first n entries in the audit table, used with limit to implement paged interfaces
- **source** - filter the audit entries to be only those from the specified source
- **severity** - filter the audit entries to only those of the specified severity


**Response Payload**

The response payload is an array of JSON objects with the audit trail entries.

+-----------+-----------+------------------------------------------------+--------------------------------------------------------+
| Name      | Type      | Description                                    | Example                                                |
+===========+===========+================================================+========================================================+
| timestamp | timestamp | The timestamp when the audit trail |br|        | 2018-03-01T12:00:48.219183                             |
|           |           | item was written.                              |                                                        |
+-----------+-----------+------------------------------------------------+--------------------------------------------------------+
| source    | string    | The source of the audit trail entry.           | CoAP                                                   |
+-----------+-----------+------------------------------------------------+--------------------------------------------------------+
| severity  | string    | The severity of the event that triggered |br|  | FATAL                                                  |
|           |           | the audit trail entry to be written. |br|      |                                                        |
|           |           | This will be one of FATAL, ERROR, WARNING |br| |                                                        |
|           |           | or INFORMATION.                                |                                                        |
+-----------+-----------+------------------------------------------------+--------------------------------------------------------+
| details   | object    | A JSON object that describes the detail |br|   | { "message" : |br|                                     |
|           |           | of the audit trail event.                      | "Sensor readings discarded due to malformed payload" } |
+-----------+-----------+------------------------------------------------+--------------------------------------------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/audit | jq -c '.'
  { "totalCount" : 24,
    "audit"      : [ { "timestamp" : "2018-02-25 18:58:07.748322+00",
                       "source"    : "SRVRG",
                       "details"   : { "name" : "COAP" },
                       "severity"  : "INFORMATION" },
                     { "timestamp" : "2018-02-25 18:58:07.742927+00",
                       "source"    : "SRVRG",
                       "details"   : { "name" : "HTTP_SOUTH" },
                       "severity"  : "INFORMATION" },
                     { "timestamp" : "2018-02-25 18:58:07.390814+00",
                       "source"    : "START",
                       "details"   : {},
                       "severity"  : "INFORMATION" },
                     ...
                   ]
  }
  $ curl -s 'http://localhost:8081/foglamp/audit?limit=1&skip=1' | jq
  { "totalCount" : 24,
    "audit"      : [ { "timestamp" : "2018-02-25 18:58:07.742927+00",
                       "source"    : "SRVRG",
                       "details"   : { "name": "HTTP_SOUTH" },
                       "severity"  : "INFORMATION" }
                   ]
  }
  $ curl -s 'http://localhost:8081/foglamp/audit?source=SRVUN&limit=1' | jq
  { "totalCount" : 4,
    "audit"      : [ { "timestamp" : "2018-02-25 05:22:11.053845+00",
                       "source"    : "SRVUN",
                       "details"   : { "name": "COAP" },
                       "severity"  : "INFORMATION" }
                   ]
  }
  $


POST Audit Entries
~~~~~~~~~~~~~~~~~~

``POST /foglamp/audit`` - create a new audit trail entry.

The purpose of the create method on an audit trail entry is to allow a user interface or an application that is using the FogLAMP API to utilise the FogLAMP audit trail and notification mechanism to raise user defined audit trail entries.


**Request Payload**

The request payload is a JSON object with the audit trail entry minus the timestamp..

+-----------+-----------+------------------------------------------------+-----------------------------+
| Name      | Type      | Description                                    | Example                     |
+===========+===========+================================================+=============================+
| source    | string    | The source of the audit trail entry.           | LocalMonitor                |
+-----------+-----------+------------------------------------------------+-----------------------------+
| severity  | string    | The severity of the event that triggered |br|  | FATAL                       |
|           |           | the audit trail entry to be written. |br|      |                             |
|           |           | This will be one of FATAL, ERROR, WARNING |br| |                             |
|           |           | or INFORMATION.                                |                             |
+-----------+-----------+------------------------------------------------+-----------------------------+
| details   | object    | A JSON object that describes the detail |br|   | { "message" : |br|          |
|           |           | of the audit trail event.                      | "Engine oil pressure low" } |
+-----------+-----------+------------------------------------------------+-----------------------------+


**Response Payload**

The response payload is the newly created audit trail entry.

+-----------+-----------+------------------------------------------------+-----------------------------+
| Name      | Type      | Description                                    | Example                     |
+===========+===========+================================================+=============================+
| timestamp | timestamp | The timestamp when the audit trail |br|        | 2018-03-01T12:00:48.219183  |
|           |           | item was written.                              |                             |
+-----------+-----------+------------------------------------------------+-----------------------------+
| source    | string    | The source of the audit trail entry.           | LocalMonitor                |
+-----------+-----------+------------------------------------------------+-----------------------------+
| severity  | string    | The severity of the event that triggered |br|  | FATAL                       |
|           |           | the audit trail entry to be written. |br|      |                             |
|           |           | This will be one of FATAL, ERROR, WARNING |br| |                             |
|           |           | or INFORMATION.                                |                             |
+-----------+-----------+------------------------------------------------+-----------------------------+
| details   | object    | A JSON object that describes the detail |br|   | { "message" : |br|          |
|           |           | of the audit trail event.                      | "Engine oil pressure low" } |
+-----------+-----------+------------------------------------------------+-----------------------------+


**Example**

.. code-block:: console

  $


category
--------

The Category interface is part of the Configuration Management for FogLAMP. The configuration REST API interacts with the configuration manager to create, retrieve, update and delete the configuration categories and values. Specifically all updates must go via the management layer as this is used to trigger the notifications to the components that have registered interest in configuration categories. This is the means by which the dynamic reconfiguration of FogLAMP is achieved.


POST Category
~~~~~~~~~~~~~

``POST /foglamp/category`` - creates a new category


**Request Payload**

A JSON object that defines the category.

+---------------------+--------+------------------------------------------------+-----------------------------+
| Name                | Type   | Description                                    | Example                     |
+=====================+========+================================================+=============================+
| key                 | string | The key that identifies the category. |br|     |                             |
|                     |        | If the key already exists as a category |br|   |                             |
|                     |        | then the contents of this request |br|         |                             |
|                     |        | is merged with the data stored.                |                             |
+---------------------+--------+------------------------------------------------+-----------------------------+
| description         | string | The severity of the event that triggered |br|  | FATAL                       |
|                     |        | the audit trail entry to be written. |br|      |                             |
|                     |        | This will be one of FATAL, ERROR, WARNING |br| |                             |
|                     |        | or INFORMATION.                                |                             |
+---------------------+--------+------------------------------------------------+-----------------------------+
| items               | array  | A JSON object that describes the detail |br|   | { "message" : |br|          |
+---------------------+--------+------------------------------------------------+-----------------------------+
| items[].name        | string | A JSON object that describes the detail |br|   | { "message" : |br|          |
+---------------------+--------+------------------------------------------------+-----------------------------+
| items[].description | string | A JSON object that describes the detail |br|   | { "message" : |br|          |
+---------------------+--------+------------------------------------------------+-----------------------------+
| items[].type        | string | A JSON object that describes the detail |br|   | { "message" : |br|          |
+---------------------+--------+------------------------------------------------+-----------------------------+
| items[].default     | string | A JSON object that describes the detail |br|   | { "message" : |br|          |
+---------------------+--------+------------------------------------------------+-----------------------------+








User API Reference
==================

This section presents the list of user API methods in alphabetical order.



