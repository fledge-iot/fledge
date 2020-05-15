.. Utilities and Scripts
.. https://docs.google.com/document/d/1JJDP7g25SWerNVCxgff02qp9msHbqA9nt3RAFx8-Qng

.. |br| raw:: html

   <br />

.. Images


.. Links

.. Links in new tabs


.. =============================================


*****************************
Fledge Utilities and Scripts
*****************************

The Fledge platform comes with a set of utilities and scripts to help users, developers and administrators with their day-by-day operations. These tools are under heavy development and you may expect incompatibilities in future versions, therefore it is highly recommended to check the revision history to verify the changes in new versions.


fledge
=======

``fledge`` is the first utility available with the platform, it is the control center for all the admin operations on Fledge.

In the current implementation, *fledge* provides these features:

- *start* Fledge
- *stop* Fledge
- *kill* Fledge processes
- Check the *status* of Fledge, i.e. whether it is running, starting or not running
- *reset* Fledge to its factory settings


Starting Fledge
----------------

``fledge start`` is the command to start Fledge. Since only one core microservice of Fledge can be executed in the same environment, the command checks if Fledge is already running, and if it does, it ends. The command also checks the presence of the *FLEDGE_ROOT* and *FLEDGE_DATA* environment variables. If the variables have not been set, it verifies if Fledge has been installed in the default position, which is */usr/local/fledge* or a position defined by the installed package, and it will set the missing variables accordingly. It will also take care of the *PYTHONPATH* variable.

In more specific terms, the command executes these steps:

- Check if Fledge is already running
- Check if the storage layer is *managed* or *unmanaged*. "managed" means that the storage layer relies on a storage system (i.e. a database, a set of files or in-memory structures) that are under exclusive control of Fledge. "unmanaged" means that the storage system is generic and potentially shared with other applications.
- Check if the storage plugin and the related storage system (for example a PostgreSQL database) is available. 
- Check if the metadata structure that is necessary to execute Fledge is already available in the storage layer. If the metadata is not available, it creates the data model and sets the factory settings that are necessary to start and use Fledge.
- Start the core microservice.
- Wait until the core microservice starts the Storage microservice and the initial required process that are necessary to handle other tasks and microservices.


Safe Mode
---------

It is possible to start Fledge in safe mode by passing the flag ``--safe-mode`` to the start command. In safe mode Fledge
will not start any of the south services or schedule any tasks, such as purge or north bound tasks. Safe mode allows
Fledge to be started and configured in those situations where a previous misconfiguration has rendered it impossible to
start and interact with Fledge.

Once started in safe mode any configuration changes should be made and then Fledge should be restarted in normal mode
to test those configuration changes.


Stopping Fledge
----------------

``fledge stop`` is the command used to stop Fledge. The command waits until all the tasks and services have been completed, then it stops the core service.


If Fledge Does Not Stop
------------------------

If Fledge does not stop, i.e. if by using the process status command ``ps`` you see Fledge processes still running, you can use ``fledge kill`` to kill them.

.. note:: The command issues a ``kill -9`` against the processes associated to Fledge. This is not recommended, unless Fledge cannot be stopped. The *stop* command. In other words, *kill* is your last resort before a reboot. If you must use the kill command, it means that there is a problem: please report this to the Fledge project slack channel.


Checking the Status of Fledge
------------------------------

``fledge status`` is used to provide the current status of tasks and microservices on the machine. The output is something like:

.. code-block:: console

  $ fledge status
  Fledge running.
  Fledge uptime:  2034 seconds.
  === Fledge services:
  fledge.services.core
  fledge.services.south --port=33074 --address=127.0.0.1 --name=HTTP_SOUTH
  fledge.services.south --port=33074 --address=127.0.0.1 --name=COAP
  === Fledge tasks:
  $ fledge_use_from_here stop
  Fledge stopped.
  $ fledge_use_from_here status
  Fledge not running.
  $

- The first row always indicates if Fledge is running or not
- The second row provides the uptime in seconds
- The next set of rows provides information regarding the microservices running on the machine
- The last set of rows provides information regarding the tasks running on the machine


Resetting Fledge
-----------------

It may occur that you want to restore Fledge to its factory settings, and this is what ``fledge reset`` does. The command also destroys all the data and all the configuration currently stored in Fledge, so you must use it at your own risk!

Fledge can be restored to its factory settings only when it is not running, hence you should stop it first. 

The command forces you to insert the word *YES*, all in uppercase, to continue:

.. code-block:: console

  $ fledge reset
  This script will remove all data stored in the server.
  Enter YES if you want to continue: YES
  $


