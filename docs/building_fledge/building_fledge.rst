.. Getting Started describes how to build and install Fledge

.. |br| raw:: html

   <br />

.. Images
.. |fledge_all_round| image:: ../images/fledge_all_round_solution.jpg

.. Links
.. _here: #id1
.. _this section: #appendix-building-fledge-on-centos

.. Links in new tabs
.. |Fledge Repo| raw:: html

   <a href="https://github.com/fledge-iot/Fledge" target="_blank">https://github.com/fledge-iot/Fledge</a>

.. |GCC Bug| raw:: html

   <a href="https://gcc.gnu.org/bugzilla/show_bug.cgi?id=66425" target="_blank">here</a>

.. |snappy| raw:: html

   <a href="https://snapcraft.io" target="_blank">Snappy</a>

.. =============================================


****************
Building Fledge
****************

Let's get started! In this chapter we will see where to find and how to build, install and run Fledge for the first time.


Fledge Platforms
=================

Due to the use of standard libraries, Fledge can run on a large number of platforms and operating environments, but its primary target is Linux distributions. |br| Our testing environment includes Ubuntu LTS 18.04 and Raspbian, but we have installed and tested Fledge on other Linux distributions. In addition to the native support, Fledge can also run on Virtual Machines, Docker and LXC containers.


General Requirements
--------------------

This version of Fledge requires the following software to be installed in the same environment:

- **Avahi 0.6.32+**
- **Python 3.6.9+**
- **PostgreSQL 9.5+**
- **SQLite 3.11+**

If you intend to download and build Fledge from source (as explained in this page), you also need *git*. |br| In this version SQLite is default engine, but we have left libraries to easily switch to PostgreSQL, in case you need it. The PostgreSQL plugin will be moved to a different repository in future versions. Other requirements largely depend on the plugins that run in Fledge.

You may also want to install some utilities to make your life easier when you use or test Fledge:

- **curl**: it is used to interact with the REST API
- **jq**: the JSON processor, it helps in formatting the output of the REST API calls


Building Fledge
================

In this section we will describe how to build Fledge on Ubuntu 18.04 LTS (Server or Desktop). Other Linux distributions, Debian or Red-Hat based, or even other versions of Ubuntu may differ. If you are not familiar with Linux and you do not want to build Fledge from the source code, you can download a ready-made Debian package (the list of packages is `available here <../92_downloads.html>`_).


Build Pre-Requisites
--------------------

Fledge is currently based on C/C++ and Python code. The packages needed to build and run Fledge are:

- autoconf
- automake
- avahi-daemon
- build-essential
- ca-certificates
- cmake
- cpulimit
- curl
- g++
- git
- krb5-user
- libboost-dev
- libboost-system-dev
- libboost-thread-dev
- libcurl4-openssl-dev
- libssl-dev
- libpq-dev
- libsqlite3-dev
- libtool
- libz-dev
- make
- pkg-config
- postgresql
- python3-dev
- python3-pip
- python3-setuptools
- sqlite3
- uuid-dev

.. code-block:: console

  $ sudo apt-get update
  Get:1 http://security.ubuntu.com/ubuntu xenial-security InRelease [102 kB]
  ...
  All packages are up-to-date.
  $
  $ sudo apt-get install avahi-daemon ca-certificates curl git cmake g++ make build-essential autoconf automake
  Reading package lists... Done
  Building dependency tree
  ...
  $
  $ sudo apt-get install sqlite3 libsqlite3-dev
  Reading package lists... Done
  Building dependency tree
  ...
  $
  $ sudo apt-get install libtool libboost-dev libboost-system-dev libboost-thread-dev libssl-dev libpq-dev uuid-dev libz-dev
  Reading package lists... Done
  Building dependency tree
  ...
  $
  $ sudo apt-get install python3-dev python3-pip python3-setuptools
  Reading package lists... Done
  Building dependency tree
  ...
  $
  $ sudo apt-get install postgresql
  Reading package lists... Done
  Building dependency tree
  $
  ...
  $
  $ sudo apt-get install pkg-config cpulimit
  Reading package lists... Done
  Building dependency tree
  $
  ...
  $
  $ sudo DEBIAN_FRONTEND=noninteractive apt-get install -yq krb5-user
  Reading package lists... Done
  Building dependency tree
  $
  ...
  $
  $ sudo DEBIAN_FRONTEND=noninteractive apt-get install -yq libcurl4-openssl-dev
  Reading package lists... Done
  Building dependency tree
  $


