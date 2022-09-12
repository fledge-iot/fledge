Developer API Calls
===================

A number of calls exist in the API that are targeted at those developing
pipelines and plugins for Fledge. These are not actions that are expected
to be of everyday use, but are to aid in this development process.

Purge Readings
--------------

Under ordinary circumstances a user should never need to manually purge
data from the Fledge storage buffer, however during the development
process it can be useful to be able to manually purge data.

``DELETE /fledge/asset`` - Purge data for all assets from the buffer

**Response Payload**

The response payload is a JSON document that returns the number of readings that have been deleted.

**Example**

.. code-block:: console

   $ curl -X DELETE http://localhost:8081/fledge/asset

The return from this is the number of readings that have been purged.

.. code-block:: JSON

   { "purged" : 3239 }

.. note::

   Great care should be exercised in using this call as **all** data that is currently buffered in the Fledge storage layer will be lost and there is no mechanism to undo this operation.

``DELETE /fledge/asset/{asset name}`` - Purge data for the named asset from the buffer

**Response Payload**

The response payload is a JSON document that returns the number of readings that have been deleted.

**Example**

.. code-block:: console

   $ curl -X DELETE http://localhost:8081/fledge/asset/sinusoid

The return from this is the number of readings that have been purged.

.. code-block:: JSON

   { "purged" : 435 }

.. note::

   Great care should be exercised in using this call as **all** data for the **named** asset that is currently buffered in the Fledge storage layer will be lost and there is no mechanism to undo this operation.

View Plugin Persisted Data
--------------------------

Fledge plugins may persist data between executions of the the plugin. This data takes the form of a JSON document. In normally circumstance the user should not need to view or manage this data as it is the responsibility of the plugin to manage this data. However, during the development of a plugin it is useful for a plugin developer to be able to view this data and manage the data.

``GET /fledge/service/{service_name}/persist`` - get the names of the plugins that persist data within a service.

.. code-block:: console

   curl http:/localhost:8081/fledge/service/OMF/persist

This would return the list of plugins as a JSON document as shown below

.. code-block:: JSON

   {
      "persistent": [
        "OMF"
      ]
    }

If no plugins within this service persist data the *persistent* array would be empty.

``GET /fledge/service/{service_name}/plugin/{plugin_name}/data`` - view the plugin data persisted by an instance of a plugin

**Parameters**

  - *service_name* - the name of the service in which the plugin is running

  - *plugin_name* - the name of the plugin within the service. For a north or south plugin this is the same as the service name. For a filter this will be the name given to the filter instance when it was added to the pipeline.

**Response Payload**

The response payload is the persisted data from the plugin.

**Example**

.. code-block:: console

   $ curl http://localhost:8081/fledge/service/OMF/plugin/OMF/data

Where *OMF* is the name of a north service with an OMF filter connected to a PI Server. In this case the persisted data is the type information we cache locally that describes the types that have been created within the OMF layer of the PI Server.

.. code-block:: console

    {
      "data": {
        "sentDataTypes": [
          {
            "sine25": {
              "type-id": 1,
              "dataTypesShort": "0x101",
              "hintChecksum": "0x0",
              "namingScheme": 0,
              "afhHash": "15489826335467873671",
              "afHierarchy": "fledge/data_piwebapi/mark",
              "afHierarchyOrig": "fledge/data_piwebapi/mark",
              "dataTypes": {
                "sinusoid": {
                  "type": "number",
                  "format": "float64"
                }
              }
            }
          },
          {
            "sinusoid": {
              "type-id": 1,
              "dataTypesShort": "0x101",
              "hintChecksum": "0x0",
              "namingScheme": 0,
              "afhHash": "15489826335467873671",
              "afHierarchy": "fledge/data_piwebapi/mark",
              "afHierarchyOrig": "fledge/data_piwebapi/mark",
              "dataTypes": {
                "sinusoid": {
                  "type": "number",
                  "format": "float64"
                }
              }
            }
          }
        ]
      }
    }

.. note::

   Persisted data is written when the plugin is shutdown. Therefore in order to obtain accurate results this call should only be made when the service is shutdown. Calling this API when a service is running will result in data from the previous time the service was shutdown.

``POST /fledge/service/{service_name}/plugin/{plugin_name}/data`` - write the persisted data for a plugin. Also send the data with payload ``{"data": "<YOUR_VALUE>"}``

Write or overwrite data persisted by the plugin. The request payload is the data which the plugin should receive and must be in the correct format for the plugin.

The payload for the POST command is defined by the plugin itself and hence no general example can be given here. It is intended that this is used in conjunction with an earlier GET request or a GET request on another instance, to restore a previous state.

.. note::

   Persisted data is written when the plugin is shutdown. Therefore in order to obtain predictable results this call should only be made when the service is shutdown. Calling this API when a service is running will result in data that is written by the call being overwritten by the plugin when it shuts down.


``DELETE /fledge/service/{service_name}/plugin/{plugin_name}/data`` - delete the persisted data for the plugin

.. note::

   Persisted data is written when the plugin is shutdown. Therefore in order to obtain predictable results this call should only be made when the service is shutdown. Calling this API when a service is running will result the data being written from the plugin when it is shutdown and render this delete operation obsolete.
