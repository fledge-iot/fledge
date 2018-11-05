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

The user API provides a mechanism to access the data that is buffered within FogLAMP. It is designed to allow users and applications to get a view of the data that is available in the buffer and do analysis and possibly trigger actions based on recently received sensor readings.

In order to use the entry points in the user API, with the exception of the ``/foglamp/authenticate`` entry point, there must be an authenticated client calling the API. The client must provide a header field in each request, authtoken, the value of which is the token that was retrieved via a call to ``/foglamp/authenticate``. This token must be checked for validity and also that the authenticated entity has user or admin permissions.


Browsing Assets
===============


asset
-----

The asset method is used to browse all or some assets, based on search and filtering.


GET all assets
~~~~~~~~~~~~~~

``GET /foglamp/asset`` - Return an arraty of asset codes buffered in FogLAMP and a count of assets by code.


**Response Payload**

An array of JSON objects, one per asset.

+--------------+--------+----------------------------------------------------+------------------------+
| Name         | Type   | Description                                        | Example                |
+==============+========+====================================================+========================+
| [].assetCode | string | The code of the asset                              | fogbench/accelerometer |
+--------------+--------+----------------------------------------------------+------------------------+
| [].count     | number | The number of recorded readings for the asset code | 22359                  |
+--------------+--------+----------------------------------------------------+------------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset
  [ { "count": 18, "assetCode": "fogbench/accelerometer" },
    { "count": 18, "assetCode": "fogbench/gyroscope" },
    { "count": 18, "assetCode": "fogbench/humidity" },
    { "count": 18, "assetCode": "fogbench/luxometer" },
    { "count": 18, "assetCode": "fogbench/magnetometer" },
    { "count": 18, "assetCode": "fogbench/mouse" },
    { "count": 18, "assetCode": "fogbench/pressure" },
    { "count": 18, "assetCode": "fogbench/switch" },
    { "count": 18, "assetCode": "fogbench/temperature" },
    { "count": 18, "assetCode": "fogbench/wall clock" } ]
  $


GET asset readings
~~~~~~~~~~~~~~~~~~

``GET /foglamp/asset/{code}`` - Return an array of readings for a given asset code.


**Path Parameters**

- **code** - the asset code to retrieve.


**Request Parameters**

- **limit** - set the limit of the number of readings to return. If not specified, the defaults is 20 readings.


**Response Payload**

An array of JSON objects with the readings data for a series of readings sorted in reverse chronological order.

