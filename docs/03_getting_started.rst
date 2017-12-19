.. Getting Started describes how to build and install FogLAMP

.. |br| raw:: html

   <br />

.. Images
.. |foglamp_all_round| image:: images/foglamp_all_round_solution.jpg

.. Links
.. _FogLAMP project on GitHub: https://github.com/foglamp/FogLAMP/issues

.. Links in new tabs
.. |FogLAMP Repo| raw:: html

   <a href="https://github.com/foglamp/FogLAMP" target="_blank">https://github.com/foglamp/FogLAMP</a>

.. |GCC Bug| raw:: html

   <a href="https://gcc.gnu.org/bugzilla/show_bug.cgi?id=66425" target="_blank">here</a>

.. =============================================


***************
Getting Started
***************

Let's get started! In this chapter we will see where to find and how to build, install and run FogLAMP for the first time.


FogLAMP Platforms
=================

Due to the use of standard libraries, FogLAMP can run on a large number of platforms and operating environments, but its primary target is Linux distributions. |br| Our testing environment includes Ubuntu LTS 16.04 and Ubuntu Core 16.04, but we have installed and tested FogLAMP on other Linux distributions such as CentOS and Raspbian. In addition to the native support, FogLAMP can also run on Virtual Machines, Docker and LXC containers. |br| FogLAMP development Ubuntu 16.04 and later additions.


General Requirements
--------------------

This version of FogLAMP requires the following software to be installed in the same environment:
- Python 3.5+
- PostgreSQL 9.5+

The requirements largely depend on the plugins that run in FogLAMP, but Python and PostgreSQL are essential for the Core and Storage microservices and tasks.


Building FogLAMP
================

In this section we will describe how to build FogLAMP on Ubuntu 16.04.3 LTS (Server or Desktop).  Other Linux distributions, Debian or Red-Hat based, or even other versions of Ubuntu may differ. If you are not familiar with Linux and you do not want to build FogLAMP from the source code, you can download a snap package from Snappy.

Build Pre-Requisites
--------------------

FogLAMP is currently based on C/C++ and Python code. The packages needed to build and run FogLAMP are:

- cmake, g++, make
- liboost-dev, liboost-system-dev, liboost-thread-dev, libpq-dev
- python3-pip
- postgresql

.. code-block:: console

  $ sudo apt update
  Get:1 http://security.ubuntu.com/ubuntu xenial-security InRelease [102 kB]
  ...
  All packages are up-to-date.
  $
  $ sudo apt install cmake g++ make
  Reading package lists... Done
  Building dependency tree
  ...
  $
  $ sudo apt-get install libboost-dev libboost-system-dev libboost-thread-dev libpq-dev
  Reading package lists... Done
  Building dependency tree
  ...
  $
  $ sudo apt-get install python3-pip
  Reading package lists... Done
  Building dependency tree
  ...
  $
  $ sudo apt install postgresql
  Reading package lists... Done
  Building dependency tree
  $


Setting the PostgreSQL Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this version of FogLAMP the PostgreSQL database is the default storage engine, used by the Storage microservice. Make sure that PostgreSQL is installed and running correctly:

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

PostgreSQL 9.5 is the version available for Ubuntu 16.04 when we have published this page. Other versions of PostgreSQL, such as 9.6 or 10.1, work just fine. |br| |br| When you install the Ubuntu package, PostreSQL is set for a *peer authentication*, i.e. the database user must match with the Linux user. Other packages may differ. You may quickly check the authentication mode set in the *pg_hba.conf* file. The file is in the same directory of the *postgresql.conf* file you may see as output from the *ps* command shown above, in our case */etc/postgresql/9.5/main*:

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

Encoding and collations may differ, depending on the choices made when you installed your operating system. |br| Before you proceed, you must create a PostgreSQL user that matches your Linux user. Supposing that your user is *<foglamp_user>*, type:

.. code-block:: console

  $ sudo -u postgres createuser -d <foglamp_user>
 
