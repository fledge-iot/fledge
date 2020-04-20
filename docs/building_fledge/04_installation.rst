.. Fledge installation describes how to install Fledge

.. |br| raw:: html

   <br />

.. Images

.. Links

.. Links in new tabs

.. |build fledge| raw:: html

   <a href="building_fledge.html" target="_blank">here</a>

.. |snappy| raw:: html

   <a href="https://en.wikipedia.org/wiki/Snappy_(package_manager)" target="_blank">Snappy</a>

.. |snapcraft| raw:: html

   <a href="https://snapcraft.io" target="_blank">snapcraft.io</a>

.. |x86 Package| raw:: html

   <a href="https://s3.amazonaws.com/fledge/snaps/x86_64/fledge_1.0_amd64.snap" target="_blank">Snap for Intel x86_64 architecture</a>

.. |ARM Package| raw:: html

   <a href="https://s3.amazonaws.com/fledge/snaps/armhf/fledge_1.0_armhf.snap" target="_blank">Snap for ARM (armhf - ARM hard float) / Raspberry PI 2 & 3</a>

.. |Downloads page| raw:: html

   <a href="92_downloads.html" target="_blank">Downloads page</a>


.. =============================================


********************
Fledge Installation
********************

Installing Fledge using defaults is straightforward: depending on the usage, you may install a new version from source or from a pre-built package. In environments where the defaults do not fit, you will need to execute few more steps. This chapter describes the default installation of Fledge and the most common scenarios where administrators need to modify the default behavior.


Installing Fledge from a Build
===============================

Once you have built Fledge following the instructions presented |build fledge|, you can execute the default installation with the ``make install`` command. By default, Fledge is installed from build in the root directory, under */usr/local/fledge*. Since the root directory */* is a protected a system location, you will need superuser privileges to execute the command. Therefore, if you are not superuser, you should login as superuser or you should use the ``sudo`` command.

.. code-block:: console

  $ sudo make install
  mkdir -p /usr/local/fledge
  Installing Fledge version 1.3.1, DB schema 2
  -- Fledge DB schema check OK: Info: /usr/local/fledge is empty right now. Skipping DB schema check.
  cp VERSION /usr/local/fledge
  cd cmake_build ; cmake /home/fledge/Fledge/
  -- Boost version: 1.58.0
  -- Found the following Boost libraries:
  --   system
  --   thread
  --   chrono
  --   date_time
  --   atomic
  -- Found SQLite version 3.11.0: /usr/lib/x86_64-linux-gnu/libsqlite3.so
  -- Boost version: 1.58.0
  -- Found the following Boost libraries:
  --   system
  --   thread
  --   chrono
  --   date_time
  --   atomic
  -- Configuring done
  -- Generating done
  -- Build files have been written to: /home/fledge/Fledge/cmake_build
  cd cmake_build ; make
  make[1]: Entering directory '/home/fledge/Fledge/cmake_build'
  ...
  $

These are the main steps of the installation:

- Create the */usr/local/fledge* directory, if it does not exist
- Build the code that has not been compiled and built yet
- Create all the necessary destination directories and copy the executables, scripts and configuration files
- Change the ownership of the *data* directory, if the install user is a superuser (we recommend to run Fledge as regular user, i.e. not as superuser).

Fledge is now present in */usr/local/fledge* and ready to start. The start script is in the */usr/local/fledge/bin* directory