Obtaining the Source Code
-------------------------

Fledge is available on GitHub. The link to the repository is |Fledge Repo|. In order to clone the code in the repository, type:

.. code-block:: console

  $ git clone https://github.com/fledge-iot/Fledge.git
  Cloning into 'Fledge'...
  remote: Counting objects: 15639, done.
  remote: Compressing objects: 100% (88/88), done.
  remote: Total 15639 (delta 32), reused 58 (delta 14), pack-reused 15531
  Receiving objects: 100% (15639/15639), 9.71 MiB | 2.11 MiB/s, done.
  Resolving deltas: 100% (10486/10486), done.
  Checking connectivity... done.
  $

The code should be now in your home directory. The name of the repository directory is *Fledge*:

.. code-block:: console

  $ ls -l Fledge
  total 128
  drwxr-xr-x   7 ubuntu ubuntu    224 Jan  3 20:08 C
  -rw-r--r--   1 ubuntu ubuntu   1480 May  7 00:29 CMakeLists.txt
  -rw-r--r--   1 ubuntu ubuntu  11346 Jan  3 20:08 LICENSE
  -rw-r--r--   1 ubuntu ubuntu  20660 Mar 13 00:25 Makefile
  -rw-r--r--   1 ubuntu ubuntu   9173 May  7 00:29 README.rst
  -rwxr-xr-x   1 ubuntu ubuntu     38 May  9 19:50 VERSION
  drwxr-xr-x   3 ubuntu ubuntu     96 Jan  3 20:08 contrib
  drwxr-xr-x   4 ubuntu ubuntu    128 Jan  3 20:08 data
  drwxr-xr-x  15 ubuntu ubuntu    480 Jan  3 20:08 dco-signoffs
  drwxr-xr-x  24 ubuntu ubuntu    768 May 11 00:44 docs
  drwxr-xr-x   3 ubuntu ubuntu     96 Jan  3 20:08 examples
  drwxr-xr-x   4 ubuntu ubuntu    128 Jan  3 20:08 extras
  drwxr-xr-x  14 ubuntu ubuntu    448 Jan  3 20:08 python
  -rwxr-xr-x   1 ubuntu ubuntu   6804 Mar 13 00:25 requirements.sh
  drwxr-xr-x  13 ubuntu ubuntu    416 May  7 00:29 scripts
  drwxr-xr-x   7 ubuntu ubuntu    224 Mar 13 00:25 tests
  drwxr-xr-x   3 ubuntu ubuntu     96 Jan  3 20:08 tests-manual
  $


Selecting the Correct Version
-----------------------------

The git repository created on your local machine, creates several branches. More specifically:

- The **main** branch is the latest, stable version. You should use this branch if you are interested in using Fledge with the last release features and fixes.
- The **develop** branch is the current working branch used by our developers. The branch contains the latest version and features, but it may be unstable and there may be issues in the code. You may consider to use this branch if you are curious to see one of the latest features we are working on, but you should not use this branch in production.
- The branches with versions **majorID.minorID**, such as *1.0* or *1.4*, contain the code of that specific version. You may use one of these branches if you need to check the code used in those versions.
- The branches with name **FOGL-XXXX**, where 'XXXX' is a sequence number, are working branches used by developers and contributors to add features, fix issues, modify and release code and documentation of Fledge. Those branches are free for you to see and learn from the work of the contributors.

Note that the default branch is *develop*.

Once you have cloned the Fledge project, in order to check the branches available, use the ``git branch`` command:

.. code-block:: console

  $ pwd
  /home/ubuntu
  $ cd Fledge
  $ git branch --all
  * develop
  remotes/origin/1.0
  ...
  remotes/origin/FOGL-822
  remotes/origin/FOGL-823
  remotes/origin/HEAD -> origin/develop
  ...
  remotes/origin/develop
  remotes/origin/main
  $

Assuming you want to use the latest released, stable version, use the ``git checkout`` command to select the *master* branch:

