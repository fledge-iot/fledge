.. Getting Started describes how to build and install Fledge

.. |br| raw:: html

   <br />

.. Links in new tabs
.. |Fledge Repo| raw:: html

   <a href="https://github.com/fledge-iot/fledge" target="_blank">https://github.com/fledge-iot/fledge</a>

.. |GCC Bug| raw:: html

   <a href="https://gcc.gnu.org/bugzilla/show_bug.cgi?id=66425" target="_blank">here</a>

.. =============================================


****************
Building Fledge
****************

Let's get started! In this chapter we will see where to find and how to build, install and run Fledge for the first time.


Fledge Platforms
=================

Due to the use of standard libraries, Fledge can run on a large number of platforms and operating environments, but its primary target is Linux distributions. |br| Our testing environment includes Ubuntu 18.04 LTS, Ubuntu 20.04 LTS and Raspbian, but we have installed and tested Fledge on other Linux distributions. In addition to the native support, Fledge can also run on Virtual Machines, Docker and LXC containers.


Requirements
------------

Fledge requires a number of software packages and libraries to be installed in order to be built, the process of installing these has been streamlined and automated for all the currently supported platforms. A single script, *requirements.sh* can be run and this will install all of the packages needed to to build and run Fledge.

Building Fledge
================

In this section we will describe how to build Fledge on any of the supported platforms. If you are not familiar with Linux and you do not want to build Fledge from the source code, you can download a ready-made package (the list of packages is `available here <../92_downloads.html>`_).

Obtaining the Source Code
-------------------------

Fledge is available on GitHub. The link to the repository is |Fledge Repo|. In order to clone the code in the repository, type:

.. code-block:: console

  $ git clone https://github.com/fledge-iot/fledge.git
  Cloning into 'fledge'...
  remote: Enumerating objects: 83394, done.
  remote: Counting objects: 100% (2093/2093), done.
  remote: Compressing objects: 100% (903/903), done.
  remote: Total 83394 (delta 1349), reused 1840 (delta 1161), pack-reused 81301
  Receiving objects: 100% (83394/83394), 34.85 MiB | 7.38 MiB/s, done.
  Resolving deltas: 100% (55599/55599), done.
  $

The code should now be loaded on your machine in a directory called fledge. The name of the repository directory is *fledge*:

.. code-block:: console

  $ ls -l fledge
  total 228
  drwxrwxr-x  7 fledge fledge   4096 Aug 26 11:20 C
  -rw-rw-r--  1 fledge fledge   1659 Aug 26 11:20 CMakeLists.txt
  drwxrwxr-x  2 fledge fledge   4096 Aug 26 11:20 contrib
  -rw-rw-r--  1 fledge fledge   4786 Aug 26 11:20 CONTRIBUTING.md
  drwxrwxr-x  4 fledge fledge   4096 Aug 26 11:20 data
  drwxrwxr-x  2 fledge fledge   4096 Aug 26 11:20 dco-signoffs
  drwxrwxr-x 10 fledge fledge   4096 Aug 26 11:20 docs
  -rw-rw-r--  1 fledge fledge 108680 Aug 26 11:20 doxy.config
  drwxrwxr-x  3 fledge fledge   4096 Aug 26 11:20 examples
  drwxrwxr-x  4 fledge fledge   4096 Aug 26 11:20 extras
  -rw-rw-r--  1 fledge fledge  11346 Aug 26 11:20 LICENSE
  -rw-rw-r--  1 fledge fledge  24216 Aug 26 11:20 Makefile
  -rwxrwxr-x  1 fledge fledge    310 Aug 26 11:20 mkversion
  drwxrwxr-x  4 fledge fledge   4096 Aug 26 11:20 python
  -rw-rw-r--  1 fledge fledge   9292 Aug 26 11:20 README.rst
  -rwxrwxr-x  1 fledge fledge   8177 Aug 26 11:20 requirements.sh
  drwxrwxr-x  8 fledge fledge   4096 Aug 26 11:20 scripts
  drwxrwxr-x  4 fledge fledge   4096 Aug 26 11:20 tests
  drwxrwxr-x  3 fledge fledge   4096 Aug 26 11:20 tests-manual
  -rwxrwxr-x  1 fledge fledge     38 Aug 26 11:20 VERSION
  $

Selecting the Correct Version
-----------------------------

The git repository created on your local machine, creates several branches. More specifically:

- The **main** branch is the latest, stable version. You should use this branch if you are interested in using Fledge with the last release features and fixes.
- The **develop** branch is the current working branch used by our developers. The branch contains the latest version and features, but it may be unstable and there may be issues in the code. You may consider to use this branch if you are curious to see one of the latest features we are working on, but you should not use this branch in production.
- The branches with versions **majorID.minorID** or **majorID.minorID.patchID**, such as *1.0* or *1.4.2*, contain the code of that specific version. You may use one of these branches if you need to check the code used in those versions.
- The branches with name **FOGL-XXXX**, where 'XXXX' is a sequence number, are working branches used by developers and contributors to add features, fix issues, modify and release code and documentation of Fledge. Those branches are free for you to see and learn from the work of the contributors.

Note that the default branch is *develop*.

Once you have cloned the Fledge project, in order to check the branches available, use the ``git branch`` command:

.. code-block:: console

  $ pwd
  /home/ubuntu
  $ cd fledge
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

You are now ready to build your first Fledge project. 

  - Move to the *fledge* project directory

  - Load the requirements needed to build Fledge by typing

    .. code-block:: console

      $ sudo ./requirements.sh
      [sudo] password for john:
      Platform is Ubuntu, Version: 18.04
      apt 1.6.14 (amd64)
      Reading package lists...
      Building dependency tree...
      ...

  - Type the ``make`` command and let the magic happen.

    .. code-block:: console

      $ make
      Building Fledge version X.X., DB schema X
      scripts/certificates "fledge" "365"
      Creating a self signed SSL certificate ...
      Certificates created successfully, and placed in data/etc/certs
      scripts/auth_certificates ca "ca" "365"
      ...
      Successfully installed aiohttp-3.8.1 aiohttp-cors-0.7.0 aiosignal-1.2.0 async-timeout-4.0.2 asynctest-0.13.0 attrs-22.1.0 cchardet-2.1.4 certifi-2022.6.15 charset-normalizer-2.1.1 frozenlist-1.2.0 idna-3.3 idna-ssl-1.1.0 ifaddr-0.2.0 multidict-5.2.0 pyjq-2.3.1 pyjwt-1.6.4 requests-2.27.1 requests-toolbelt-0.9.1 six-1.16.0 typing-extensions-4.1.1 urllib3-1.26.12 yarl-1.7.2 zeroconf-0.27.0
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
  /home/ubuntu/fledge
  $ export FLEDGE_ROOT=/home/ubuntu/fledge
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
  Fledge vX.X.X running.
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

PostgreSQL 13 is the version available for Ubuntu 18.04 when we have published this page. Other versions of PostgreSQL, such as 9.6 to newer version work just fine. |br| |br| When you install the Ubuntu package, PostreSQL is set for a *peer authentication*, i.e. the database user must match with the Linux user. Other packages may differ. You may quickly check the authentication mode set in the *pg_hba.conf* file. The file is in the same directory of the *postgresql.conf* file you may see as output from the *ps* command shown above, in our case */etc/postgresql/9.5/main*:

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

