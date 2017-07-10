Core Service
============

Starting the Service
--------------------

- ``foglamp start`` start as daemon
- ``python -m foglamp.core`` run as a regular process


Base URI
--------

      /foglamp

Methods
-------

GET /ping
^^^^^^^^^

 - Response:

   .. code-block:: python

      {
        "uptime": 120
      }

 - unit: seconds

