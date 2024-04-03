.. Links
.. |Debian PostgreSQL| raw:: html

   <a href="../storage.html#ubuntu-install">For Debian Platform</a>

.. |RPM PostgreSQL| raw:: html

   <a href="../storage.html#red-hat-install">For Red Hat Platform</a>

.. |Configure Storage Plugin| raw:: html

   <a href="../storage.html#configuring-the-storage-plugin">Configure Storage Plugin from GUI</a>


Installing Fledge
==================

Fledge is extremely lightweight and can run on inexpensive edge devices, sensors and actuator boards.  For the purposes of this manual, we assume that all services are running on a Raspberry Pi running the Bullseye operating system. Be sure your system has plenty of storage available for data readings.

If your system does not have a supported version of the Raspberry Pi Operating System  pre-installed, you can find instructions on downloading and installing it at https://www.raspberrypi.org/downloads/operating-systems/.  After installing a supported operating system, ensure you have the latest updates by executing the following commands on your Fledge server::

  sudo apt-get update
  sudo apt-get upgrade
  sudo apt-get update

.. include:: instructions.txt

In general, Fledge installation will require the following packages:

- Fledge core
- Fledge user interface
- One or more Fledge South services
- One or more Fledge North service (OSI PI and OCS north services are included in Fledge core)

Using the package repository to install Fledge
###############################################

If you choose to use the Dianomic Systems package repository to install the packages you will need to follow the steps outlined below for the particular platform you are using.

Ubuntu or Debian
~~~~~~~~~~~~~~~~

On a Ubuntu or Debian system, including the Raspberry Pi, the package manager that is supported is *apt*. You will need to add the Dianomic Systems archive server into the configuration of apt on your system. The first thing that most be done is to add the key that is used to verify the package repository. To do this run the command

.. code-block:: console

   wget -q -O - http://archives.fledge-iot.org/KEY.gpg | sudo apt-key add -

Once complete you can add the repository itself into the apt configuration file /etc/apt/sources.list. The simplest way to do this is the use the *add-apt-repository* command. The exact command will vary between systems;

  - Raspberry Pi does not have an apt-add-repository command, the user must edit the apt sources file manually

    .. code-block:: console

       sudo vi /etc/apt/sources.list
       
    and add the line
    
    .. code-block:: console

       deb  http://archives.fledge-iot.org/latest/bullseye/armv7l/ /

    to the end of the file.

    .. note:: 
       Replace `bullseye` with  the name of the version of the Raspberry Operating System you have installed.

  - Users with an Intel or AMD system with Ubuntu 18.04 should run

    .. code-block:: console

       sudo add-apt-repository "deb http://archives.fledge-iot.org/latest/ubuntu1804/x86_64/ / "

  - Users with an Intel or AMD system with Ubuntu 20.04 should run

    .. code-block:: console

       sudo add-apt-repository "deb http://archives.fledge-iot.org/latest/ubuntu2004/x86_64/ / "

  - Users with an Arm system with Ubuntu 18.04, such as the Odroid board, should run

    .. code-block:: console

       sudo add-apt-repository "deb http://archives.fledge-iot.org/latest/ubuntu1804/aarch64/ / "

  - Users of the Mendel operating system on a Google Coral create the file /etc/apt/sources.list.d/fledge.list and insert the following content

    .. code-block:: console

       deb http://archives.fledge-iot.org/latest/mendel/aarch64/ /

Once the repository has been added you must inform the package manager to go and fetch a list of the packages it supports. To do this run the command

.. code-block:: console

   sudo apt -y update

You are now ready to install the Fledge packages. You do this by running the command

.. code-block:: console

   sudo apt -y install *package*

You may also install multiple packages in a single command. To install the base fledge package, the fledge user interface and the sinusoid south plugin run the command

.. code-block:: console

   sudo DEBIAN_FRONTEND=noninteractive apt -y install fledge fledge-gui fledge-south-sinusoid


Installing Fledge downloaded packages
######################################

Assuming you have downloaded the packages from the download link given above. Use SSH to login to the system that will host Fledge services. For each Fledge package that you choose to install, type the following command

.. code-block:: console

  sudo apt -y install <filename>

.. note::

  The downloaded files are named using the package name and the current version of the software. Therefore these names will change over time as new versions are released. At the time of writing the version of the Fledge package is 2.3.0, therefore the package filename is fledge_2.3.0_x86_64.deb on the X86 64bit platform. As a result the filenames shown in the following examples may differ from the names of the files you have downloaded.

The key packages to install are the Fledge core and the Fledge Graphical User Interface