.. code-block:: console

  $ git checkout main
  Branch main set up to track remote branch main from origin.
  Switched to a new branch 'main'
  $

You can always use the ``git status`` command to check the branch you have checked out.


Building Fledge
----------------

You are now ready to build your first Fledge project. If you want to install Fledge on CentOS, Fedora or Red Hat, we recommend you to read this section first and then look at `this section`_. |br| |br|
Move to the *Fledge* project directory, type the ``make`` command and let the magic happen.

.. code-block:: console

  $ cd Fledge
  $ make
  mkdir -p cmake_build
  cd cmake_build ; cmake /home/ubuntu/Fledge/
  -- The C compiler identification is GNU 5.4.0
  -- The CXX compiler identification is GNU 5.4.0
  ...
  pip3 install -Ir python/requirements.txt --user --no-cache-dir
  ...
  Installing collected packages: multidict, idna, yarl, async-timeout, chardet, aiohttp, typing, aiohttp-cors, cchardet, pyjwt, six, pyjq
  Successfully installed aiohttp-2.3.8 aiohttp-cors-0.5.3 async-timeout-3.0.0 cchardet-2.1.1 chardet-3.0.4 idna-2.6 multidict-4.3.1 pyjq-2.1.0 pyjwt-1.6.0 six-1.11.0 typing-3.6.4 yarl-1.2.6
  $


Depending on the version of Ubuntu or other Linux distribution you are using, you may have found some issues. For example, there is a bug in the GCC compiler that raises a warning under specific circumstances. The output of the build will be something like:

.. code-block:: console

  /home/ubuntu/Fledge/C/services/storage/storage.cpp:97:14: warning: ignoring return value of ‘int dup(int)’, declared with attribute warn_unused_result [-Wunused-result]
    (void)dup(0);     // stdout GCC bug 66425 produces warning
                ^
  /home/ubuntu/Fledge/C/services/storage/storage.cpp:98:14: warning: ignoring return value of ‘int dup(int)’, declared with attribute warn_unused_result [-Wunused-result]
    (void)dup(0);     // stderr GCC bug 66425 produces warning
                ^

The bug is documented |GCC Bug|. For our project, you should ignore it.


The other issue is related to the version of pip (more specifically pip3), the Python package manager. If you see this warning in the middle of the build output:

.. code-block:: console

  /usr/lib/python3.6/distutils/dist.py:261: UserWarning: Unknown distribution option: 'python_requires'
    warnings.warn(msg)

...and this output at the end of the build process:

.. code-block:: console

  You are using pip version 8.1.1, however version 9.0.1 is available.
  You should consider upgrading via the 'pip install --upgrade pip' command.

In this case, what you need to do is to upgrade the pip software for Python3:

.. code-block:: console

  $ sudo pip3 install --upgrade pip
  Collecting pip
    Downloading pip-9.0.1-py2.py3-none-any.whl (1.3MB)
      100% |████████████████████████████████| 1.3MB 1.1MB/s
  Installing collected packages: pip
  Successfully installed pip-9.0.1
  $

At this point, run the ``make`` command again and the Python warning should disappear.


Testing Fledge from the Build Environment
------------------------------------------

If you are eager to test Fledge straight away, you can do so! All you need to do is to set the *FLEDGE_ROOT* environment variable and you are good to go. Stay in the Fledge project directory, set the environment variable with the path to the Fledge directory and start fledge with the ``fledge start`` command:

.. code-block:: console

  $ pwd
  /home/ubuntu/Fledge
  $ export FLEDGE_ROOT=/home/ubuntu/Fledge
  $ ./scripts/fledge start
  Starting Fledge vX.X.....
  Fledge started.
  $


You can check the status of Fledge with the ``fledge status`` command. For few seconds you may see service starting, then it will show the status of the Fledge services and tasks:

.. code-block:: console

  $ ./scripts/fledge status
  Fledge starting.
  $
  $ scripts/fledge status
  Fledge v1.8.0 running.
  Fledge Uptime:  9065 seconds.
  Fledge records: 86299 read, 86851 sent, 0 purged.
  Fledge does not require authentication.
  === Fledge services:
  fledge.services.core
  fledge.services.storage --address=0.0.0.0 --port=42583
  fledge.services.south --port=42583 --address=127.0.0.1 --name=Sine
  fledge.services.notification --port=42583 --address=127.0.0.1 --name=Fledge Notifications
  === Fledge tasks:
  fledge.tasks.purge --port=42583 --address=127.0.0.1 --name=purge
  tasks/sending_process --port=42583 --address=127.0.0.1 --name=PI Server
  $

