.. FogLAMP installation describes how to install FogLAMP

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. |build foglamp| raw:: html

   <a href="03_getting_started.html#building-foglamp" target="_blank">here</a>

.. |snappy| raw:: html

   <a href="https://en.wikipedia.org/wiki/Snappy_(package_manager)" target="_blank">Snappy</a>

.. |snapcraft| raw:: html

   <a href="https://snapcraft.io" target="_blank">snapcraft.io</a>

.. |foglamp-snap issues| raw:: html

   <a href="https://github.com/foglamp/foglamp-snap/issues" target="_blank">GitHub issues database</a>

.. |x86 Package| raw:: html

   <a href="https://s3.amazonaws.com/foglamp/snaps/x86_64/foglamp_1.0_amd64.snap" target="_blank">Snap for Intel x86_64 architecture</a>

.. |ARM Package| raw:: html

   <a href="https://s3.amazonaws.com/foglamp/snaps/armhf/foglamp_1.0_armhf.snap" target="_blank">Snap for ARM (armhf - ARM hard float) / Raspberry PI 2 & 3</a>

.. |Downloads page| raw:: html

   <a href="92_downloads.html" target="_blank">Downloads page</a>


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
  Starting FogLAMP......
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
  Starting FogLAMP......
  FogLAMP started.
  $


The setenv.sh Script
--------------------

In the *extras/scripts* folder of the newly installed FogLAMP you can find the *setenv.sh* script. This script can be used to set the environment variables used by FogLAMP and update your PATH environment variable. |br|
You can call the script from your shell or you can add the same command to your *.profile* script:

.. code-block:: console

  $ cat /usr/local/foglamp/extras/scripts/setenv.sh
  #!/bin/sh

  ##--------------------------------------------------------------------
  ## Copyright (c) 2018 OSIsoft, LLC
  ##
  ## Licensed under the Apache License, Version 2.0 (the "License");
  ## you may not use this file except in compliance with the License.
  ## You may obtain a copy of the License at
  ##
  ##     http://www.apache.org/licenses/LICENSE-2.0
  ##
  ## Unless required by applicable law or agreed to in writing, software
  ## distributed under the License is distributed on an "AS IS" BASIS,
  ## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  ## See the License for the specific language governing permissions and
  ## limitations under the License.
  ##--------------------------------------------------------------------

  #
  # This script sets the user environment to facilitate the administration
  # of FogLAMP
  #
  # You can execute this script from shell, using for example this command:
  #
  # source /usr/local/foglamp/extras/scripts/setenv.sh
  #
  # or you can add the same command at the bottom of your profile script
  # {HOME}/.profile.
  #

  export FOGLAMP_ROOT="/usr/local/foglamp"
  export FOGLAMP_DATA="${FOGLAMP_ROOT}/data"

  export PATH="${FOGLAMP_ROOT}/bin:${PATH}"

  $ source /usr/local/foglamp/extras/scripts/setenv.sh
  $


The foglamp.service Script
--------------------------

Another file available in the *extras/scripts* folder is the foglamp.service script. This script can be used to set FogLAMP as a Linux service. If you wish to do so, we recommend to install the FogLAMP package, but if you have a special build or for other reasons you prefer to work with FogLAMP built from source, this script will be quite helpful.

You can install FogLAMP as a service following these simple steps:

- After the ``make install`` command, copy *foglamp.service* with a simple name *foglamp* in the */etc/init.d* folder.
- Execute the command ``systemctl enable foglamp.service`` to enable FogLAMP as a service
- Execute the command ``systemctl start foglamp.service`` if you want to start FogLAMP

