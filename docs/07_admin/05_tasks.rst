.. Tasks

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. =============================================


*************
FogLAMP Tasks
*************

Tasks are part of the FogLAMP IoT platform. They are like services, but with a clear distinction:

- *services* are started at a certain point (usually at startup) and they are likely to continue to work until FogLAMP stops. 
- *tasks* are started when required, they execute a job and then they terminate.

In simple terms, a service is meant to always listen and react to requests, while a task is triggered by an event and then when job is terminated, the tasks ends.

That said, tasks and services shared these same features:

- They are both started by the FogLAMP scheduler. It is likely that services are started at startup, while tasks can start at a given time or interval.
- They both use the internal API to communicate with other services.
- They both use the same pluggable architecture to separate a common logic, usually associated to the internal features of FogLAMP, from a more generic logic, usually closer to the type of operations that must be performed.

In this chapter we present a set of tasks that are commonly available in FogLAMP.


Purge
=====

The *Purge* task is triggered by the scheduler to purge old data that is still stored (buffered) in FogLAMP. The logic applied to the task is relatively simple:

- The task is called exclusively (i.e. there cannot be more than one *Purge* task running at any given time) by the FogLAMP scheduler every hour (by default).
- Data that is older than a certain date/time is removed.
- Optionally, data is removed if the total size of the stored objects is bigger than 1GByte (default)
- Optionally, data is not removed if it has not been extracted and used by any North task or service yet.
- All purge operations are stored in the audit log.


Purge Schedule
--------------

*Purge* is one of the tasks launched by the FogLAMP scheduler. You can retrieve information about the scheduling by calling the *GET* method of the *schedule* call. The name and the process name of the task are both *purge*:

.. code-block:: console

  $ curl -sX GET http://localhost:8081/foglamp/schedule
  ...
  { "id"          : "cea17db8-6ccc-11e7-907b-a6006ad3dba0",
    "name"        : "purge",
    "time"        : 0,
    "enabled"     : true,
    "repeat"      : 3600,
    "type"        : "INTERVAL",
    "exclusive"   : true,
    "processName" : "purge",
    "day"         : null },
  ...
  $

As you can see from the JSON output, the task is scheduled to be executed every hour (3,600 seconds). In order to change the interval between *Purge* tasks, you can call the *PUT* method of the *schedule* call by passing the associated *id*. For example, in order to change the task to be executed any 5 minutes (i.e. 300 seconds) you should call:

.. code-block:: console

  $ curl -sX PUT http://localhost:8081/foglamp/schedule/cea17db8-6ccc-11e7-907b-a6006ad3dba0 -d '{"repeat": 300}'
  { "schedule": { "id": "cea17db8-6ccc-11e7-907b-a6006ad3dba0",
                  "name"        : "purge",
                  "time"        : 0,
                  "enabled"     : true,
                  "repeat"      : 300,
                  "type"        : "INTERVAL",
                  "exclusive"   : true,
                  "processName" : "purge",
                  "day"         : null }
  }
  $


Purge Configuration
-------------------

The configuration of the *Purge* task is stored in the metadata structures of FogLAMP and it can be retrieve using the *GET* method of the *category/PURGE_READ* call. This is the command used to retrieve the configuration in JSON format:

.. code-block:: console

  $ curl -sX GET http://localhost:8081/foglamp/category/PURGE_READ
  { "retainUnsent" : { "type": "boolean",
                       "default": "False",
                       "description": "Retain data that has not been sent to any historian yet.",
                       "value": "False" },
    "age"          : { "type": "integer",
                       "default": "72",
                       "description": "Age of data to be retained, all data that is older than this value will be removed,unless retained. (in Hours)",
                       "value": "72" },
    "size"         : { "type": "integer",
                       "default": "1000000",
                       "description": "Maximum size of data to be retained, the oldest data will be removed to keep below this size, unless retained. (in Kbytes)",
                       "value": "1000000" } }
  $


Changes can be applied using the *PUT* method for each parameter call. For example, in order to change the retention policy for data that has not been sent to historians yet, you can use this call:

.. code-block:: console

  $ curl -sX PUT http://locahost:8081/foglamp/category/PURGE_READ/retainUnsent -d '{"value": "True"}'
  { "type": "boolean",
    "default": "False",
    "description": "Retain data that has not been sent to any historian yet.",
    "value": "True" }
  $

The following table shows the list of parameters that can be changed in the *Purge* task:

+-------------------+----------+-----------------------------------------+--------------------------------------------------------+
| Item              | Type     | Default                                 | Description                                            |
+===================+==========+=========================================+========================================================+
| retainUnsent      | boolean  | False                                   | Retain data that has not been sent to "North" yet |br| |
|                   |          |                                         | When *True*, data that has not yet been retrieved |br| |
|                   |          |                                         | by any North service or task, will not be purged. |br| |
|                   |          |                                         | When *False*, data is purged withouth checking    |br| |
|                   |          |                                         | whether it has been sent to a North destination   |br| |
|                   |          |                                         | yet or not.                                            |
+-------------------+----------+-----------------------------------------+--------------------------------------------------------+
| age               | integer  | 72                                      | Age in hours of the data to be retained. Data     |br| |
|                   |          |                                         | that is older than this value, will be purged.         |
+-------------------+----------+-----------------------------------------+--------------------------------------------------------+
| size              | integer  | 1000000                                 | Size in KBytes of data that will be retained in   |br| | 
|                   |          |                                         | FogLAMP. Older data will be removed to keep the   |br| |
|                   |          |                                         | data stored in FogLAMP below this size.                |
+-------------------+----------+-----------------------------------------+--------------------------------------------------------+


