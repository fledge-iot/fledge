..

Working With Services
=====================

There are a number of API entries points related to working with services within Fledge. 

Service Status
--------------

In order to discover the services registered within a Fledge instance and what state they are currently in the API call */fledge/service* can be used. This is a GET call and will return the set of services along with various information regarding the service. A registered service is one that is either currently running or is configured but disabled.

.. code-block:: console

   $ curl http://localhost:8081/fledge/service | jq
   {
      "services": [
        {
          "name": "Fledge Storage",
          "type": "Storage",
          "address": "localhost",
          "management_port": 39773,
          "service_port": 46391,
          "protocol": "http",
          "status": "running"
        },
        {
          "name": "Fledge Core",
          "type": "Core",
          "address": "0.0.0.0",
          "management_port": 41547,
          "service_port": 8081,
          "protocol": "http",
          "status": "running"
        },
        {
          "name": "Notification",
          "type": "Notification",
          "address": "localhost",
          "management_port": 40605,
          "service_port": 40779,
          "protocol": "http",
          "status": "shutdown"
        },
        {
          "name": "dispatcher",
          "type": "Dispatcher",
          "address": "localhost",
          "management_port": 46353,
          "service_port": 35605,
          "protocol": "http",
          "status": "shutdown"
        },
        {
          "name": "lathe1004",
          "type": "Southbound",
          "address": "localhost",
          "management_port": 45113,
          "service_port": 34403,
          "protocol": "http",
          "status": "running"
        },
        {
          "name": "OPCUA",
          "type": "Northbound",
          "address": "localhost",
          "management_port": 42783,
          "service_port": null,
          "protocol": "http",
          "status": "shutdown"
        },
        {
          "name": "sine2",
          "type": "Southbound",
          "address": "localhost",
          "management_port": 38679,
          "service_port": 33433,
          "protocol": "http",
          "status": "running"
        }
      ]
    }

The data returned for each service includes

.. list-table::
    :widths: 20 50
    :header-rows: 1

    * - Key
      - Description
    * - name
      - The name of the service.
    * - type
      - The service type. This may be one of Northbound, Southbound, Core, Storage, Notification or Dispatcher. In addition other storage types may also be installed to extend the functionality of Fledge.
    * - address
      - The Address the service can be contacted via. Normally localhost or 0.0.0.0 if the service is running on the same machine as the Core service of the Fledge instance.
    * - management_port
      - The management port the service is using to communicate with the core.
    * - service_port
      - The port the service is using to expose the service API of the service.
    * - protocol
      - The protocol the service is using for its control API.
    * - status
      - The status of the service. This may be running, shutdown, unresponsive or failed.

Parameters
~~~~~~~~~~

You may limit the services returned by this call to a particular type by using the *type=* parameter to the URL.

.. code-block:: console

    $ curl -sX GET http://localhost:8081/fledge/service?type=Southbound | jq
    {
      "services": [
        {
          "name": "lathe1004",
          "type": "Southbound",
          "address": "localhost",
          "management_port": 45113,
          "service_port": 34403,
          "protocol": "http",
          "status": "running"
        },
        {
          "name": "sine2",
          "type": "Southbound",
          "address": "localhost",
          "management_port": 38679,
          "service_port": 33433,
          "protocol": "http",
          "status": "running"
        }
      ]
    }

South and North Services
~~~~~~~~~~~~~~~~~~~~~~~~

Specific API calls exist for the two must commonly used service types, the south and north services. These give additional information and are primarily used to give the status of all south or north services in the system.

.. note::

   In the case of the north API entry point the information returned is for both services and tasks

South Services
~~~~~~~~~~~~~~

The */fledge/south* call will list all of the south service with the information above and will also list 

  - the assets that are ingested by the service, 
    
  - a count for each asset of how many readings have been ingested, this is only applicable if the plugin ingests multiple assets
    
  - the name and version of the south plugin used 
    
  - and the current enabled state of the south service.

.. code-block:: console 

    $ curl -s http://localhost:8081/fledge/south |jq
    {
      "services": [
        {
          "name": "lathe1004",
          "address": "localhost",
          "management_port": 45113,
          "service_port": 34403,
          "protocol": "http",
          "status": "running",
          "assets": [
            {
              "count": 520774,
              "asset": "lathe1004"
            },
            {
              "count": 520774,
              "asset": "lathe1004Current"
            },
            {
              "count": 520239,
              "asset": "lathe1004IR"
            },
            {
              "count": 260379,
              "asset": "lathe1004Vibration"
            }
          ],
          "plugin": {
            "name": "lathesim",
            "version": "1.9.2"
          },
          "schedule_enabled": true
        },
        {
          "name": "sine2",
          "address": "localhost",
          "management_port": 38679,
          "service_port": 33433,
          "protocol": "http",
          "status": "running",
          "assets": [
            {
              "count": 734,
              "asset": "sine2"
            },
            {
              "count": 373008,
              "asset": "sine250"
            }
          ],
          "plugin": {
            "name": "sinusoid",
            "version": "1.9.2"
          },
          "schedule_enabled": true
        },
        {
          "name": "test1",
          "address": "",
          "management_port": "",
          "service_port": "",
          "protocol": "",
          "status": "",
          "assets": [
            {
              "count": 76892,
              "asset": "sinusoid"
            },
            {
              "count": 125681,
              "asset": "sinusoid2"
            }
          ],
          "plugin": {
            "name": "sinusoid",
            "version": "1.9.2"
          },
          "schedule_enabled": false
        },
        {
          "name": "testacl",
          "address": "",
          "management_port": "",
          "service_port": "",
          "protocol": "",
          "status": "",
          "assets": [
            {
              "count": 76892,
              "asset": "sinusoid"
            }
          ],
          "plugin": {
            "name": "testing",
            "version": "1.9.2"
          },
          "schedule_enabled": false
        },
        {
          "name": "dsds",
          "address": "",
          "management_port": "",
          "service_port": "",
          "protocol": "",
          "status": "",
          "assets": [],
          "plugin": {
            "name": "Expression",
            "version": "1.9.2"
          },
          "schedule_enabled": false
        }
      ]
    }
    $

