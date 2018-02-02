.. Utilities and Scripts
.. https://docs.google.com/document/d/1JJDP7g25SWerNVCxgff02qp9msHbqA9nt3RAFx8-Qng

.. |br| raw:: html

   <br />

.. Images


.. Links


.. =============================================


*****************************
FogLAMP Utilities and Scripts
*****************************

The FogLAMP platform comes with a set of utilities and scripts to help users, developers and administrators with their day-by-day operations. These tools are under heavy development and you may expect incompatibilities in future versions, therefore it is higly recommended to check the revision history to verify if your scripts based on the FogLAMP utilities can still working properly.

foglamp
=======

``foglamp`` is the first utility available with the platform, it is in some way the control center for all the admin operations on FogLAMP. |br| In the current implementation, *foglamp* provides these features:

- **start** FogLAMP
- **stop** FogLAMP
- Check the **status** of FogLAMP, i.e. whether it is running, starting or not running
- **reset** FogLAMP to its factory settings

Starting FogLAMP
----------------

``foglamp start`` is the command to start FogLAMP. Since in its current implementation, only one core microservice of FogLAMP can be executed in the same environment, the command checks if FogLAMP is already running, and if it does, it ends. The command also checks the presence of the *FOGLAMP_ROOT* and *FOGLAMP_DATA* environment variables. If the variables have not been set, it verifies if FogLAMP has been installed in the default position, which is */usr/local/foglamp* or a position defined by the installed package, and it will set the missing variables accordingly. It will asso take care of the *PYTHONPATH* variable.

In more specific terms, the command executes these steps:

- Check if FogLAMP is already running
- Check if the storage layer is managed or unmanaged. "managed" means that the storage layer relies on a storage system (i.e. a database, a set of files or in-memory structures) that are under exclusive control of FogLAMP. "unmanaged" means that the storage system is generic and potentially shared with other applications.
- Check if the storage plugin and the related storage system (for example a PosrgreSQL database) is available. 
- Check if the metadata structure that is necessary to execute FogLAMP is already available in the storage layer. If the metadata is not available, it creates the data model and stors ethe factory settings that are necessary to start and use FogLAMP.
- Start the core microservice.
- Wait until the core microservice starts the Storage microservice and the initial required process that are necessary to handle other tasks and microservices.


Stopping FogLAMP
----------------

``foglamp stop`` is the command used to stop FogLAMP. In its current implementation, the command kills the processes associated to the FogLAMP microservices on the machine. A later version will execute a more graceful shutdown.


Checking the Status of FogLAMP
------------------------------

``foglamp status`` is used to provide the current status of tasks and microservices on the machine. The output is something like:

.. code-block:: console

  $ foglamp status
  FogLAMP running.
  FogLAMP uptime:  2034 seconds.
  === FogLAMP services:
  foglamp.services.core
  foglamp.services.south --port=33074 --address=127.0.0.1 --name=HTTP_SOUTH
  foglamp.services.south --port=33074 --address=127.0.0.1 --name=COAP
  === FogLAMP tasks:
  $

- The first row always indicates if FogLAMP is running or not
- The second row provides the uptime in seconds
- The next set of rows provides information regarding the microservices running on the machine
- The last set of rows provides information regarding the tasks running on the machine


Resetting FogLAMP
-----------------

It may occur that you want to restore FogLAMP to its factory settings, and this is what ``foglamp reset`` does. The command also destroys all the data and all the configuration currently stored in FogLAMP, so you must use at your own risk!

FogLAMP can be restored to its factory settings only when it is not running, hence you should stop it first. 

The command forces you to insert the word *YES*, all in uppercase, to continue:

.. code-block:: console

$ foglamp reset
This script will remove all data stored in the server.
Enter YES if you want to continue: YES
$

