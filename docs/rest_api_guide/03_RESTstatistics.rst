
statistics
----------

The *statistics* interface allows the retrieval of live statistics, statistical history and statistical rates for the Fledge device.

Fledge records a number of statistics values, some with fixed names and other that reflect the name of a service or an asset. The statistics counters with fixed names are given below.

.. list-table::
    :widths: 20 50
    :header-rows: 1

    * - Key
      - Description
    * - BUFFERED
      - Readings currently in the Fledge buffer
    * - DISCARDED
      - Readings discarded by the South Service before being  placed in the buffer. This may be due to an error in the readings themselves.
    * - PURGED
      - Readings removed from the buffer by the purge process
    * - READINGS
      - Readings received by Fledge
    * - UNSENT
      - Readings filtered out in the send process
    * - UNSNPURGED
      - Readings that were purged from the buffer before being sent

In addition to these fixed names there will be;

  - One statistic per north service of task that is named the same as the service or task name. This will count the number of readings sent out on that service.

  - One statistic per asset that is named the same as the asset. This will be the number of readings that have been ingested for that asset.

  - One statistics per south service, that is named with the service name and *-Ingest* appended. This is the count of readings read in for that service.

GET statistics
~~~~~~~~~~~~~~

``GET /fledge/statistics`` - return a general set of statistics


**Response Payload**

The response payload is a JSON document with statistical information (all numerical), these statistics are absolute counts since Fledge started.


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/statistics
  [ {
      "key": "BUFFERED",
      "description": "Readings currently in the Fledge buffer",
      "value": 0
    },
  ...
    {
      "key": "UNSNPURGED",
      "description": "Readings that were purged from the buffer before being sent",
      "value": 0
    },
  ... ]
  $


GET statistics/history
~~~~~~~~~~~~~~~~~~~~~~

``GET /fledge/statistics/history`` - return a historical set of statistics. This interface is normally used to check if a set of sensors or devices are sending data to Fledge, by comparing the recent statistics and the number of readings received for an asset.


**Request Parameters**

- **limit** - limit the result set to the *N* most recent entries.


**Response Payload**

A JSON document containing an array of statistical information, these statistics are delta counts since the previous entry in the array. The time interval between values is a constant defined that runs the gathering process which populates the history statistics in the storage layer.

.. list-table::
    :widths: 20 50
    :header-rows: 1

    * - Key
      - Description
    * - interval
      - The interval in seconds between successive statistics values
    * - statistics[].BUFFERED
      - Readings currently in the Fledge buffer
    * - statistics[].DISCARDED
      - Readings discarded by the South Service before being  placed in the buffer. This may be due to an error in the readings themselves.
    * - statistics[].PURGED
      - Readings removed from the buffer by the purge process
    * - statistics[].READINGS
      - Readings received by Fledge
    * - statistics[].*NORTH_TASK_NAME*
      - The number of readings sent to the PI system via the OMF plugin with north instance name
    * - statistics[].UNSENT
      - Readings filtered out in the send process
    * - statistics[].UNSNPURGED
      - Readings that were purged from the buffer before being sent
    * - statistics[].*ASSET-CODE*
      - The number of readings received by Fledge since startup with name *asset-code*


**Example**

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/statistics/history?limit=2
  {
    "interval": 15,
    "statistics": [
      {
        "history_ts": "2020-06-01 11:21:04.357",
        "READINGS": 0,
        "BUFFERED": 0,
        "UNSENT": 0,
        "PURGED": 0,
        "UNSNPURGED": 0,
        "DISCARDED": 0,
        "Readings Sent": 0
      },
      {
        "history_ts": "2020-06-01 11:20:48.740",
        "READINGS": 0,
        "BUFFERED": 0,
        "UNSENT": 0,
        "PURGED": 0,
        "UNSNPURGED": 0,
        "DISCARDED": 0,
        "Readings Sent": 0
      }
    ]
  }
  $


GET statistics/rate
~~~~~~~~~~~~~~~~~~~

``GET /fledge/statistics/rate`` - return a set of rates for a set of statistics. This interface returns the rate of a statistic value in counts per minute over a specified set of averages. It is passed two parameters, a comma separated list of intervals in minutes and a comma separated list of statistics.

**Request Parameters**

  - **statistics** - a comma separated list of statistics values to return

  - **periods** - a comma separated list of time periods in minutes. The corresponding rate that will be returned for a given value X is the counts per minute over the previous X minutes.

**Example**

.. code-block:: console

   $ curl http://localhost:8081/fledge/statistics/rate?statistics=Readdings%20Sent\&periods=1,5,15,30,60
   {
      "rates": {
        "READINGS": {
          "1": 12.938816958618938,
          "5": 12.938816958618938,
          "15": 12.938816958618938,
          "30": 12.938816958618938,
          "60": 12.938816958618938
        },
        "READINGS SENT": {
          "1": 0,
          "5": 0,
          "15": 0,
          "30": 0,
          "60": 0
        }
      }
    }
    $


