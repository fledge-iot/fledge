Core Rest Server
===========

Start rest server
-----------------

  .. code-block:: bash

      cd foglamp/core/
      python -m server

TODO
^^^^

- ``foglamp``  will run in foreground
- ``foglampd`` or ``foglamp start`` command will start this as daemon


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
 - 0 if service is down