.. code-block:: console

  $ sudo cp /usr/local/foglamp/extras/scripts/foglamp.service /etc/init.d/foglamp
  $ sudo systemctl status foglamp.service
  ● foglamp.service
     Loaded: not-found (Reason: No such file or directory)
     Active: inactive (dead)
  $ sudo systemctl enable foglamp.service
  foglamp.service is not a native service, redirecting to systemd-sysv-install
  Executing /lib/systemd/systemd-sysv-install enable foglamp
  $ sudo systemctl status foglamp.service
  ● foglamp.service - LSB: FogLAMP
     Loaded: loaded (/etc/init.d/foglamp; bad; vendor preset: enabled)
     Active: inactive (dead)
       Docs: man:systemd-sysv-generator(8)
  $ sudo systemctl start foglamp.service
  $ sudo systemctl status foglamp.service
  ● foglamp.service - LSB: FogLAMP
     Loaded: loaded (/etc/init.d/foglamp; bad; vendor preset: enabled)
     Active: active (running) since Sun 2018-03-25 13:03:31 BST; 2min 8s ago
       Docs: man:systemd-sysv-generator(8)
    Process: 1661 ExecStart=/etc/init.d/foglamp start (code=exited, status=0/SUCCESS)
      Tasks: 14
     Memory: 79.5M
        CPU: 2.888s
     CGroup: /system.slice/foglamp.service
             ├─1759 python3 -m foglamp.services.core
             ├─1764 /usr/local/foglamp/services/storage --address=0.0.0.0 --port=46309
             ├─1814 /bin/sh services/south --port=46309 --address=127.0.0.1 --name=COAP
             ├─1815 python3 -m foglamp.services.south --port=46309 --address=127.0.0.1 --name=COAP
             ├─1816 /bin/sh services/south --port=46309 --address=127.0.0.1 --name=HTTP_SOUTH
             └─1817 python3 -m foglamp.services.south --port=46309 --address=127.0.0.1 --name=HTTP_SOUTH
  $


Installing the Snap Package
===========================

|snappy| is a software deployment and package management system originally designed and built by Canonical. Snappy is now available for many Linux distributions, including Ubuntu, Ubuntu Core, Debian, Fedora, Archlinux, Raspbian, Suse, the Yocto project and many others. The package management is based on snap packages that can be installed in a *transactional* environment, i.e. the packages have a current installation and the system can maintain a given number of previous installations. In case of issues with the new packages, Administrators can easily revert to previous installations.

More information regarding the package manager are available on the |snapcraft| website.

.. note:: The snap package is still experimental, if you find any issue you should report them to the |foglamp-snap issues| for the *foglamp-snap* project.


Obtaining the Snap Package
--------------------------

Check the |Downloads page| to find the package to install.

Once you have downloaded the package, install it using the ``snap install`` command. Note that you may need to install it as superuser (or by using the ``sudo`` command). The current version of FogLAMP must be installed using the *--devmode* argument, since there are currently no security confinments.

For example, if you are installing FogLAMP on an Intel x86/64 machine, you can type:

.. code-block:: console

  $ sudo snap install --devmode foglamp_<version>_amd64.snap
  foglamp <version> installed 
  $

... where *<version>* is the selected version that you are installing.

Congratulations! This is all you need to do, now FogLAMP is ready to run.


Starting FogLAMP from Snap
--------------------------

You can use the same ``foglamp`` command we discussed in the previous section to start the core microservice of FogLAMP:


.. code-block:: console

  $ foglamp start
  Starting PostgreSQL...
  PostgreSQL started.
  Building the metadata for the FogLAMP Plugin...
  Build complete.
  Starting FogLAMP......
  FogLAMP started.
  $
  $ foglamp status
  FogLAMP starting.
  $
  $ foglamp status
  FogLAMP running.
  FogLAMP uptime:  16 seconds.
  FogLAMP Records: 0 read, 0 sent, 0 purged.
  FogLAMP does not require authentication.
  === FogLAMP services:
  foglamp.services.core
  foglamp.services.south --port=37829 --address=127.0.0.1 --name=COAP
  === FogLAMP tasks:
  foglamp.tasks.north.sending_process --stream_id 1 --debug_level 1 --port=37829 --address=127.0.0.1 --name=sending process
  foglamp.tasks.statistics --port=37829 --address=127.0.0.1 --name=stats collector
  $
  $ foglamp stop
  Stopping FogLAMP.............
  Stopping PostgreSQL...
  PostgreSQL stopped.
  FogLAMP stopped.
  $

From the output of the *foglamp* command you can notice that now the PostgreSQL database is managed by FogLAMP itself. In fact, the snap package also installs an embedded version of PostgreSQL that should be exclusively used by FogLAMP. 


Data Directories with the Snap Package
-------------------------------------------

Snap is designed to be self-contained and it does not require any user setting, therefore there are no *FOGLAMP_ROOT* or *FOGLAMP_DATA* variables to set. The FogLAMP package is installed in readonly and it is visible by the user in the */snap/foglamp* directory, data is stored in the *snap/foglamp* directory under the user home directory. The data directory also contains the PostgreSQL database.