+--------------+-------------+---------------------------------------------------+-----------------------------------+
| Name         | Type        | Description                                       | Example                           |
+==============+=============+===================================================+===================================+
| [].timestamp | timestamp   | The time at which the reading was received.       | 2018-04-16 14:33:18.215           |
+--------------+-------------+---------------------------------------------------+-----------------------------------+
| [].reading   | JSON object | The JSON reading object received from the sensor. | {"reading": {"x":0, "y":0, "z":1} |
+--------------+-------------+---------------------------------------------------+-----------------------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset/fogbench%2Faccelerometer
  [ { "reading": { "x": 0, "y": -2, "z": 0 }, "timestamp": "2018-04-19 14:20:59.692" },
    { "reading": { "x": 0, "y": 0, "z": -1 }, "timestamp": "2018-04-19 14:20:54.643" },
    { "reading": { "x": -1, "y": 2, "z": 1 }, "timestamp": "2018-04-19 14:20:49.899" },
    { "reading": { "x": -1, "y": -1, "z": 1 }, "timestamp": "2018-04-19 14:20:47.026" },
    { "reading": { "x": -1, "y": -2, "z": -2 }, "timestamp": "2018-04-19 14:20:42.746" },
    { "reading": { "x": 0, "y": 2, "z": 0 }, "timestamp": "2018-04-19 14:20:37.418" },
    { "reading": { "x": -2, "y": -1, "z": 2 }, "timestamp": "2018-04-19 14:20:32.650" },
    { "reading": { "x": 0, "y": 0, "z": 1 }, "timestamp": "2018-04-19 14:06:05.870" },
    { "reading": { "x": 1, "y": 1, "z": 1 }, "timestamp": "2018-04-19 14:06:05.870" },
    { "reading": { "x": 0, "y": 0, "z": -1 }, "timestamp": "2018-04-19 14:06:05.869" },
    { "reading": { "x": 2, "y": -1, "z": 0 }, "timestamp": "2018-04-19 14:06:05.868" },
    { "reading": { "x": -1, "y": -2, "z": 2 }, "timestamp": "2018-04-19 14:06:05.867" },
    { "reading": { "x": 2, "y": 1, "z": 1 }, "timestamp": "2018-04-19 14:06:05.867" },
    { "reading": { "x": 1, "y": -2, "z": 1 }, "timestamp": "2018-04-19 14:06:05.866" },
    { "reading": { "x": 2, "y": -1, "z": 1 }, "timestamp": "2018-04-19 14:06:05.865" },
    { "reading": { "x": 0, "y": -1, "z": 2 }, "timestamp": "2018-04-19 14:06:05.865" },
    { "reading": { "x": 0, "y": -2, "z": 1 }, "timestamp": "2018-04-19 14:06:05.864" },
    { "reading": { "x": -1, "y": -2, "z": 0 }, "timestamp": "2018-04-19 13:45:15.881" } ]
  $
  $ curl -s http://localhost:8081/foglamp/asset/fogbench%2Faccelerometer?limit=5
  [ { "reading": { "x": 0, "y": -2, "z": 0 }, "timestamp": "2018-04-19 14:20:59.692" },
    { "reading": { "x": 0, "y": 0, "z": -1 }, "timestamp": "2018-04-19 14:20:54.643" },
    { "reading": { "x": -1, "y": 2, "z": 1 }, "timestamp": "2018-04-19 14:20:49.899" },
    { "reading": { "x": -1, "y": -1, "z": 1 }, "timestamp": "2018-04-19 14:20:47.026" },
    { "reading": { "x": -1, "y": -2, "z": -2 }, "timestamp": "2018-04-19 14:20:42.746" } ]
  $


GET asset reading
~~~~~~~~~~~~~~~~~

``GET /foglamp/asset/{code}/{reading}`` - Return an array of single readings for a given asset code.


**Path Parameters**

- **code** - the asset code to retrieve.
- **reading** - the sensor from the assets JSON formatted reading.


**Request Parameters**

- **limit** - set the limit of the number of readings to return. If not specified, the defaults is 20 single readings.


**Response Payload**

An array of JSON objects with a series of readings sorted in reverse chronological order.

+-----------+-------------+---------------------------------------------+-------------------------+
| Name      | Type        | Description                                 | Example                 |
+===========+=============+=============================================+=========================+
| timestamp | timestamp   | The time at which the reading was received. | 2018-04-16 14:33:18.215 |
+-----------+-------------+---------------------------------------------+-------------------------+
| {reading} | JSON object | The value of the specified reading.         | "temperature": 20       |
+-----------+-------------+---------------------------------------------+-------------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset/fogbench%2Fhumidity/temperature
  [ { "temperature": 20, "timestamp": "2018-04-19 14:20:59.692" },
    { "temperature": 33, "timestamp": "2018-04-19 14:20:54.643" },
    { "temperature": 35, "timestamp": "2018-04-19 14:20:49.899" },
    { "temperature": 0, "timestamp": "2018-04-19 14:20:47.026" },
    { "temperature": 37, "timestamp": "2018-04-19 14:20:42.746" },
    { "temperature": 47, "timestamp": "2018-04-19 14:20:37.418" },
    { "temperature": 26, "timestamp": "2018-04-19 14:20:32.650" },
    { "temperature": 12, "timestamp": "2018-04-19 14:06:05.870" },
    { "temperature": 38, "timestamp": "2018-04-19 14:06:05.869" },
    { "temperature": 7, "timestamp": "2018-04-19 14:06:05.869" },
    { "temperature": 21, "timestamp": "2018-04-19 14:06:05.868" },
    { "temperature": 5, "timestamp": "2018-04-19 14:06:05.867" },
    { "temperature": 40, "timestamp": "2018-04-19 14:06:05.867" },
    { "temperature": 39, "timestamp": "2018-04-19 14:06:05.866" },
    { "temperature": 29, "timestamp": "2018-04-19 14:06:05.865" },
    { "temperature": 41, "timestamp": "2018-04-19 14:06:05.865" },
    { "temperature": 46, "timestamp": "2018-04-19 14:06:05.864" },
    { "temperature": 10, "timestamp": "2018-04-19 13:45:15.881" } ]
  $
  $ curl -s http://localhost:8081/foglamp/asset/fogbench%2Faccelerometer?limit=5
  [ { "temperature": 20, "timestamp": "2018-04-19 14:20:59.692" },
    { "temperature": 33, "timestamp": "2018-04-19 14:20:54.643" },
    { "temperature": 35, "timestamp": "2018-04-19 14:20:49.899" },
    { "temperature": 0, "timestamp": "2018-04-19 14:20:47.026" },
    { "temperature": 37, "timestamp": "2018-04-19 14:20:42.746" } ]
  $


GET asset reading summary
~~~~~~~~~~~~~~~~~~~~~~~~~

``GET /foglamp/asset/{code}/{reading}/summary`` - Return minimum, maximum and average values of a reading by asset code.


**Path Parameters**

- **code** - the asset code to retrieve.
- **reading** - the sensor from the assets JSON formatted reading.


**Response Payload**

An array of JSON objects with a series of readings sorted in reverse chronological order.

+-------------------+--------+--------------------------------------------+---------+
| Name              | Type   | Description                                | Example |
+===================+========+============================================+=========+
| {reading}.average | number | The average value of the set of       |br| | 27      | 
|                   |        | sensor values selected in the query string |         |
+-------------------+--------+--------------------------------------------+---------+
| {reading}.min     | number | The minimum value of the set of       |br| | 0       | 
|                   |        | sensor values selected in the query string |         |
+-------------------+--------+--------------------------------------------+---------+
| {reading}.max     | number | The maximum value of the set of       |br| | 47      | 
|                   |        | sensor values selected in the query string |         |
+-------------------+--------+--------------------------------------------+---------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset/fogbench%2Fhumidity/temperature/summary
  { "temperature": { "max": 47, "min": 0, "average": 27 } }
  $


GET timed average asset reading
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``GET /foglamp/asset/{code}/{reading}/series`` - Return minimum, maximum and average values of a reading by asset code in a time series. The default interval in the series is one second.


**Path Parameters**

- **code** - the asset code to retrieve.
- **reading** - the sensor from the assets JSON formatted reading.


**Request Parameters**

- **limit** - set the limit of the number of readings to return. If not specified, the defaults is 20 single readings.


**Response Payload**

An array of JSON objects with a series of readings sorted in reverse chronological order.

+-----------+-----------+--------------------------------------------+---------------------+
| Name      | Type      | Description                                | Example             |
+===========+===========+============================================+=====================+
| timestamp | timestamp | The time the reading represents.           | 2018-04-16 14:33:18 |
+-----------+-----------+--------------------------------------------+---------------------+
| average   | number    | The average value of the set of       |br| | 27                  | 
|           |           | sensor values selected in the query string |                     |
+-----------+-----------+--------------------------------------------+---------------------+
| min       | number    | The minimum value of the set of       |br| | 0                   | 
|           |           | sensor values selected in the query string |                     |
+-----------+-----------+--------------------------------------------+---------------------+
| max       | number    | The maximum value of the set of       |br| | 47                  | 
|           |           | sensor values selected in the query string |                     |
+-----------+-----------+--------------------------------------------+---------------------+


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/asset/fogbench%2Fhumidity/temperature/series
  [ { "timestamp": "2018-04-19 14:20:59", "max": 20, "min": 20, "average": 20 },
    { "timestamp": "2018-04-19 14:20:54", "max": 33, "min": 33, "average": 33 },
    { "timestamp": "2018-04-19 14:20:49", "max": 35, "min": 35, "average": 35 },
    { "timestamp": "2018-04-19 14:20:47", "max": 0,  "min": 0,  "average": 0  },
    { "timestamp": "2018-04-19 14:20:42", "max": 37, "min": 37, "average": 37 },
    { "timestamp": "2018-04-19 14:20:37", "max": 47, "min": 47, "average": 47 },
    { "timestamp": "2018-04-19 14:20:32", "max": 26, "min": 26, "average": 26 },
    { "timestamp": "2018-04-19 14:06:05", "max": 46, "min": 5,  "average": 27.8 },
    { "timestamp": "2018-04-19 13:45:15", "max": 10, "min": 10, "average": 10 } ]
  $
  $ curl -s http://localhost:8081/foglamp/asset/fogbench%2Fhumidity/temperature/series
  [ { "timestamp": "2018-04-19 14:20:59", "max": 20, "min": 20, "average": 20 },
    { "timestamp": "2018-04-19 14:20:54", "max": 33, "min": 33, "average": 33 },
    { "timestamp": "2018-04-19 14:20:49", "max": 35, "min": 35, "average": 35 },
    { "timestamp": "2018-04-19 14:20:47", "max": 0,  "min": 0,  "average": 0  },
    { "timestamp": "2018-04-19 14:20:42", "max": 37, "min": 37, "average": 37 } ]






