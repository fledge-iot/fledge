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

``GET /foglamp/asset`` - Return a list of asset codes buffered in FogLAMP and a count of assets by code.


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
  [ { "count": 1, "assetCode": "fogbench/accelerometer" },
    { "count": 1, "assetCode": "fogbench/gyroscope" },
    { "count": 1, "assetCode": "fogbench/humidity" },
    { "count": 1, "assetCode": "fogbench/luxometer" },
    { "count": 1, "assetCode": "fogbench/magnetometer" },
    { "count": 1, "assetCode": "fogbench/mouse" },
    { "count": 1, "assetCode": "fogbench/pressure" },
    { "count": 1, "assetCode": "fogbench/switch" },
    { "count": 1, "assetCode": "fogbench/temperature" },
    { "count": 1, "assetCode": "fogbench/wall clock" } ]
  $








