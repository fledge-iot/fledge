Core Rest Server
================

Start rest server
-----------------

  .. code-block:: bash

      cd src/python
      python -m foglamp.core

TODO
^^^^

- ``foglamp start`` command will start this as daemon


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