The *-d* argument is important because the user will need to create the FogLAMP database.

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


Obtaining the Source Code
-------------------------

FogLAMP is available on GitHub. The link to the repository is |FogLAMP Repo|. In order to clone the code in the repository, type:

.. code-block:: console

  $ git clone https://github.com/foglamp/FogLAMP.git
  Cloning into 'FogLAMP'...
  remote: Counting objects: 15639, done.
  remote: Compressing objects: 100% (88/88), done.
  remote: Total 15639 (delta 32), reused 58 (delta 14), pack-reused 15531
  Receiving objects: 100% (15639/15639), 9.71 MiB | 2.11 MiB/s, done.
  Resolving deltas: 100% (10486/10486), done.
  Checking connectivity... done.
  $

The code should be now in your home directory. The name of the repository directory is *FogLAMP*:

.. code-block:: console

  $ ls -l FogLAMP
  total 84
  drwxrwxr-x 5 ubuntu ubuntu  4096 Dec  8 18:00 C
  -rw-rw-r-- 1 ubuntu ubuntu   180 Dec  8 18:00 CMakeLists.txt
  drwxrwxr-x 3 ubuntu ubuntu  4096 Dec  8 18:00 data
  drwxrwxr-x 3 ubuntu ubuntu  4096 Dec  8 18:00 docs
  dtrwxrwxr-x 3 ubuntu ubuntu  4096 Dec  8 18:00 examples
  drwxrwxr-x 3 ubuntu ubuntu  4096 Dec  8 18:00 extras
  -rw-rw-r-- 1 ubuntu ubuntu  5869 Dec  8 18:00 Jenkinsfile
  -rw-rw-r-- 1 ubuntu ubuntu 11342 Dec  8 18:00 LICENSE
  -rw-rw-r-- 1 ubuntu ubuntu 10654 Dec  8 18:00 Makefile
  -rw-rw-r-- 1 ubuntu ubuntu  5842 Dec  8 18:00 pr_tester.sh
  drwxrwxr-x 4 ubuntu ubuntu  4096 Dec  8 18:00 python
  -rw-rw-r-- 1 ubuntu ubuntu  5916 Dec  8 18:00 README.rst
  drwxrwxr-x 8 ubuntu ubuntu  4096 Dec  8 18:00 scripts
  drwxrwxr-x 3 ubuntu ubuntu  4096 Dec  8 18:00 tests
  $


Selecting the Correct Version
-----------------------------

The git repository created on your local machine, creates several branches. More specifically:

- The **master** branch is the latest, stable version. You should use this branch if you are interested in using FogLAMP with the latest features and fixes.
- The **develop** branch is the current working branch used by our developers. The branch contains the lastest version and features, but it may be unstable and there may be issues in the code. You may consider to use this branch if you are curious to see one of the latest features we are working on, but you should not use this branch in production.
- The branches with versions **majorID.minorID**, such as *1.0* or *1.4*, contain the code of that specific version. You may use one of these branches if you need to check the code used in those versions.
- The branches with name **FOGL-XXXX**, where 'XXXX' is a sequence number, are working branches used by developers and contributors to add features, fix issues, modify and release code and documentation of FogLAMP. Those branches are free for you to see and learn from the work of the contributors.
 
Note that the default branch is *develop*.

Once you have cloned the FogLAMP project, in order to check the branches available, use the ``git branch`` command:

.. code-block:: console

  $ pwd
  /home/ubuntu
  $ cd FogLAMP
  $ git branch --all
  * develop
  remotes/origin/1.0
  ...
  remotes/origin/FOGL-822
  remotes/origin/FOGL-823
  remotes/origin/HEAD -> origin/develop
  ...
  remotes/origin/develop
  remotes/origin/master
  $

Assuming you want to use the latest, stable version, use the ``git checkout`` command to select the *master* branch:

