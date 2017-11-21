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
-------------------------------------

Make sure you have pre-requisite installed.

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

    `sudo apt-get install libboost-dev libboost-system-dev libboost-thread-dev libpq-dev`

    `sudo apt-get install cmake`

    `sudo apt-get install g++`

    `sudo apt-get install make`


.. _demo test scripts:

… where can I find the test (demo) scripts?
------------------------------------------
There are some curl scripts that demonstrate the usage in FogLAMP/test/storage.


.. _DB connection and snap:

… how can I use different db connection?
------------------------------------------

Code allows the environment variable DB_CONNECTION to override the default connection string, so you can set this to

:Example:

     `export DB_CONNECTION="dbname=foglamp host=/tmp"`

If you are installing Postgres via the snap package

… How to run  queries?
----------------------

See `Storage Layer Architecture Document`_ and `Storage Client Usage Document`_

.. _Storage Layer Architecture Document: https://docs.google.com/document/d/1qGIswveF9p2MmAOw_W1oXpo_aFUJd3bXBkW563E16g0/edit

.. _Storage Client Usage Document: https://docs.google.com/document/d/1vzZf5Fu3prQ-dsy1zB0iOOFAa9jbAc5KrfzJV9K2bAI/edit#
