.. REST API Guide
.. https://docs.google.com/document/d/1JJDP7g25SWerNVCxgff02qp9msHbqA9nt3RAFx8-Qng

.. |br| raw:: html

   <br />

.. |ar| raw:: html

   <div align="right">

.. Images


.. Links


.. =============================================


******************
User API Reference
******************

The user API provides a mechanism to access the data that is buffered within Fledge. It is designed to allow users and applications to get a view of the data that is available in the buffer and do analysis and possibly trigger actions based on recently received sensor readings.

In order to use the entry points in the user API, with the exception of the ``/fledge/authenticate`` entry point, there must be an authenticated client calling the API. The client must provide a header field in each request, authtoken, the value of which is the token that was retrieved via a call to ``/fledge/authenticate``. This token must be checked for validity and also that the authenticated entity has user or admin permissions.


Browsing Assets
===============


asset
-----

The asset method is used to browse all or some assets, based on search and filtering.


GET all assets
~~~~~~~~~~~~~~

``GET /fledge/asset`` - Return an array of asset codes buffered in Fledge and a count of assets by code.


**Response Payload**

An array of JSON objects, one per asset.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - count
      - number
      - The number of recorded readings for the asset code
      - 11
    * - assetCode
      - string
      - The code of the asset
      - asset_1

**Example**

.. code-block:: console

  $ curl -sX GET http://localhost:8081/fledge/asset
  [
    {"count": 11, "assetCode": "asset_1"},
    {"count": 11, "assetCode": "asset_2"},
    {"count": 11, "assetCode": "asset_3"}
  ]
  $

GET asset readings
~~~~~~~~~~~~~~~~~~

``GET /fledge/asset/{code}`` - Return an array of readings for a given asset code.


**Path Parameters**

- **code** - the asset code to retrieve.


**Request Parameters**

  - **limit** - set the limit of the number of readings to return. If not specified, the defaults is 20 readings.
  
  - **skip** - the number of assets to skip. This is used in conjunction with limit and allows the caller to not just get the last N readings, but to get a set of readings from the past.

  - **seconds** - this is essentially an alternative form of limit, but here the limit is expressed in seconds rather than a number of readings. It will return the readings for the last N seconds. Note that this can not be used in conjunction with the *limit* and *skip* or with *hours* and *minutes* request parameters.

  - **minutes** - this is essentially an alternative form of limit, but here the limit is expressed in minutes rather than a number of readings. It will return the readings for the last N minutes. Note that this can not be used in conjunction with the *limit* and *skip* or with *seconds* and *hours* request parameters.

  - **hours** - this is essentially an alternative form of limit, but here the limit is expressed in hours rather than a number of readings. It will return the readings for the last N hours. Note that this can not be used in conjunction with the *limit* and *skip* or with *seconds* and *minutes* request parameters.

  - **previous** - This is used in conjunction with the *hours*, *minutes* or *seconds* request parameter and allows the caller to get not just the most recent readings but historical readings. The value of *previous* is defined in hours, minutes or seconds dependent upon the parameter it is used with and defines how long ago the data that is returned should end. If the caller passes a set of parameters *seconds=30&previous=120* the call will return 30 seconds worth of data and the newest data returned will be 120 seconds old.

**Response Payload**

An array of JSON objects with the readings data for a series of readings sorted in reverse chronological order.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - reading
      - JSON object
      - The JSON reading object received from the sensor
      - {"pressure": 885.7}
    * - timestamp
      - timestamp
      - The time at which the reading was received
      - 2023-04-14 12:04:34.603963

**Example**

.. code-block:: console

  $ curl -sX GET http://localhost:8081/fledge/asset/asset_3
  [
    {"reading": {"pressure": 885.7}, "timestamp": "2023-04-14 12:04:34.603963"},
    {"reading": {"pressure": 846.3}, "timestamp": "2023-04-14 12:02:39.150127"},
    {"reading": {"pressure": 913.0}, "timestamp": "2023-04-14 12:02:26.616218"},
    {"reading": {"pressure": 994.7}, "timestamp": "2023-04-14 12:02:11.171338"},
    {"reading": {"pressure": 960.2}, "timestamp": "2023-04-14 12:01:56.979426"}
  ]
  $

  $ curl -sX GET http://localhost:8081/fledge/asset/asset_3?limit=3
  [
    {"reading": {"pressure": 885.7}, "timestamp": "2023-04-14 12:04:34.603963"},
    {"reading": {"pressure": 846.3}, "timestamp": "2023-04-14 12:02:39.150127"},
    {"reading": {"pressure": 913.0}, "timestamp": "2023-04-14 12:02:26.616218"}
  ]
  $

Using *seconds* and *previous* to obtain historical data.