.. code-block:: console

  $ cd /usr/local/fledge/
  $ ls -l
  total 32
  drwxr-xr-x 2 root    root    4096 Apr 24 18:07 bin
  drwxr-xr-x 4 fledge fledge 4096 Apr 24 18:07 data
  drwxr-xr-x 4 root    root    4096 Apr 24 18:07 extras
  drwxr-xr-x 4 root    root    4096 Apr 24 18:07 plugins
  drwxr-xr-x 3 root    root    4096 Apr 24 18:07 python
  drwxr-xr-x 6 root    root    4096 Apr 24 18:07 scripts
  drwxr-xr-x 2 root    root    4096 Apr 24 18:07 services
  -rwxr-xr-x 1 root    root      37 Apr 24 18:07 VERSION
  $
  $ bin/fledge
  Usage: fledge {start|stop|status|reset|kill|help|version}
  $
  $ bin/fledge help
  Usage: fledge {start|stop|status|reset|kill|help|version}
  Fledge v1.3.1 admin script
  The script is used to start Fledge
  Arguments:
   start   - Start Fledge core (core will start other services).
   stop    - Stop all Fledge services and processes
   kill    - Kill all Fledge services and processes
   status  - Show the status for the Fledge services
   reset   - Restore Fledge factory settings
             WARNING! This command will destroy all your data!
   version - Print Fledge version
   help    - This text
  $
  $ bin/fledge start
  Starting Fledge......
  Fledge started.
  $ 


Installing Fledge in a Different Destination Directory
-------------------------------------------------------

The destination directory for Fledge is the root directory */*.  You can change the destination by setting the *make* variable *DESTDIR*. For example, if you want to install Fledge in */opt* you should execute this command:

.. code-block:: console

  $ sudo make install DESTDIR=/opt
  mkdir -p /opt/usr/local/fledge
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

In order to operate, Fledge requires two environment variables:

- **FLEDGE_ROOT**: the root directory for Fledge. The default is */usr/local/fledge*
- **FLEDGE_DATA**: the data directory. The default is *$FLEDGE_ROOT/data*, hence whichever value *FLEDGE_ROOT* has plus the *data* sub-directory, or */usr/local/fledge/data* in case *FLEDGE_ROOT* is set as default value.

If you have installed Fledge in a non-default directory, you must at least set the new root directory before you start the platform. For example, supposing that the destination directory is */opt* and the package has been installed in */opt/usr/local/fledge*, you should type:

.. code-block:: console

  $ export FLEDGE_ROOT="/opt/usr/local/fledge"
  $ cd /opt/usr/local/fledge/
  $ bin/fledge start
  Starting Fledge......
  Fledge started.
  $


The setenv.sh Script
--------------------

In the *extras/scripts* folder of the newly installed Fledge you can find the *setenv.sh* script. This script can be used to set the environment variables used by Fledge and update your PATH environment variable. |br|
You can call the script from your shell or you can add the same command to your *.profile* script:

.. code-block:: console

  $ cat /usr/local/fledge/extras/scripts/setenv.sh
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
  # of Fledge
  #
  # You can execute this script from shell, using for example this command:
  #
  # source /usr/local/fledge/extras/scripts/setenv.sh
  #
  # or you can add the same command at the bottom of your profile script
  # {HOME}/.profile.
  #

  export FLEDGE_ROOT="/usr/local/fledge"
  export FLEDGE_DATA="${FLEDGE_ROOT}/data"

  export PATH="${FLEDGE_ROOT}/bin:${PATH}"
  export LD_LIBRARY_PATH="${FLEDGE_ROOT}/lib:${LD_LIBRARY_PATH}"

  $ source /usr/local/fledge/extras/scripts/setenv.sh
  $


The fledge.service Script
--------------------------

Another file available in the *extras/scripts* folder is the fledge.service script. This script can be used to set Fledge as a Linux service. If you wish to do so, we recommend to install the Fledge package, but if you have a special build or for other reasons you prefer to work with Fledge built from source, this script will be quite helpful.

You can install Fledge as a service following these simple steps:

- After the ``make install`` command, copy *fledge.service* with a simple name *fledge* in the */etc/init.d* folder.
- Execute the command ``systemctl enable fledge.service`` to enable Fledge as a service
- Execute the command ``systemctl start fledge.service`` if you want to start Fledge

