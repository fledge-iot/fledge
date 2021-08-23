Installing Fledge
==================

Fledge is extremely lightweight and can run on inexpensive edge devices, sensors and actuator boards.  For the purposes of this manual, we assume that all services are running on a Raspberry Pi running the Raspbian operating system. Be sure your system has plenty of storage available for data readings.

If your system does not have Raspbian pre-installed, you can find instructions on downloading and installing it at https://www.raspberrypi.org/downloads/raspbian/.  After installing Raspbian, ensure you have the latest updates by executing the following commands on your Fledge server::

  sudo apt-get update
  sudo apt-get upgrade
  sudo apt-get update

You can obtain Fledge in three ways:

- Dianomic Systems hosts a package repository that allows the Fledge packages to be loaded using the system package manage. This is the recommended method for long term use of Fledge as it gives access to all the Fledge plugins and provides a route for easy upgrade of the Fledge packages. This also has the advantages that once the repository is configured you are able to install new plugins directly from the Fledge user interface without the need to resort to the Linux command line.
- Dianomic Systems offers pre-built, certified binaries of Fledge for Debian using either Intel or ARM architectures. This is perhaps the simplest method for users not used to Linux. You can download the complete set of packages from https://fledge-iot.readthedocs.io/en/latest/92_downloads.html.
- As source code from https://github.com/fledge-iot/.  Instructions for downloading and building Fledge source code can be found in the Fledge Developer’s Guide

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

On a Ubuntu or Debian system, including the Raspberry Pi, the package manager that is supported in *apt*. You will need to add the Dianomic Systems archive server into the configuration of apt on your system. The first thing that most be done is to add the key that is used to verify the package repository. To do this run the command

.. code-block:: console

   wget -q -O - http://archives.fledge-iot.org/KEY.gpg | sudo apt-key add -

Once complete you can add the repository itself into the apt configuration file /etc/apt/sources.list. The simplest way to do this is the use the *add-apt-repository* command. The exact command will vary between systems;

  - Raspberry Pi does not have an apt-add-repository command, the user must edit the apt sources file manually

    .. code-block:: console

       sudo vi /etc/apt/sources.list
       
    and add the line
    
    .. code-block:: console

       deb  http://archives.fledge-iot.org/latest/buster/armv7l/ /

    to the end of the file.

  - Users with an Intel or AMD system with Ubuntu 18.04 should run

    .. code-block:: console

       sudo add-apt-repository "deb http://archives.fledge-iot.org/latest/ubuntu1804/x86_64/ / "

  - Users with an Intel or AMD system with Ubuntu 20.04 should run

    .. code-block:: console

       sudo add-apt-repository "deb http://archives.fledge-iot.org/latest/ubuntu2004/x86_64/ / "

    .. note::
        We do not support the `aarch64` architecture with Ubuntu 20.04 yet.

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

RedHat & CentOS
~~~~~~~~~~~~~~~

The RedHat and CentOS flavors of Linux use a different package management system, known as *yum*. Fledge also supports a package management system for the yum package manager.

To add the fledge repository to the yum package manager run the command

.. code-block:: console

   sudo rpm --import http://archives.fledge-iot.org/RPM-GPG-KEY-fledge

CentOS users should then create a file called fledge.repo in the directory /etc/yum.repos.d and add the following content

.. code-block:: console

   [fledge]
   name=fledge Repository
   baseurl=http://archives.fledge-iot.org/latest/centos7/x86_64/
   enabled=1
   gpgkey=http://archives.fledge-iot.org/RPM-GPG-KEY-fledge
   gpgcheck=1

Users of RedHat systems should do the same, however the files content is slightly different

.. code-block:: console


   [fledge]
   name=fledge Repository
   baseurl=http://archives.fledge-iot.org/latest/rhel7/x86_64/
   enabled=1
   gpgkey=http://archives.fledge-iot.org/RPM-GPG-KEY-fledge
   gpgcheck=1

There are a few pre-requisites that need to be installed on these platforms, they differ slightly between the two of them.

On CentOS 7 run the commands

.. code-block:: console

   sudo yum install -y centos-release-scl-rh
   sudo yum install -y epel-release


On RedHat 7 run the command

.. code-block:: console

   sudo yum-config-manager --enable 'Red Hat Enterprise Linux Server 7 RHSCL (RPMs)'
   sudo yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

You can now install and upgrade fledge packages using the yum command. For example to install fledge and the fledge GUI you run the command

.. code-block:: console

   sudo yum install -y fledge fledge-gui


Installing Fledge downloaded packages
######################################

Assuming you have downloaded the packages from the download link given above. Use SSH to login to the system that will host Fledge services. For each Fledge package that you choose to install, type the following command::

  sudo apt -y install PackageName

The key packages to install are the Fledge core and the Fledge User Interface::

  sudo DEBIAN_FRONTEND=noninteractive apt -y install ./fledge-1.8.0-armv7l.deb
  sudo apt -y install ./fledge-gui-1.8.0.deb

You will need to install one of more South plugins to acquire data.  You can either do this now or when you are adding the data source. For example, to install the plugin for the Sense HAT sensor board, type::

  sudo apt -y install ./fledge-south-sensehat-1.8.0-armv7l.deb

You may also need to install one or more North plugins to transmit data.  Support for OSIsoft PI and OCS are included with the Fledge core package, so you don't need to install anything more if you are sending data to only these systems.

Checking package installation
#############################

To check what packages have been installed, ssh into your host system and use the dpkg command::

  dpkg -l | grep 'fledge'
