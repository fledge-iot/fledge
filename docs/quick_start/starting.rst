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

If authentication is enabled, which is the default mode for Fledge version 3.0 onward, then a number of the  commands require authentication. Authentication can be accomplished by several means;

  - Set the environment variable *FLEDGE_USER* to be the user name.
    
  - Pass the *-u* flag flag to the command to specify a user name.

  - Create an authentication file

  - If neither of the above are done the user will be prompted to enter a user name.

.. note::

   It is recommended to create an authentication file rather than pass parameters to the fledge command or set environment varaiables as both these methods can expose plain text user names, or passwords, to other users of the system.

In both cases the user will be prompted to enter a password. It is possible, but not recommended, to set an environment variable *FLEDGE_PASSWORD* or pass the *-p* flag on the command line, with the plain text version of the password.

.. code-block:: console

   $ /usr/local/fledge/bin/fledge -u admin stop
   Password:
   Stopping Fledge..........
   Fledge Stopped

.. note::

   The *start*, *status* and *help* commands do not require authentication.

It is also possible to use certificate based authentication to login to the system. In this case the "fledge" command line utility should be passed the *-c* flag with the name of the certificate file to use to authenticate.

.. code-block:: console

   $ /usr/local/fledge/bin/fledge -c ~/.fledge/admin.cert stop
   Stopping Fledge..........
   Fledge Stopped

.. note::

   Extreme caution should be taken when storing certificate files. They must not be readable by any other users within the system.

Following a successful authentication attempt a time based token is issued that allows the user to run further commands, for a limited time, without the need to authenticate again.

Authentication File
-------------------

The prompting for username and password when using the *fledge* script can be bypassed if an authentication file is created. This is a file that should be created in a directory called *.fledge* in the user's home directory.

The file created should be called *auth* and contains the credentials required to login. This may either be a username and password or the filename of a certficate to use to authenticate.

.. note::

   The *auth* file will only be read if the permissions on that file are set such that only the owner can read the file.

   .. code-block:: console

       $ chmod 600 ~/.fledge/auth

   In older versions of Fledge the *auth* file was simply called *~/.fledge*. If the older *.fledge* file exists it will still be used.

An example *auth* file, using the default username and password would be as follows

.. code-block:: console

   FLEDGE_USER=admin
   FLEDGE_PASSWORD=fledge

If using a certificate to authenticate the file would look as follow

.. code-block:: console

   FLEDGE_CERT=~/.auth/user.cert

The file name, minus the extension, should match the user name of the user.

.. note::

   In the above example the certificate has been placed in the .auth directory, this is not a requirement and the user name choose to place the certificate in any location that is convienent for them. However the certificate file should be protected sich that it can not be red or copied by other users.