If you are curious to see a proper output from Fledge, you can query the Core microservice using the REST API:

.. code-block:: console

  $ curl -s http://localhost:8081/fledge/ping ; echo
  {"uptime": 10480, "dataRead": 0, "dataSent": 0, "dataPurged": 0, "authenticationOptional": true, "serviceName": "Fledge", "hostName": "fledge", "ipAddresses": ["x.x.x.x", "x:x:x:x:x:x:x:x"], "health": "green", "safeMode": false}
  $
  $ curl -s http://localhost:8081/fledge/statistics ; echo
  [{"key": "BUFFERED", "description": "Readings currently in the Fledge buffer", "value": 0}, {"key": "DISCARDED", "description": "Readings discarded by the South Service before being  placed in the buffer. This may be due to an error in the readings themselves.", "value": 0}, {"key": "PURGED", "description": "Readings removed from the buffer by the purge process", "value": 0}, {"key": "READINGS", "description": "Readings received by Fledge", "value": 0}, {"key": "UNSENT", "description": "Readings filtered out in the send process", "value": 0}, {"key": "UNSNPURGED", "description": "Readings that were purged from the buffer before being sent", "value": 0}]
  $

Congratulations! You have installed and tested Fledge! If you want to go extra mile (and make the output of the REST API more readable, download the *jq* JSON processor and pipe the output of the *curl* command to it:

.. code-block:: console

  $ sudo apt install jq
  ...
  $
  $ curl -s http://localhost:8081/fledge/statistics | jq
  [
    {
      "key": "BUFFERED",
      "description": "Readings currently in the Fledge buffer",
      "value": 0
    },
    {
      "key": "DISCARDED",
      "description": "Readings discarded by the South Service before being  placed in the buffer. This may be due to an error in the readings themselves.",
      "value": 0
    },
    {
      "key": "PURGED",
      "description": "Readings removed from the buffer by the purge process",
      "value": 0
    },
    {
      "key": "READINGS",
      "description": "Readings received by Fledge",
      "value": 0
    },
    {
      "key": "UNSENT",
      "description": "Readings filtered out in the send process",
      "value": 0
    },
    {
      "key": "UNSNPURGED",
      "description": "Readings that were purged from the buffer before being sent",
      "value": 0
    }
  ]
  $


Now I Want to Stop Fledge!
---------------------------

Easy, you have learnt ``fledge start`` and ``fledge status``, simply type ``fledge stop``:


.. code-block:: console

  $ scripts/fledge stop
  Stopping Fledge.........
  Fledge stopped.
  $

|br| |br|
As a next step, let's install Fledge!


Appendix: Setting the PostgreSQL Database
=========================================

If you intend to use the PostgreSQL database as storage engine, make sure that PostgreSQL is installed and running correctly:

.. code-block:: console

  $ sudo systemctl status postgresql
  ● postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
     Active: active (exited) since Fri 2017-12-08 15:56:07 GMT; 15min ago
   Main PID: 14572 (code=exited, status=0/SUCCESS)
     CGroup: /system.slice/postgresql.service

  Dec 08 15:56:07 ubuntu systemd[1]: Starting PostgreSQL RDBMS...
  Dec 08 15:56:07 ubuntu systemd[1]: Started PostgreSQL RDBMS.
  Dec 08 15:56:11 ubuntu systemd[1]: Started PostgreSQL RDBMS.
  $
  $ ps -ef | grep postgres
  postgres 14806     1  0 15:56 ?        00:00:00 /usr/lib/postgresql/9.5/bin/postgres -D /var/lib/postgresql/9.5/main -c config_file=/etc/postgresql/9.5/main/postgresql.conf
  postgres 14808 14806  0 15:56 ?        00:00:00 postgres: checkpointer process
  postgres 14809 14806  0 15:56 ?        00:00:00 postgres: writer process
  postgres 14810 14806  0 15:56 ?        00:00:00 postgres: wal writer process
  postgres 14811 14806  0 15:56 ?        00:00:00 postgres: autovacuum launcher process
  postgres 14812 14806  0 15:56 ?        00:00:00 postgres: stats collector process
  ubuntu   15198  1225  0 17:22 pts/0    00:00:00 grep --color=auto postgres
  $

PostgreSQL 9.5 is the version available for Ubuntu 18.04 when we have published this page. Other versions of PostgreSQL, such as 9.6 or 10.1, work just fine. |br| |br| When you install the Ubuntu package, PostreSQL is set for a *peer authentication*, i.e. the database user must match with the Linux user. Other packages may differ. You may quickly check the authentication mode set in the *pg_hba.conf* file. The file is in the same directory of the *postgresql.conf* file you may see as output from the *ps* command shown above, in our case */etc/postgresql/9.5/main*:

.. code-block:: console

  $ sudo grep '^local' /etc/postgresql/9.5/main/pg_hba.conf
  local   all             postgres                                peer
  local   all             all                                     peer
  $

The installation procedure also creates a Linux *postgres* user. In order to check if everything is set correctly, execute the *psql* utility as sudo user:

.. code-block:: console

  $ sudo -u postgres psql -l
                                    List of databases
     Name    |  Owner   | Encoding |   Collate   |    Ctype    |   Access privileges
  -----------+----------+----------+-------------+-------------+-----------------------
   postgres  | postgres | UTF8     | en_GB.UTF-8 | en_GB.UTF-8 |
   template0 | postgres | UTF8     | en_GB.UTF-8 | en_GB.UTF-8 | =c/postgres          +
             |          |          |             |             | postgres=CTc/postgres
   template1 | postgres | UTF8     | en_GB.UTF-8 | en_GB.UTF-8 | =c/postgres          +
             |          |          |             |             | postgres=CTc/postgres
  (3 rows)
  $

Encoding and collations may differ, depending on the choices made when you installed your operating system. |br| Before you proceed, you must create a PostgreSQL user that matches your Linux user. Supposing that your user is *<fledge_user>*, type:

.. code-block:: console

  $ sudo -u postgres createuser -d <fledge_user>

The *-d* argument is important because the user will need to create the Fledge database.

A more generic command is:
  $ sudo -u postgres createuser -d $(whoami)

Finally, you should now be able to see the list of the available databases from your current user:

.. code-block:: console

  $ psql -l
                                    List of databases
     Name    |  Owner   | Encoding |   Collate   |    Ctype    |   Access privileges
  -----------+----------+----------+-------------+-------------+-----------------------
   postgres  | postgres | UTF8     | en_GB.UTF-8 | en_GB.UTF-8 |
   template0 | postgres | UTF8     | en_GB.UTF-8 | en_GB.UTF-8 | =c/postgres          +
             |          |          |             |             | postgres=CTc/postgres
   template1 | postgres | UTF8     | en_GB.UTF-8 | en_GB.UTF-8 | =c/postgres          +
             |          |          |             |             | postgres=CTc/postgres
  (3 rows)
  $

|br|


Appendix: Building Fledge on CentOS
====================================

In this section we present how to prepare a CentOS machine to build and install Fledge. A similar approach can be adopted to build the platform on RedHat and Fedora distributions. Here we refer to CentOS version 17.4.1708, requirements for other versions or distributions might differ.


Pre-Requisites
--------------

Pre-requisites on CentOS are similar to the ones on other distributions, but the name of the packages may differ from Debian-based distros. Starting from a minimal installation, this is the list of packages you need to add:

- libtool
- cmake
- boost-devel
- libuuid-devel
- gmp-devel
- mpfr-devel
- libmpc-devel
- sqlite3
- bzip2
- jq

This is the complete list of the commands to execute and the installed packages in CentoOS 17.4.1708.

.. code-block:: console

  sudo yum install libtool
  sudo yum install cmake
  sudo yum install boost-devel
  sudo yum install libuuid-devel
  sudo yum install gmp-devel
  sudo yum install mpfr-devel
  sudo yum install libmpc-devel
  sudo yum install bzip2
  sudo yum install jq
  sudo yum install libsqlite3x-devel


Building and Installing C++ 5.4
-------------------------------

Fledge, requires C++ 5.4, CentOS 7 provides version 4.8. These are the commands to build and install the new GCC environment:

.. code-block:: console

  sudo yum install gcc-c++
  curl https://ftp.gnu.org/gnu/gcc/gcc-5.4.0/gcc-5.4.0.tar.bz2 -O
  bzip2 -dk gcc-5.4.0.tar.bz
  tar xvf gcc-5.4.0.tar
  mkdir gcc-5.4.0-build
  cd gcc-5.4.0-build
  ../gcc-5.4.0/configure --enable-languages=c,c++ --disable-multilib
  make -j$(nproc)
  sudo make install

At the end of the procedure, the system will have two versions of GCC installed:

- GCC 4.8, installed in /usr/bin and /usr/lib64
- GCC 5.4, installed in /usr/local/bin and /usr/local/lib64

In order to use the latest version for Fledge, add the following lines at the end of your ``$HOME/.bash_profile`` script:

.. code-block:: console

  export CC=/usr/local/bin/gcc
  export CXX=/usr/local/bin/g++
  export LD_LIBRARY_PATH=/usr/local/lib64


Installing PostgreSQL 9.6
-------------------------

CentOS provides PostgreSQL 9.2. Fledge has been tested with PostgreSQL 9.5, 9.6 and 10.X.
Following https://www.postgresql.org/download/ instructions, the commands to install the new version of PostgreSQL are:

.. code-block:: console

  sudo yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
  sudo yum install postgresql96-server
  sudo yum install postgresql96-devel
  sudo yum install rh-postgresql96
  sudo yum install rh-postgresql96-postgresql-devel
  sudo /usr/pgsql-9.6/bin/postgresql96-setup initdb
  sudo systemctl enable postgresql-9.6
  sudo systemctl start postgresql-9.6

At this point, Postgres has been configured to start at boot and it should be up and running. You can always check the status of the database server with ``systemctl status postgresql-9.6``:

.. code-block:: console

  $ sudo systemctl status postgresql-9.6
  [sudo] password for fledge:
  ● postgresql-9.6.service - PostgreSQL 9.6 database server
     Loaded: loaded (/usr/lib/systemd/system/postgresql-9.6.service; enabled; vendor preset: disabled)
     Active: active (running) since Sat 2018-03-17 06:22:52 GMT; 8min ago
       Docs: https://www.postgresql.org/docs/9.6/static/
    Process: 1036 ExecStartPre=/usr/pgsql-9.6/bin/postgresql96-check-db-dir ${PGDATA} (code=exited, status=0/SUCCESS)
   Main PID: 1049 (postmaster)
     CGroup: /system.slice/postgresql-9.6.service
             ├─1049 /usr/pgsql-9.6/bin/postmaster -D /var/lib/pgsql/9.6/data/
             ├─1077 postgres: logger process
             ├─1087 postgres: checkpointer process
             ├─1088 postgres: writer process
             ├─1089 postgres: wal writer process
             ├─1090 postgres: autovacuum launcher process
             └─1091 postgres: stats collector process

  Mar 17 06:22:52 vbox-centos-test systemd[1]: Starting PostgreSQL 9.6 database server...
  Mar 17 06:22:52 vbox-centos-test postmaster[1049]: < 2018-03-17 06:22:52.910 GMT > LOG:  redirecting log output to logging collector process
  Mar 17 06:22:52 vbox-centos-test postmaster[1049]: < 2018-03-17 06:22:52.910 GMT > HINT:  Future log output will appear in directory "pg_log".
  Mar 17 06:22:52 vbox-centos-test systemd[1]: Started PostgreSQL 9.6 database server.
  $

Next, add the Fledge user to PostgreSQL with the command ``sudo -u postgres createuser -d <user>``, where *<user>* is your Fledge user.

Finally, add ``/usr/pgsql-9.6/bin`` to your PATH environment variable in ``$HOME/.bash_profile``. the new PATH setting in the file should look something like this:

.. code-block:: console

  PATH=$PATH:$HOME/.local/bin:$HOME/bin:/usr/pgsql-9.6/bin


Installing SQLite3
------------------

Fledge requires SQLite version 3.11 or later, CentOS provides an old version of SQLite. We must download SQLite, compile it and install it. The steps are:

- Download the source code of SQLite with *wget*. If you do not have *wget* installed, install it with ``sudo yum install wget``: |br| ``wget http://www.sqlite.org/2018/sqlite-autoconf-3230100.tar.gz``
- Extract the SQLite tarball: |br| ``tar xzvf sqlite-autoconf-3230100.tar.gz``
- Move into the SQLite directory and execute the *configure-make-make install* commands: |br| ``cd sqlite-autoconf-3230100`` |br| ``./configure`` |br| ``make`` |br| ``sudo make install``


Changing to the PostgreSQL Engine
---------------------------------

The CentOS version of Fledge is optimized to work with PostgreSQL as storage engine. In order to achieve that, change the file *configuration.cpp* in the *C/services/storage* directory: line #20, word *sqlite* must be replaced with *postgres*:

``" { \"plugin\" : { \"value\" : \"postgres\", \"description\" : \"The stora    ge plugin to load\"},"``


Building Fledge
----------------

We are finally ready to install Fledge, but we need to apply some little changes to the code and the make files. These changes will be removed in the future, but for the moment they are necessary to complete the procedure.

First, clone the Github repository with the usual command: |br| ``git clone https://github.com/fledge-iot/Fledge.git`` |br| The project should have been added to your machine under the *Fledge* directory.

We need to apply these changes to *C/plugins/storage/postgres/CMakeLists.txt*:

- Replace |br| ``include_directories(../../../thirdparty/rapidjson/include /usr/include/postgresql)`` |br| with: |br| ``include_directories(../../../thirdparty/rapidjson/include /usr/pgsql-9.6/include)`` |br| ``link_directories(/usr/pgsql-9.6/lib)`` |br|

You are now ready to execute the ``make`` command, as described here_.


Further Notes
-------------

Here are some extra notes for the CentOS users.

**Commented code** |br| The code commented in the previous paragraph is experimental and used for auto-discovery. It has been used for tests with South Microservices running on smart sensors, separated from the Core and Storage Microservices. This means that auto-discovery, i.e. the ability for a South Microservice to automatically identify the other services of Fledge distributed over the network, is currently not available on CentOS.


**fledge start** |br| When Fledge starts on CentOS, it returns this message:

.. code-block:: console

  Starting Fledge v1.8.0.Fledge cannot start.
  Check /home/fledge/Fledge/data/core.err for more information.

Check the *core.err* file, but if it is empty and *fledge status* shows Fledge running, it means that the services are up and running.

.. code-block:: console

  $ fledge start
  Starting Fledge v1.8.0.Fledge cannot start.
  Check /home/fledge/Fledge/data/core.err for more information.
  $
  $ fledge status
  Fledge v1.8.0 running.
  Fledge uptime:  6 seconds.
  Fledge Records: 0 read, 0 sent, 0 purged.
  Fledge does not require authentication.
  === Fledge services:
  fledge.services.core
  === Fledge tasks:
  $
  $ cat data/core.err
  $
  $ ps -ef | grep fledge
  ...
  fledge   6174     1  1 08:03 pts/0    00:00:00 python3 -m fledge.services.core
  fledge   6179     1  0 08:03 ?        00:00:00 /home/fledge/Fledge/services/storage --address=0.0.0.0 --port=34037
  fledge   6213  6212  0 08:04 pts/0    00:00:00 python3 -m fledge.tasks.statistics --port=34037 --address=127.0.0.1 --name=stats collector
  ...
  $

**fledge stop** |br| In CentOS, the command stops all the microservices with the exception of Core (with a ``ps -ef`` command you can easily check the process still running). You should execute a *stop* and a *kill* command to complete the shutdown on CentOS:

.. code-block:: console

  $ fledge status
  Fledge v1.8.0 running.
  Fledge uptime:  6 seconds.
  Fledge Records: 0 read, 0 sent, 0 purged.
  Fledge does not require authentication.
  === Fledge services:
  fledge.services.core
  === Fledge tasks:
  $ fledge stop
  Stopping Fledge.............
  Fledge stopped.
  $
  $ ps -ef | grep fledge
  ...
  fledge   5782     1  5 07:56 pts/0    00:00:11 python3 -m fledge.services.core
  ...
  $
  $ fledge kill
  Fledge killed.
  $ ps -ef | grep fledge
  ...
  $