.. code-block:: console

  $ curl -sX GET http://localhost:8081/fledge/asset/sinusoid?seconds=5\&previous=60|jq
  [
    { "reading": { "sinusoid": 1 }, "timestamp": "2022-11-09 09:37:51.930688" },
    { "reading": { "sinusoid": 0.994521895 }, "timestamp": "2022-11-09 09:37:50.930887" },
    { "reading": { "sinusoid": 0.978147601 }, "timestamp": "2022-11-09 09:37:49.933698" },
    { "reading": { "sinusoid": 0.951056516 }, "timestamp": "2022-11-09 09:37:48.930644" },
    { "reading": { "sinusoid": 0.913545458 }, "timestamp": "2022-11-09 09:37:47.930950" }
  ]

The above call returned 5 seconds of data from the current time minus 65 seconds to the current time minus 5 seconds.

GET asset reading
~~~~~~~~~~~~~~~~~

``GET /fledge/asset/{code}/{reading}`` - Return an array of single readings for a given asset code.


**Path Parameters**

- **code** - the asset code to retrieve.
- **reading** - the sensor from the assets JSON formatted reading.


**Request Parameters**

  - **limit** - set the limit of the number of readings to return. If not specified, the defaults is 20 single readings.
  
  - **skip** - the number of assets to skip. This is used in conjunction with limit and allows the caller to not just get the last N readings, but to get a set of readings from the past.

  - **seconds** - this is essentially an alternative form of limit, but here the limit is expressed in seconds rather than a number of readings. It will return the readings for the last N seconds. Note that this can not be used in conjunction with the *limit* and *skip* or with *hours* and *minutes* request parameters.

  - **minutes** - this is essentially an alternative form of limit, but here the limit is expressed in minutes rather than a number of readings. It will return the readings for the last N minutes. Note that this can not be used in conjunction with the *limit* and *skip* or with *seconds* and *hours* request parameters.

  - **hours** - this is essentially an alternative form of limit, but here the limit is expressed in hours rather than a number of readings. It will return the readings for the last N hours. Note that this can not be used in conjunction with the *limit* and *skip* or with *seconds* and *minutes* request parameters.

  - **previous** - This is used in conjunction with the *hours*, *minutes* or *seconds* request parameter and allows the caller to get not just the most recent readings but historical readings. The value of *previous* is defined in hours, minutes or seconds dependent upon the parameter it is used with and defines how long ago the data that is returned should end. If the caller passes a set of parameters *seconds=30&previous=120* the call will return 30 seconds worth of data and the newest data returned will be 120 seconds old.


**Response Payload**

An array of JSON objects with a series of readings sorted in reverse chronological order.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - timestamp
      - timestamp
      - The time at which the reading was received
      - 2023-04-14 12:04:34.603937
    * - reading
      - JSON object
      - The value of the specified reading
      - {"lux": 47705.68}

**Example**

.. code-block:: console

  $ curl -sX GET http://localhost:8081/fledge/asset/asset_2/lux
  [
    {"timestamp": "2023-04-14 12:04:34.603937", "lux": 47705.68},
    {"timestamp": "2023-04-14 12:02:39.150106", "lux": 97967.9},
    {"timestamp": "2023-04-14 12:02:26.616200", "lux": 28788.154},
    {"timestamp": "2023-04-14 12:02:11.171319", "lux": 57992.674},
    {"timestamp": "2023-04-14 12:01:56.979407", "lux": 10373.945}
  ]
  $

  $ curl -sX GET http://localhost:8081/fledge/asset/asset_2/lux?limit=3
  [
    {"timestamp": "2023-04-14 11:25:05.672528", "lux": 75723.923},
    {"timestamp": "2023-04-14 11:24:49.767983", "lux": 50475.99},
    {"timestamp": "2023-04-14 11:23:15.672528", "lux": 75723.923}
  ]
  $


GET asset reading summary
~~~~~~~~~~~~~~~~~~~~~~~~~

``GET /fledge/asset/{code}/{reading}/summary`` - Return minimum, maximum and average values of a reading by asset code.


**Path Parameters**

- **code** - the asset code to retrieve.
- **reading** - the sensor from the assets JSON formatted reading.


**Response Payload**

A JSON object of a reading by asset code.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - .lux.min
      - number
      - The minimum value of the set of sensor values selected in the query string
      - 10373.945
    * - .lux.max
      - number
      - The maximum value of the set of sensor values selected in the query string
      - 97967.9
    * - .lux.average
      - number
      - The average value of the set of sensor values selected in the query string
      - 48565.6706

**Example**

.. code-block:: console

  $ curl -sX GET http://localhost:8081/fledge/asset/asset_2/lux/summary
    {"lux": {"min": 10373.945, "max": 97967.9, "average": 48565.6706}}
  $

GET all asset reading timespan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``GET /fledge/asset/timespan`` - Return newest and oldest timestamp of each asset for which we hold readings in the buffer.


**Response Payload**

An array of JSON objects with newest and oldest timestamps of the readings held for each asset.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - oldest
      - string
      - The oldest timestamp held in the buffer for this asset
      - 2022-11-08 17:07:02.623258
    * - newest
      - string
      - The newest timestamp held in the buffer for this asset
      - 2022-11-09 14:52:50.069432
    * - asset_code
      - string
      - The asset code for which the timestamps refer
      - sinusoid

**Example**