.. code-block:: console

  $ ls -l /snap
  total 20
  drwxr-xr-x  5 root root 4096 Dec 11 15:06 ./
  drwxr-xr-x 23 root root 4096 Dec 11 14:14 ../
  drwxr-xr-x  2 root root 4096 Dec 11 15:06 bin/
  drwxr-xr-x  3 root root 4096 Dec 11 14:41 core/
  drwxr-xr-x  3 root root 4096 Dec 11 15:06 foglamp/
  $
  $ ls -l /snap/foglamp
  total 8
  drwxr-xr-x 3 root root 4096 Dec 11 15:06 ./
  drwxr-xr-x 5 root root 4096 Dec 11 15:06 ../
  lrwxrwxrwx 1 root root    2 Dec 11 15:06 current -> x1/
  drwxr-xr-x 8 root root  137 Dec 11 15:04 x1/ 
  $
  $ ls -l /snap/foglamp/x1
  total 5
  drwxr-xr-x  8 root root  137 Dec 11 15:04 ./
  drwxr-xr-x  3 root root 4096 Dec 11 15:06 ../
  drwxr-xr-x  2 root root   95 Dec 11 14:16 bin/
  -rwxr-xr-x  1 root root  378 Dec 11 15:04 command-foglamp.wrapper*
  drwxr-xr-x 13 root root  279 Dec 11 15:04 etc/
  drwxr-xr-x  5 root root   71 Nov 21  2016 lib/
  drwxr-xr-x  3 root root   43 Dec 11 14:16 meta/
  drwxr-xr-x  7 root root   99 Dec 11 15:04 usr/
  drwxr-xr-x  4 root root   37 Dec 11 15:04 var/
  $
  $  $ ls -l $HOME/snap
  total 4
  drwxr-xr-x 4 ubuntu ubuntu 4096 Dec 11 15:07 foglamp
  $ ls -l /home/ubuntu/snap/foglamp/
  total 8
  drwxr-xr-x 4 ubuntu ubuntu 4096 Dec 11 15:07 common
  lrwxrwxrwx 1 ubuntu ubuntu    2 Dec 11 14:54 current -> x1
  drwxr-xr-x 2 ubuntu ubuntu 4096 Dec 11 15:07 x1
  $ ls -l /home/ubuntu/snap/foglamp/common/
  total 8
  drwxr-xr-x 2 ubuntu ubuntu 4096 Dec 11 15:07 etc
  drwxrwxr-x 3 ubuntu ubuntu 4096 Dec 11 15:07 storage
  $ ls -l /home/ubuntu/snap/foglamp/common/storage/postgres/pgsql/
  total 8
  drwx------ 19 ubuntu ubuntu 4096 Dec 11 15:07 data
  -rw-------  1 ubuntu ubuntu  506 Dec 11 15:17 logger
  $ ls -l /home/ubuntu/snap/foglamp/common/storage/postgres/pgsql/data/
  total 120
  drwx------ 6 ubuntu ubuntu  4096 Dec 11 15:07 base
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:08 global
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_clog
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_commit_ts
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_dynshmem
  -rw------- 1 ubuntu ubuntu  4462 Dec 11 15:07 pg_hba.conf
  -rw------- 1 ubuntu ubuntu  1636 Dec 11 15:07 pg_ident.conf
  drwx------ 4 ubuntu ubuntu  4096 Dec 11 15:07 pg_logical
  drwx------ 4 ubuntu ubuntu  4096 Dec 11 15:07 pg_multixact
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_notify
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_replslot
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_serial
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_snapshots
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_stat
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:18 pg_stat_tmp
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_subtrans
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_tblspc
  drwx------ 2 ubuntu ubuntu  4096 Dec 11 15:07 pg_twophase
  -rw------- 1 ubuntu ubuntu     4 Dec 11 15:07 PG_VERSION
  drwx------ 3 ubuntu ubuntu  4096 Dec 11 15:07 pg_xlog
  -rw------- 1 ubuntu ubuntu    88 Dec 11 15:07 postgresql.auto.conf
  -rw------- 1 ubuntu ubuntu 21344 Dec 11 15:07 postgresql.conf
  -rw------- 1 ubuntu ubuntu   121 Dec 11 15:07 postmaster.opts
  -rw------- 1 ubuntu ubuntu   117 Dec 11 15:07 postmaster.pid
  $