.. code-block:: console

  sudo DEBIAN_FRONTEND=noninteractive apt -y install ./fledge_2.3.0_x86_64.deb
  sudo apt -y install ./fledge-gui_2.3.0.deb

You will need to install one of more South plugins to acquire data.  You can either do this now or when you are adding the data source. For example, to install the plugin for the Sense HAT sensor board, type

.. code-block:: console

  sudo apt -y install ./fledge-south-sensehat_2.3.0_armv7l.deb  

.. note::

  In this case we are showing the name for a package on the Raspberry Pi platform. The sensehat plugin is not supported on all platforms as it requires Raspberry Pi specific hardware connections.

You may also need to install one or more North plugins to transmit data.  Support for OSIsoft PI and OCS are included with the Fledge core package, so you don't need to install anything more if you are sending data to only these systems.

Firewall Configuration
######################

If you are installing packages within a fire walled environment you will need to open a number of locations for outgoing connections. This will vary depending upon how you install the packages.

If you are downloading or installing packages on the fire walled machine, that machine will need to access *archives.fledge-iot.org* to be able to pull the Fledge packages. This will use the standard HTTP port, port 80.

It is also recommended that you allow the machine to access the source of packages for your Linux installation. This allows you to keep the machine updated with important patches and also for the installation of any Linux packages that are required by Fledge or the plugins that you load.

As part of the installation of the Python components of Fledge a number of Python packages are installed using the *pip* utility. In order to allow this you need to open access to a set of locations that pip will pull packages from. The set of locations required is

  - python.org

  - pypi.org

  - pythonhosted.org

In all cases the standard HTTPS port, 443, is used for communication and is the only port that needs to be opened.

.. note::

   If you download packages on a different machine and copy them to your machine behind the fire wall you must still open the access for pip to the Python package locations.

Checking package installation
#############################

To check what packages have been installed, ssh into your host system and use the dpkg command::

  dpkg -l | grep 'fledge'


Run with PostgreSQL
###################

To start Fledge with PostgreSQL, first you need to install the PostgreSQL package explicitly. See the below links for setup

|Debian PostgreSQL|

|RPM PostgreSQL|

Also you need to change the value of Storage plugin. See |Configure Storage Plugin| or with below curl command

.. code-block:: console

    $ curl -sX PUT localhost:8081/fledge/category/Storage/plugin -d '{"value": "postgres"}'
    {
      "description": "The main storage plugin to load",
      "type": "string",
      "order": "1",
      "displayName": "Storage Plugin",
      "default": "sqlite",
      "value": "postgres"
    }

Now, it's time to restart Fledge. Thereafter you will see Fledge is running with PostgreSQL.


Using Docker Containerizer to install Fledge
#############################################

Fledge Docker containers are provided in a private repository. This repository has no authentication or encryption associated with it.

The following steps describe how to install Fledge using these containers:

- Edit the daemon.json file, whose default location is /etc/docker/daemon.json on Linux, If the daemon.json file does not exist, create it. Assuming there are no other settings in the file, it should have the following contents:

.. code-block:: console

    { "insecure-registries":["54.204.128.201:5000"] }

- Restart Docker for the changes to take effect

.. code-block:: console

    sudo systemctl restart docker.service

- Check using command

.. code-block:: console

    docker info

You should see the following output:

.. code-block:: console

    Insecure Registries:
    52.3.255.136:5000
    127.0.0.0/8

You may also refer to the Docker documentation `here <https://docs.docker.com/registry/insecure/>`_.

Ubuntu 20.04
~~~~~~~~~~~~

- To pull the Docker registry

.. code-block:: console

    docker pull 54.204.128.201:5000/fledge:latest-ubuntu2004

- To run the Docker container

.. code-block:: console

    docker run -d --name fledge -p 8081:8081 -p 1995:1995 -p 8082:80 54.204.128.201:5000/fledge:latest-ubuntu2004

Here, The GUI is forwarded to port 8082 on the host machine, it can be any port and omitted if port 80 is free.

- It is possible to check if Fledge and the Fledge GUI are running by using the following commands on the host machine

*Fledge*

.. code-block:: console

    curl -sX GET http://localhost:8081/fledge/ping

*Fledge GUI*

.. code-block:: console

    http://localhost:8082

- To attach to the running container

.. code-block:: console

    docker exec -it fledge bash

.. note::
    For Ubuntu 18.04 setup, you just need to replace ubuntu2004 with ubuntu1804.
    Images are currently only available for Ubuntu version 18.04 and 20.04.