.. code-block:: console

    $ curl -sX GET http://localhost:8081/fledge/asset/timespan
    [
      {
        "oldest": "2022-11-08 17:07:02.623258",
        "newest": "2022-11-09 14:52:50.069432",
        "asset_code": "sinusoid"
      }
    ]

GET asset reading timespan
~~~~~~~~~~~~~~~~~~~~~~~~~~

``GET /fledge/asset/{code}/timespan`` - Return newest and oldest timestamp for which we hold readings in the buffer.


**Path Parameters**

- **code** - the asset code to retrieve.


**Response Payload**

A JSON object with the newest and oldest timestamps for the asset held in the storage buffer.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - oldest
      - string
      - The oldest timestamp held in the buffer for this asset
      - 2022-11-08 17:07:02.623258
    * - newest
      - string
      - The newest timestamp held in the buffer for this asset
      - 2022-11-09 14:52:50.069432

**Example**

.. code-block:: console

    $ curl -sX GET http://localhost:8081/fledge/asset/sinusoid/timespan|jq
      {
        "oldest": "2022-11-08 17:07:02.623258",
        "newest": "2022-11-09 14:59:14.069207"
      }


GET timed average asset reading
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``GET /fledge/asset/{code}/{reading}/series`` - Return minimum, maximum and average values of a reading by asset code in a time series. The default interval in the series is one second.


**Path Parameters**

- **code** - the asset code to retrieve.
- **reading** - the sensor from the assets JSON formatted reading.

**Request Parameters**

  - **limit** - set the limit of the number of readings to return. If not specified, the defaults is 20 readings.

  - **skip** - the number of assets to skip. This is used in conjunction with limit and allows the caller to not just get the last N readings, but to get a set of readings from the past.

  - **seconds** - this is essentially an alternative form of limit, but here the limit is expressed in seconds rather than a number of readings. It will return the readings for the last N seconds. Note that this can not be used in conjunction with the *limit* and *skip* or with *hours* and *minutes* request parameters.

  - **minutes** - this is essentially an alternative form of limit, but here the limit is expressed in minutes rather than a number of readings. It will return the readings for the last N minutes. Note that this can not be used in conjunction with the *limit* and *skip* or with *seconds* and *hours* request parameters.

  - **hours** - this is essentially an alternative form of limit, but here the limit is expressed in hours rather than a number of readings. It will return the readings for the last N hours. Note that this can not be used in conjunction with the *limit* and *skip* or with *seconds* and *minutes* request parameters.

  - **previous** - This is used in conjunction with the *hours*, *minutes* or *seconds* request parameter and allows the caller to get not just the most recent readings but historical readings. The value of *previous* is defined in hours, minutes or seconds dependent upon the parameter it is used with and defines how long ago the data that is returned should end. If the caller passes a set of parameters *seconds=30&previous=120* the call will return 30 seconds worth of data and the newest data returned will be 120 seconds old.

**Response Payload**

An array of JSON objects with a series of readings sorted in reverse chronological order.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - min
      - number
      - The minimum value of the set of sensor values selected in the query string
      - 47705.68
    * - max
      - number
      - The maximum value of the set of sensor values selected in the query string
      - 47705.68
    * - average
      - number
      - The average value of the set of sensor values selected in the query string
      - 47705.68
    * - timestamp
      - timestamp
      - The time the reading represents
      - 2023-04-14 12:04:34

**Example**

.. code-block:: console

  $ curl -sX GET http://localhost:8081/fledge/asset/asset_2/lux/series
  [
    {"min": 47705.68, "max": 47705.68, "average": 47705.68, "timestamp": "2023-04-14 12:04:34"},
    {"min": 97967.9, "max": 97967.9, "average": 97967.9, "timestamp": "2023-04-14 12:02:39"},
    {"min": 28788.154, "max": 28788.154, "average": 28788.154, "timestamp": "2023-04-14 12:02:26"},
    {"min": 57992.674, "max": 57992.674, "average": 57992.674, "timestamp": "2023-04-14 12:02:11"},
    {"min": 10373.945, "max": 10373.945, "average": 10373.945, "timestamp": "2023-04-14 12:01:56"}
  ]
  $

  $ curl -sX GET http://localhost:8081/fledge/asset/asset_2/lux/series?limit=3
  [
    {"min": 47705.68, "max": 47705.68, "average": 47705.68, "timestamp": "2023-04-14 12:04:34"},
    {"min": 97967.9, "max": 97967.9, "average": 97967.9, "timestamp": "2023-04-14 12:02:39"},
    {"min": 28788.154, "max": 28788.154, "average": 28788.154, "timestamp": "2023-04-14 12:02:26"}
  ]

Using *seconds* and *previous* to obtain historical data.

.. code-block:: console

    $ curl -sX GET http://localhost:8081/fledge/asset/asset_2/lux/series?seconds=5\&previous=60
    [
        {"min": 47705.68, "max": 47705.68, "average": 47705.68, "timestamp": "2023-04-14 12:04:34"}
    ]
  $

The above call returned 5 seconds of data from the current time minus 65 seconds to the current time minus 5 seconds.
