Starting and stopping Fledge
=============================

Fledge administration is performed using the “fledge” command line utility.  You must first ssh into the host system.  The Fledge utility is installed by default in /usr/local/fledge/bin.

The following command options are available:

  - **Start:** Start the Fledge system
  - **Stop:** Stop the Fledge system
  - **Status:** Lists currently running Fledge services and tasks
  - **Reset:** Delete all data and configuration and return Fledge to factory settings
  - **Kill:** Kill Fledge services that have not correctly responded to Stop
  - **Help:** Describe Fledge options

For example, to start the Fledge system, open a session to the Fledge device and type::

/usr/local/fledge/bin/fledge start

If authentication is enabled, which is the default mode for Fledge version 3.0 onward, then the commands can be passed a username, using the -u flag and will prompt for a password for that user.

.. code-block:: console

   $ /usr/local/fledge/bin/fledge -u admin stop
   Password:
   Stopping Fledge..........
   Fledge Stopped

.. note::

   The *start* and *status* commands do not require authentication.
