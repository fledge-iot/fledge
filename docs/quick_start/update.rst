.. Images
.. |alert| image:: ../images/alert.jpg

Package Updates
===============

Fledge will periodically check for updates to the various packages that are installed. If updates are available then this will be indicated by a status indicating on the bar at the top of the Fledge GUI.

+---------+
| |alert| |
+---------+

Clicking on the *bell* icon will display the current system alerts, including the details of the packages available to be updated.

Installing Updates
------------------

Updates must either be installed manually from the command line or via the Fledge API. To update via the API a call to the */fledge/update* should be made using the PUT method.

.. code-block:: console

   curl -X PUT http://localhost:8081/fledge/update

If the Fledge instance has been configured to require authentication then a valid authentication token must be passed in the request header and that authentication token must by for a user with administration rights on the instance.

.. code-block:: console

    curl -H "authorization: <token>" -X PUT http://localhost:8081/fledge/update

Manual updates can be down from the command line using the appropriate package manager for your Linux host. If using the *apt* package manager then the command would be

.. code-block:: console

   apt upgrade --only-upgrade 'fledge*'

Or for the *yum* package manager

.. code-block:: console

   yum upgrade 'fledge*'

.. note::

   These commands should be executed as the root user or using the sudo command.