.. code-block:: console

  $ git checkout master
  Branch master set up to track remote branch master from origin.
  Switched to a new branch 'master'
  $

You can always use the ``git status`` command to check the branch you have checked out.


Building FogLAMP
----------------

You are now ready to build your first FogLAMP project. Move to the *FogLAMP* project directory, type the ``make`` comand and let the magic happen.

.. code-block:: console

  $ cd FogLAMP
  $ make
  mkdir -p cmake_build
  cd cmake_build ; cmake /home/ubuntu/FogLAMP/
  -- The C compiler identification is GNU 5.4.0
  -- The CXX compiler identification is GNU 5.4.0
  ...
  Successfully built aiocoap pexpect
  Installing collected packages: aiocoap, cbor2, six, pyparsing, packaging, async-timeout, multidict, yarl, chardet, aiohttp, typing, aiohttp-cors, cchardet, certifi, idna, urllib3, requests, ptyprocess, pexpect
  Successfully installed aiocoap aiohttp aiohttp-cors async-timeout cbor2 cchardet certifi chardet-2.3.0 idna multidict packaging pexpect ptyprocess pyparsing requests-2.9.1 six-1.10.0 typing urllib3-1.13.1 yarl
  $


Depending on the version of Ubuntu or other Linux distribution you are using, you may have found some issues. For example, there is a bug in the GCC compiler that raises a warning under specific circumstances. The output of the build will be something like: 

.. code-block:: console

  /home/ubuntu/FogLAMP/C/services/storage/storage.cpp:97:14: warning: ignoring return value of ‘int dup(int)’, declared with attribute warn_unused_result [-Wunused-result]
    (void)dup(0);     // stdout GCC bug 66425 produces warning
                ^
  /home/ubuntu/FogLAMP/C/services/storage/storage.cpp:98:14: warning: ignoring return value of ‘int dup(int)’, declared with attribute warn_unused_result [-Wunused-result]
    (void)dup(0);     // stderr GCC bug 66425 produces warning
                ^

The bug is documented |GCC Bug|. For our project, you should ignore it.


The other issue is related to the version of pip (more specifically pip3), the Python package manager. If you see this warning in the middle of the build output:

.. code-block:: console

  /usr/lib/python3.5/distutils/dist.py:261: UserWarning: Unknown distribution option: 'python_requires'
    warnings.warn(msg)

...and this output at the end of the build process:

.. code-block:: console

  You are using pip version 8.1.1, however version 9.0.1 is available.
  You should consider upgrading via the 'pip install --upgrade pip' command.

In this case, what you need to do is to upgrade the pip software for Python 3:

.. code-block:: console

  $ pip3 install --upgrade pip
  Collecting pip
    Downloading pip-9.0.1-py2.py3-none-any.whl (1.3MB)
      100% |████████████████████████████████| 1.3MB 1.1MB/s
  Installing collected packages: pip
  Successfully installed pip-9.0.1
  $

At this point, run the ``make`` command again and the Python warning should disappear.


Testing FogLAMP from the Build Environment
------------------------------------------

If you are eager to test FogLAMP straight away, you can do so! All you need to do is to set the *FOGLAMP_ROOT* environment variable and you are good to go. Stay in the FogLAMP project directory, set the environment variable with the path to the FogLAMP directory and start foglamp with the ``foglamp start`` command:

.. code-block:: console

  $ pwd
  /home/ubuntu/FogLAMP
  $ export FOGLAMP_ROOT=/home/ubuntu/FogLAMP
  $ scripts/foglamp start
  FogLAMP started.
  $


You can check the status of FogLAMP with the ``foglamp status`` command. For few seconds you may see service starting, then it will show the status of the FogLAMP services and tasks:

.. code-block:: console

  $ scripts/foglamp status
  FogLAMP starting.
  $
  $ scripts/foglamp status
  FogLAMP running.
  FogLAMP uptime:  175 seconds.
  === FogLAMP services:
  foglamp.services.core
  foglamp.services.south --port=40417 --address=127.0.0.1 --name=HTTP_SOUTH
  foglamp.services.south --port=40417 --address=127.0.0.1 --name=COAP
  foglamp.services.south --port=40417 --address=127.0.0.1 --name=CC2650POLL
  === FogLAMP tasks:
  foglamp.tasks.north.sending_process --stream_id 3 --debug_level 1 --port=40417 --address=127.0.0.1 --name=sending HTTP
  foglamp.tasks.north.sending_process --stream_id 1 --debug_level 1 --port=40417 --address=127.0.0.1 --name=sending process
  foglamp.tasks.north.sending_process --stream_id 2 --debug_level 1 --port=40417 --address=127.0.0.1 --name=statistics to pi
  $

If you are curious to see a proper out from from FogLAMP, you can query the Core microservice using the REST API:

.. code-block:: console

  $ curl -s http://localhost:8081/foglamp/ping ; echo
  {"uptime": 308.42881059646606}
  $
  $ curl -s http://localhost:8081/foglamp/statistics ; echo
  [{"key": "BUFFERED", "description": "The number of readings currently in the FogLAMP buffer", "value": 0}, {"key": "DISCARDED", "description": "The number of readings discarded at the input side by FogLAMP, i.e. discarded before being  placed in the buffer. This may be due to some error in the readings themselves.", "value": 0}, {"key": "PURGED", "description": "The number of readings removed from the buffer by the purge process", "value": 0}, {"key": "READINGS", "description": "The number of readings received by FogLAMP since startup", "value": 0}, {"key": "SENT_1", "description": "The number of readings sent to the historian", "value": 0}, {"key": "SENT_2", "description": "The number of statistics data sent to the historian", "value": 0}, {"key": "SENT_3", "description": "The number of readings data sent to the HTTP translator", "value": 0}, {"key": "UNSENT", "description": "The number of readings filtered out in the send process", "value": 0}, {"key": "UNSNPURGED", "description": "The number of readings that were purged from the buffer before being sent", "value": 0}]
  $

Congratulations! You have installed and tested FogLAMP! If you want to go extra mile (and make the output of the REST API more readible, download the *jq* JSON processor and pipe the output of the *curl* command to it:

.. code-block:: console

  $ sudo apt install jq
  ...
  $
  $ curl -s http://localhost:8081/foglamp/statistics | jq
  [
    {
      "key": "BUFFERED",
      "description": "The number of readings currently in the FogLAMP buffer",
      "value": 0
    },
    {
      "key": "DISCARDED",
      "description": "The number of readings discarded at the input side by FogLAMP, i.e. discarded before being  placed in the buffer. This may be due to some error in the readings themselves.",
      "value": 0
    },
    {
      "key": "PURGED",
      "description": "The number of readings removed from the buffer by the purge process",
      "value": 0
    },
    {
      "key": "READINGS",
      "description": "The number of readings received by FogLAMP since startup",
      "value": 0
    },
    {
      "key": "SENT_1",
      "description": "The number of readings sent to the historian",
      "value": 0
    },
    {
      "key": "SENT_2",
      "description": "The number of statistics data sent to the historian",
      "value": 0
    },
    {
      "key": "SENT_3",
      "description": "The number of readings data sent to the HTTP translator",
      "value": 0
    },
    {
      "key": "UNSENT",
      "description": "The number of readings filtered out in the send process",
      "value": 0
    },
    {
      "key": "UNSNPURGED",
      "description": "The number of readings that were purged from the buffer before being sent",
      "value": 0
    }
  ]
  $


Now I Want to Stop FogLAMP!
---------------------------

Easy, you have learnt ``foglamp start`` and ``foglamp status``, simply type ``foglamp stop``:


.. code-block:: console

  $ scripts/foglamp stop
  FogLAMP stopped.
  $

|br| |br| 
As a next step, let's install FogLAMP!