.. code-block:: console

  $ sudo cp /usr/local/fledge/extras/scripts/fledge.service /etc/init.d/fledge
  $ sudo systemctl status fledge.service
  ● fledge.service
     Loaded: not-found (Reason: No such file or directory)
     Active: inactive (dead)
  $ sudo systemctl enable fledge.service
  fledge.service is not a native service, redirecting to systemd-sysv-install
  Executing /lib/systemd/systemd-sysv-install enable fledge
  $ sudo systemctl status fledge.service
  ● fledge.service - LSB: Fledge
     Loaded: loaded (/etc/init.d/fledge; bad; vendor preset: enabled)
     Active: inactive (dead)
       Docs: man:systemd-sysv-generator(8)
  $ sudo systemctl start fledge.service
  $ sudo systemctl status fledge.service
  ● fledge.service - LSB: Fledge
     Loaded: loaded (/etc/init.d/fledge; bad; vendor preset: enabled)
     Active: active (running) since Sun 2018-03-25 13:03:31 BST; 2min 8s ago
       Docs: man:systemd-sysv-generator(8)
    Process: 1661 ExecStart=/etc/init.d/fledge start (code=exited, status=0/SUCCESS)
      Tasks: 14
     Memory: 79.5M
        CPU: 2.888s
     CGroup: /system.slice/fledge.service
             ├─1759 python3 -m fledge.services.core
             └─1764 /usr/local/fledge/services/storage --address=0.0.0.0 --port=46309
  $

|br|


Installing the Debian Package
=============================

We have versions of Fledge available as Debian packages for you. Check the |Downloads page| to review which versions and platforms are available.


Obtaining and Installing the Debian Package
-------------------------------------------

Check the |Downloads page| to find the package to install.

Once you have downloaded the package, install it using the ``apt-get`` command. You can use ``apt-get`` to install a local Debian package and automatically retrieve all the necessary packages that are defined as pre-requisites for Fledge.  Note that you may need to install the package as superuser (or by using the ``sudo`` command) and move the package to the apt cache directory first (``/var/cache/apt/archives``).

For example, if you are installing Fledge on an Intel x86_64 machine, you can type this command to download the package:

.. code-block:: console

  $ wget https://s3.amazonaws.com/fledge/debian/x86_64/fledge-1.3.1-x86_64_ubuntu_16_04.deb
  --2018-04-24 18:22:08--  https://s3.amazonaws.com/fledge/debian/x86_64/fledge-1.3.1-x86_64_ubuntu_16_04.deb
  Resolving s3.amazonaws.com (s3.amazonaws.com)... 52.216.133.221
  Connecting to s3.amazonaws.com (s3.amazonaws.com)|52.216.133.221|:443... connected.
  HTTP request sent, awaiting response... 200 OK
  Length: 496094 (484K) [application/x-deb]
  Saving to: ‘fledge-1.3.1-x86_64_ubuntu_16_04.deb’

  fledge-1.3.1-x86_64_ubuntu_16_04.deb     100%[=============================================================>] 484.47K   521KB/s    in 0.9s
  2018-04-24 18:22:10 (521 KB/s) - ‘fledge-1.3.1-x86_64_ubuntu_16_04.deb’ saved [496094/496094]
  $

We recommend to execute an *update-upgrade-update* of the system first, then you may copy the Fledge package in the *apt cache* directory and install it.


.. code-block:: console

  $ sudo apt update
  Hit:1 http://gb.archive.ubuntu.com/ubuntu xenial InRelease
  ...
  $ sudo apt upgrade
  ...
  $ sudo apt update
  ...
  $ sudo cp fledge-1.3.1-x86_64_ubuntu_16_04.deb /var/cache/apt/archives/.
  ...
  $ sudo apt install /var/cache/apt/archives/fledge-1.3.1-x86_64_ubuntu_16_04.deb
  Reading package lists... Done
  Building dependency tree
  Reading state information... Done
  Note, selecting 'fledge' instead of '/var/cache/apt/archives/fledge-1.3.1-x86_64_ubuntu_16_04.deb'
  The following packages were automatically installed and are no longer required:
  ...
  Unpacking fledge (1.3.1) ...
  Setting up fledge (1.3.1) ...
  Resolving data directory
  Data directory does not exist. Using new data directory
  Installing service script
  Generating certificate files
  Certificate files do not exist. Generating new certificate files.
  Creating a self signed SSL certificate ...
  Certificates created successfully, and placed in data/etc/certs
  Setting ownership of Fledge files
  Enabling Fledge service
  fledge.service is not a native service, redirecting to systemd-sysv-install
  Executing /lib/systemd/systemd-sysv-install enable fledge
  Starting Fledge service
  $ 

