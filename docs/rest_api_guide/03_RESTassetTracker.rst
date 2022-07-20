..

Asset Tacker
------------

The *asset tracker* API allows the operations that an asset undergoes whilst traversing the data pipeline within Fledge to be tracked as displayed.

``GET /fledge/track`` - return tracking data for one or more asset

**Parameters**

  - ``asset`` - define the asset to be tracked. If omitted tracking data for all assets is returned

  - ``event`` - the event to track. If omitted all events will be returned

  - ``service`` - limit the tracking data to a particular service

**Response Payload**

An array of tracked events, each of which contains the following

.. list-table::
    :widths: 20 20 50 50
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - asset
      - string
      - The name of the asset for which this track event relates
      - sinusoid
    * - event
      - string
      - The event that was tracked, this will be one of Ingest, Filter or Egress
      - Ingest
    * - service
      - string
      - The name of the service this event was tracked in
      - testSignal4
    * - fledge
      - string
      - The name of the fledge instance this event was tracked in
      - fledge002
    * - plugin
      - string
      - The name of the plugin this event was tracked in
      - sinusoid
    * - timestamp
      - string
      - The timestamp when this event was first tracked
      - 2022-07-06 10:20:13.059

**Example**

Return the asset tracking data for the asset called *sinusoid*

.. code-block:: console

   curl http://localhost:8081/fledge/track?asset=sinusoid

Returns

.. code-block:: console

    {
      "track": [
        {
          "asset": "sinusoid",
          "event": "Filter",
          "service": "test1",
          "fledge": "Fledge",
          "plugin": "test2",
          "timestamp": "2022-07-06 10:20:13.059"
        },
        {
          "asset": "sinusoid",
          "event": "Ingest",
          "service": "test1",
          "fledge": "Fledge",
          "plugin": "sinusoid",
          "timestamp": "2022-07-11 16:12:25.749"
        },
        {
          "asset": "sinusoid",
          "event": "Filter",
          "service": "test1",
          "fledge": "Fledge",
          "plugin": "python35",
          "timestamp": "2022-07-13 12:33:10.082"
        },
        {
          "asset": "sinusoid",
          "event": "Egress",
          "service": "OMF",
          "fledge": "Fledge",
          "plugin": "OMF",
          "timestamp": "2022-07-15 14:07:14.950"
        }
      ]
    }

