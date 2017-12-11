.. FogLAMP installation describes how to install FogLAMP

.. |br| raw:: html

   <br />

.e Images

.. Links

.. Links in new tabs

.. |build foglamp| raw:: html

   <a href="03_getting_started.html#building-foglamp" target="_blank">here</a>


.. =============================================


********************
FogLAMP Installation
********************

Installing FogLAMP using defaults is straightforward: a ``make install`` or a ``snap install`` command is all you need to type. In environments where the defaults do not fit, you will need to execute few more steps. This chapter describes the default installation of FogLAMP and the most common scenarios where administrators need to modify the default behavior.


Installing FogLAMP from a Build
===============================

Once you have built FogLAMP following the instructions presented |build foglamp|, you can execute the default installation with the ``make install`` command. By default, FogLAMP is installed from build in the root directory, under */usr/local/foglamp*. Since the root directory */* is a protected a system location, you will need superuser privileges to execute the command. Therefore, if you are not superuser, you should login as superuser or you should use the ``sudo`` command.

.. code-block:: console

  $ sudo make install
   mkdir -p /usr/local/foglamp
  cd cmake_build ; cmake /home/ubuntu/FogLAMP/
  -- Boost version: 1.58.0
  -- Found the following Boost libraries:
  --   system
  --   thread
  --   chrono
  --   date_time
  --   atomic
  -- Configuring done
  -- Generating done
  -- Build files have been written to: /home/ubuntu/FogLAMP/cmake_build
  cd cmake_build ; make
  ...
  cp -r python_build/lib/* /usr/local/foglamp/python
  pip3 install -Ir python/requirements.txt
  ...
  mkdir -p /usr/local/foglamp/scripts
  mkdir -p /usr/local/foglamp/scripts/common
  cp scripts/common/*.sh /usr/local/foglamp/scripts/common
  mkdir -p /usr/local/foglamp/scripts/plugins/storage
  cp scripts/plugins/storage/postgres /usr/local/foglamp/scripts/plugins/storage
  mkdir -p /usr/local/foglamp/scripts/services
  cp scripts/services/south /usr/local/foglamp/scripts/services
  cp scripts/services/storage /usr/local/foglamp/scripts/services
  mkdir -p /usr/local/foglamp/scripts/tasks
  cp scripts/tasks/north /usr/local/foglamp/scripts/tasks
  cp scripts/tasks/purge /usr/local/foglamp/scripts/tasks
  cp scripts/tasks/statistics /usr/local/foglamp/scripts/tasks
  cp scripts/storage /usr/local/foglamp/scripts
  mkdir -p /usr/local/foglamp/bin
  cp scripts/extras/fogbench /usr/local/foglamp/bin
  cp scripts/foglamp /usr/local/foglamp/bin
  mkdir -p /usr/local/foglamp/extras
  mkdir -p /usr/local/foglamp/extras/python
  cp -r extras/python/fogbench /usr/local/foglamp/extras/python
  cp -r data /usr/local/foglamp
  chown -R ubuntu:ubuntu /usr/local/foglamp/data
  $

These are the main steps of the installation:
- Create the */usr/local/foglamp* directory, if it does not exist
- Build the code that has not been compiled and built yet
- Create all the necessary destination directories and copy the executables, scripts and configuration files
- Change the ownership of the *data* directory, if the install user is a superuser (we recommend to run FogLAMP as regular user, i.e. not as superuser).

FogLAMP is now present in */usr/local/foglamp* and ready to start. The start script is in the *bin* directory

.. code-block:: console

  $ cd /usr/local/foglamp/
  $ ls -l
  total 28
  drwxr-xr-x 2 root   root   4096 Dec 11 13:38 bin
  drwxr-xr-x 3 ubuntu ubuntu 4096 Dec 11 13:38 data
  drwxr-xr-x 3 root   root   4096 Dec 11 13:38 extras
  drwxr-xr-x 3 root   root   4096 Dec 11 13:38 plugins
  drwxr-xr-x 3 root   root   4096 Dec 11 13:38 python
  drwxr-xr-x 6 root   root   4096 Dec 11 13:38 scripts
  drwxr-xr-x 2 root   root   4096 Dec 11 13:38 services
  $
  $ bin/foglamp
  Usage: foglamp {start|stop|status|help}
  $
  $ bin/foglamp help
  Usage: foglamp {start|stop|status|help}
  FogLAMP admin script
  The script is used to start FogLAMP
  Arguments:
   start   - Start FogLAMP core (core will start other services).
   stop    - Stop all FogLAMP services and processes
   status  - Show the status for the FogLAMP services
   help    - This text
  ubuntu@ubuntu:/usr/local/foglamp$
  $
  $ bin/foglamp start
  FogLAMP started.
  $ 


Installing FogLAMP in a Different Destination Directory
-------------------------------------------------------

The destination directory for FogLAMP is the root directory */*.  You can change the destination by setting the *make* variable *DESTDIR*. For example, if you want to install FogLAMP in */opt* you should execute this command:

.. code-block:: console

  $ sudo make install DESTDIR=/opt
  mkdir -p /opt/usr/local/foglamp
  ...
  $ ls -l
  total 36
  drwxr-xr-x 9 root   root   4096 Dec 11 13:49 ./
  drwxr-xr-x 3 root   root   4096 Dec 11 13:49 ../
  drwxr-xr-x 2 root   root   4096 Dec 11 13:49 bin/
  drwxr-xr-x 3 ubuntu ubuntu 4096 Dec 11 13:49 data/
  drwxr-xr-x 3 root   root   4096 Dec 11 13:49 extras/
  drwxr-xr-x 3 root   root   4096 Dec 11 13:49 plugins/
  drwxr-xr-x 3 root   root   4096 Dec 11 13:49 python/
  drwxr-xr-x 6 root   root   4096 Dec 11 13:49 scripts/
  drwxr-xr-x 2 root   root   4096 Dec 11 13:49 services/
  $ 


Environment Variables
---------------------

In order to operate, FogLAMP requires two environment variables:
- **FOGLAMP_ROOT**: the root directory for FogLAMP. The default is */usr/local/foglamp*
- **FOGLAMP_DATA**: the data directory. The default is *$FOGLAMP_ROOT/data*, hence whichever value *FOGLAMP_ROOT* has plus the *data* sub-directory, or */usr/local/foglamp/data* in case *FOGLAMP_ROOT* is set as default value.

If you have installed FogLAMP in a non-default directory, you must at least set the new root directory before you start the platform. For example, supposing that the destination directory is */opt* and the package has been installed in */opt/usr/local/foglamp*, you should type:

.. code-block:: console

  $ export FOGLAMP_ROOT="/opt/usr/local/foglamp"
  $ cd /opt/usr/local/foglamp/
  $ bin/foglamp start
  FogLAMP started.
  $


Installing the Snap Package
===========================