As you can see from the output, the installation automatically registers Fledge as a service, so it will come up at startup and it is already up and running when you complete the command.

Check the newly installed package:

.. code-block:: console

  $ sudo dpkg -l | grep fledge
  ii  fledge            1.3.1             amd64        Fledge, the open source platform for the Internet of Things
  $


You can also check the service currently running:

.. code-block:: console

  $ sudo systemctl status fledge.service
  ● fledge.service - LSB: Fledge
   Loaded: loaded (/etc/init.d/fledge; bad; vendor preset: enabled)
   Active: active (running) since Thu 2018-05-10 03:48:20 BST; 1min 31s ago
     Docs: man:systemd-sysv-generator(8)
  Process: 1088 ExecStart=/etc/init.d/fledge start (code=exited, status=0/SUCCESS)
    Tasks: 14
   Memory: 87.2M
      CPU: 2.603s
   CGroup: /system.slice/fledge.service
           ├─1218 python3 -m fledge.services.core
           └─1226 /usr/local/fledge/services/storage --address=0.0.0.0 --port=44530

  ...
  $


Check if Fledge is up and running with the ``fledge`` command:

.. code-block:: console

  $ /usr/local/fledge/bin/fledge status
  Fledge v1.3.1 running.
  Fledge Uptime:  162 seconds.
  Fledge records: 0 read, 0 sent, 0 purged.
  Fledge does not require authentication.
  === Fledge services:
  fledge.services.core
  ...
  === Fledge tasks:
  ...
  $


Don't forget to add the *setenv.sh* available in the /usr/local/fledge/extras/scripts* directory to your *.profile* user startup script if you want to have an easy access to the Fledge tools, and...


...Congratulations! This is all you need to do, now Fledge is ready to run.


Upgrading or Downgrading Fledge
--------------------------------

Upgrading or downgrading Fledge, starting from version 1.2, is as easy as installing it from scratch: simply follow the instructions in the previous section regarding the installation and the package will take care of the upgrade/downgrade path. The installation will not proceed if there is not a path to upgrade or downgrade from the currently installed version. You should still check the pre-requisites before you apply the upgrade. Clearly the old data will not be lost, there will be a schema upgrade/downgrade, if required.


Uninstalling the Debian Package
-------------------------------

Use the ``apt`` or the ``apt-get`` command to uninstall Fledge:

.. code-block:: console

  $ sudo apt remove fledge
  Reading package lists... Done
  ...
  The following packages will be REMOVED
  fledge
  0 to upgrade, 0 to newly install, 1 to remove and 2 not to upgrade.
  After this operation, 0 B of additional disk space will be used.
  Do you want to continue? [Y/n]
  (Reading database ... 211747 files and directories currently installed.)
  Removing fledge (1.3.1) ...
  Fledge is currently running.
  Stop Fledge service.
  Kill Fledge.
  Remove python cache files.
  find: ‘/usr/local/fledge/scripts/common/__pycache__’: No such file or directory
  Disable Fledge service.
  fledge.service is not a native service, redirecting to systemd-sysv-install
  Executing /lib/systemd/systemd-sysv-install disable fledge
  insserv: warning: current start runlevel(s) (empty) of script `fledge' overrides LSB defaults (2 3 4 5).
  insserv: warning: current stop runlevel(s) (0 1 2 3 4 5 6) of script `fledge' overrides LSB defaults (0 1 6).
  Remove Fledge service script
  Reset systemctl
  dpkg: warning: while removing fledge, directory '/usr/local/fledge' not empty so not removed
  $

The command also removes the service installed. |br| You may notice the warning in the last row of the command output: this is due to the fact that the data directory (``/usr/local/fledge/data`` by default) has not been removed, in case an administrator might want to analyze or reuse the data.

|br|
