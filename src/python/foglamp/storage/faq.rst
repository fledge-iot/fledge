FAQ
###

Here are some answers to frequently-asked questions.
Got a question that isn't answered here? Try `Slack`_ or `bug tracker`_.

.. _Slack: https://scaledb.slack.com/
.. _bug tracker: https://scaledb.atlassian.net/projects/FOGL

.. contents::
    :local:
    :depth: 2


How do I…
=========


.. _ storage server:

… build and start the storage server?
--------------------------------------------------------------

To build it check out branch, **FOGL-197**

    `cd FogLAMP`

    `mkdir build`

    `cd build`

    `cmake ..`

    `make`

**Copy the executable and plugin somewhere you want to run it**

   `cp ./src/C/foglamp/storage/plugins/postgres/libpostgres.so ./src/C/foglamp/storage/plugins/postgres/libpostgres.so.1 ./src/C/foglamp/storage/storage <run directory>`

**Run with**

   `cd <run directory>`

   `./storage`



.. _installation and setup pre-requisite:

… what are the basic requirements to build storage static files?
------------------------------------------------------------------

    `sudo apt-get install cmake`

    `sudo apt-get install g++`

    `sudo apt-get install make`


.. _demo test scripts:

…where can I find the test (demo) scripts?
------------------------------------------
There are some curl scripts that demonstrate the usage in FogLAMP/test/storage.


.. _DB connection and snap:

… how can I use different db connection?
------------------------------------------

Code allows the environment variable DB_CONNECTION to override the default connection string, so you can set this to

:example:

`export DB_CONNECTION="dbname=foglamp host=/tmp"`

If you are installing Postgres via the snap package

… How to run  `SELECT * FROM <table_name>`?
-------------------------------------------

Server: GET `{SERVICE_HOST:PORT}/storage/table/{table_name}`

Client: `Storage().connect().query_tbl(table_name)`


Open Questions FOGL-197
========================

… SELECT related other things?
------------------------------

Storage server fails (get halted) if malformed json supplied in where condition, it should be handled
error?

What about SELECT with limit, offset, order_by?

… Which layer will be responsible to create JSON Payload for storage sever?
---------------------------------------------------------------------------

a) storage client?

b) storage client consumer code?


if **a**, will the JSON (deep) check will be handled by client or server itself?


… Readings append INSERT vs COPY?
---------------------------------

Only READINGS table (plugin/ service) will be mapped for append/ fetch/ query/ purge.
COPY was the best solution for insertion as batch, Use `Readings::append`