Service Types
-------------

Fledge supports a number of different service types, some of which are included with the base Fledge installation and others that must be installed separately if required.

.. note::

   The API entry points in this section require that the Fledge installation has been configured with access to a Fledge package repository.

Installed Service Types
~~~~~~~~~~~~~~~~~~~~~~~

In order to find out what service types are installed in the system the */fledge/service/installed* call can be used.

.. code-block:: console

    $ curl http://localhost:8081/fledge/service/installed
    {"services": ["storage", "north", "dispatcher", "notification", "south"]}

.. note::

   All Fledge instances have the storage, south and north services installed by default when the Fledge core is installed.

Available Service Types
~~~~~~~~~~~~~~~~~~~~~~~

To find out what services are available to be installed from the package repository configured for your Fledge instance use the API */fledge/service/available*.

.. code-block:: console

    $ curl -q http://localhost:8081/fledge/service/available |jq
    {
      "services": [
        "fledge-service-notification"
      ],
      "link": "logs/220831-13-26-25-list.log"
    }

The *link* in the returned JSON is a link to a log file that shows the interaction with the package repository.

Install a Service Type
~~~~~~~~~~~~~~~~~~~~~~

To install a new service type the POST method can be used on the */fledge/service* API call with the parameter *action=install*.

.. code-block:: console

   $ curl -X POST http://localhost:8081/fledge/service?action=install -d'{"format":"repository", "name": "fledge-service-notification"}'

This will install the named service from the package repository.

.. note::

   In order to install a package the package repository must be configured and accessible.

Creating A Service
------------------

A new service can be created using the POST method on the */fledge/service* API call. The payload passed to this request will determine at least the service type and the name of the new service, however it may also contain further configuration which is dependent on the type of the service.

The minimum payload content that must be in every create call for a service is the name of the new service, the type of the service and the enabled state of the service. This can be used for example to create a notification service or a control dispatcher service that need no further configuration.

.. code-block:: console

   $ curl -X POST http://localhost:8081/fledge/service -d'{ "name" : "Notifier", "type" : "notification", "enabled" : "true" }'

Or for a control dispatcher

.. code-block:: console

   $ curl -X POST http://localhost:8081/fledge/service -d'{ "name" : "Control", "type" : "dispatcher", "enabled" : "true" }'

A north or south service need some extra configuration in the payload. These service type must always have a plugin and can optionally be passed configuration for that plugin. If no plugin configuration is given then the plugins default configuration values will be used.

To create a south service using the default values of the *sinusoid* plugin.

.. code-block:: console

   $ curl -X POST http://localhost:8081/fledge/service -d'{ "name" : "Sine", "type" : "south", "enabled" : "true", "plugin" : "sinusoid" }'

In the next example we create a north plugin that will send data to another Fledge instance using the *HTTPC* plugin. We set the value of the configuration item *URL* in the plugin to be the URL of the concentrator Fledge instance.

.. code-block:: console

   $ curl -sX POST http://localhost:8081/fledge/service -d '{"name": "HTTP", "plugin": "httpc", "type": "north", "enabled": true, "config": {"URL": {"value": "http://concentrator.local:6683/buildingA"}}}'

Stopping and Starting Services
------------------------------

Services within Fledge are started and stop via the scheduler, normally a service will be started via a schedule that defines the service to run at startup of Fledge. This ensures that the service runs when Fledge is started and will continue to run until Fledge is stopped. To implicitly stop a service the schedule must be disabled.

Disabling a schedule associated for a service will also stop the service. The service will not then be restarted, even if Fledge is restarted, until the schedule is again enabled.

To disable a schedule you can call the */fledge/schedule/{schedule_id}/disable* API call, however this requires you to know the ID of the schedule associated with the service. It is possible to find this for a given service, as the schedule name is the same as the service name, however it is simpler to use the API call */fledge/schedule/disable* as this can be passed the name of the schedule rather than the schedule ID. Since the schedule name and the service name are the same, we effectively pass the name of the service we wish to disable.

To disable the service call *Sine* we would use the following *curl* command.

.. code-block:: console

   $ curl -X PUT http://localhost:8081/fledge/schedule/disable -d '{"schedule_name": "Sine"}'

To enable the service again we can use the */fledge/schedule/enable* API call, this takes an identical payload to the disable API call.

.. code-block:: console

   $ curl -X PUT http://localhost:8081/fledge/schedule/enable -d '{"schedule_name": "Sine"}'

Deleting a Service
------------------

Services may be deleted from the system using the */fledge/service* API call with the DELETE method. When a service is deleted it will be stopped and the service, configuration for the service and the associated schedule will be removed. Any data that has been read by the service will however remain in the readings database.

To delete the service named *Sine*

.. code-block:: console

   $ curl -X DELETE http://localhost:8081/fledge/service/Sine

