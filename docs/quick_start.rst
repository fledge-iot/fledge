.. Images
.. |dashboard| image:: images/dashboard.JPG
.. |south_services| image:: images/south_services.JPG
.. |south_service_config| image:: images/south_service_config.JPG
.. |north_services| image:: images/north_services.JPG
.. |pi_plugin_config| image:: images/pi_plugin_config.JPG
.. |settings| image:: images/settings.JPG
.. |backup| image:: images/backup.JPG
.. |support| image:: images/support.JPG
.. |viewing_data| image:: images/viewing_data.JPG
.. |view_graph| image:: images/view_graph.jpg
.. |view_hide| image:: images/view_hide.jpg
.. |view_summary| image:: images/view_summary.jpg
.. |view_times| image:: images/view_times.jpg
.. |view_spreadsheet| image:: images/view_spreadsheet.jpg


*****************
Quick Start Guide
*****************

Introduction to Fledge
=======================

Fledge is an open sensor-to-cloud data fabric for the Internet of Things (IoT) that connects people and systems to the information they need to operate their business.  It provides a scalable, secure, robust infrastructure for collecting data from sensors, processing data at the edge and transporting data to historian and other management systems. Fledge can operate over the unreliable, intermittent and low bandwidth connections often found in IoT applications.

Fledge is implemented as a collection of microservices which include:

- Core services, including security, monitoring, and storage
- Data transformation and alerting services
- South services: Collect data from sensors and other Fledge systems
- North services: Transmit data to historians and other systems
- Edge data processing applications

Services can easily be developed and incorporated into the Fledge framework. The Fledge Developer Guides describe how to do this.

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

       sudo add-apt-repository ‘deb http://archives.fledge-iot.org/latest/ubuntu1804/x86_64/ / ‘


  - Users with an Arm system with Ubuntu 18.04, such as the Odroid board, should run

    .. code-block:: console

       sudo add-apt-repository ‘deb http://archives.fledge-iot.org/latest/ubuntu1804/aarch64/ / ‘


  - Users of the Mendel operating system on a Google Coral create the file /etc/apt/sources.list.d/fledge.list and insert the following content

    .. code-block:: console

       deb http://archives.fledge-iot.org/latest/mendel/aarch64/ /

Once the repository has been added you must inform the package manager to go and fetch a list of the packages it supports. To do this run the command

.. code-block:: console

   sudo apt update

You are now ready to install the Fledge packages. You do this by running the command

.. code-block:: console

   sudo apt -y install *package*

You may also install multiple packages in a single command. To install the base fledge package, the fledge user interface and the sinusoid south plugin run the command

.. code-block:: console

   sudo apt -y install fledge fledge-gui fledge-south-sinusoid



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
   baseurl=http://archives.fledge-iot.org/latest/centos76/x86_64/
   enabled=1
   gpgkey=http://archives.fledge-iot.org/RPM-GPG-KEY-fledge
   gpgcheck=1

Users of RedHat systems should do the same, however the files content is slightly different

.. code-block:: console


   [fledge]
   name=fledge Repository
   baseurl=http://archives.fledge-iot.org/latest/rhel76/x86_64/
   enabled=1
   gpgkey=http://archives.fledge-iot.org/RPM-GPG-KEY-fledge
   gpgcheck=1

There are a few pre-requisites that need to be installed on these platforms, they differ slightly between the two of them.

On CentOS run the commands

.. code-block:: console

   sudo yum install -y centos-release-scl-rh
   sudo yum install -y epel-release


On RedHat run the command

.. code-block:: console

   sudo yum-config-manager --enable 'Red Hat Enterprise Linux Server 7 RHSCL (RPMs)'

You can now install and upgrade fledge packages using the yum command. For example to install fledge and the fledge GUI you run the command

.. code-block:: console

   sudo yum install -y fledge fledge-gui


Installing Fledge downloaded packages
######################################

Assuming you have downloaded the packages from the download link given above. Use SSH to login to the system that will host Fledge services. For each Fledge package that you choose to install, type the following command::

  sudo apt -y install PackageName

The key packages to install are the Fledge core and the Fledge User Interface::

  sudo apt -y install ./fledge-1.8.0-armv7l.deb
  sudo apt -y install ./fledge-gui-1.8.0.deb

You will need to install one of more South plugins to acquire data.  You can either do this now or when you are adding the data source. For example, to install the plugin for the Sense HAT sensor board, type::

  sudo apt -y install ./fledge-south-sensehat-1.8.0-armv7l.deb

You may also need to install one or more North plugins to transmit data.  Support for OSIsoft PI and OCS are included with the Fledge core package, so you don't need to install anything more if you are sending data to only these systems.

Checking package installation
#############################

To check what packages have been installed, ssh into your host system and use the dpkg command::

  dpkg -l | grep 'fledge'

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

Troubleshooting Fledge
#######################

Fledge logs status and error messages to syslog.  To troubleshoot a Fledge installation using this information, open a session to the Fledge server and type::

  grep -a 'fledge' /var/log/syslog | tail -n 20

Running the Fledge GUI
=======================

Fledge offers an easy-to-use, browser-based GUI.  To access the GUI, open your browser and enter the IP address of the Fledge server into the address bar.  This will display the Fledge dashboard.

You can easily use the Fledge UI to monitor multiple Fledge servers.  To view and manage a different server, click "Settings" in the left menu bar. In the "Connection Setup" pane, enter the IP address and port number for the new server you wish to manage.  Click the "Set the URL & Restart" button to switch the UI to the new server.

If you are managing a very lightweight server or one that is connected via a slow network link, you may want to reduce the UI update frequency to minimize load on the server and network.  You can adjust this rate in the "GUI Settings" pane of the Settings screen.  While the graph rate and ping rate can be adjusted individually, in general you should set them to the same value.

Fledge Dashboard
#################
+-------------+
| |dashboard| |
+-------------+

This screen provides an overview of Fledge operations.  You can customize the information and time frames displayed on this screen using the drop-down menus in the upper right corner.  The information you select will be displayed in a series of graphs.

You can choose to view a graph of any of the sensor reading being collected by the Fledge system.  In addition, you can view graphs of the following system-wide information:

  - **Readings:** The total number of data readings collected by Fledge since system boot
  - **Buffered:** The number of data readings currently stored by the system
  - **Discarded:** Number of data readings discarded before being buffered (due to data errors, for example)
  - **Unsent:** Number of data readings that were not sent successfully
  - **Purged:** The total number of data readings that have been purged from the system
  - **Unsnpurged:** The number of data readings that were purged without being sent to a North service.

Managing Data Sources
=====================
+------------------+
| |south_services| |
+------------------+

Data sources are managed from the South Services screen.  To access this screen, click on “South” from the menu bar on the left side of any screen.

The South Services screen displays the status of all data sources in the Fledge system.  Each data source will display its status, the data assets it is providing, and the number of readings that have been collected.

Adding Data Sources
###################

To add a data source, you will first need to install the plugin for that sensor type.  If you have not already done this, open a terminal session to your Fledge server.  Download the package for the plugin and enter::

  sudo apt -y install PackageName

Once the plugin is installed return to the Fledge GUI and click on “Add+” in the upper right of the South Services screen.  Fledge will display a series of 3 screens to add the data source:

1. The first screen will ask you to select the plugin for the data source from the list of installed plugins.  If you do not see the plugin you need, refer to the Installing Fledge section of this manual.  In addition, this screen allows you to specify a display name for the data source.

2. The second screen allows you to configure the plugin and the data assets it will provide. 

   .. note::

      Every data asset in Fledge must have a unique name.  If you have multiple sensors using the same plugin, modify the asset names on this screen so they are unique. 
      
   Some plugins allow you to specify an asset name prefix that will apply to all the asset names for that sensor. Refer to the individual plugin documentation for descriptions of the fields on this screen.

3. If you modify any of the configuration fields, click on the “save” button to save them.

4. The final screen allows you to specify whether the service will be enabled immediately for data collection or await enabling in the future.

Configuring Data Sources
########################
+------------------------+
| |south_service_config| |
+------------------------+

To modify the configuration of a data source, click on its name in the South Services screen. This will display a list of all parameters available for that data source.  If you make any changes, click on the “save” button in the top panel to save the new configuration.  Click on the “x” button in the upper right corner to return to the South Services screen.

Enabling and Disabling Data Sources
###################################

To enable or disable a data source, click on its name in the South Services screen. Under the list of data source parameters, there is a check box to enable or disable the service.  If you make any changes, click on the “save” button in the bottom panel near the check box to save the new configuration.

Viewing Data
############
+----------------+
| |viewing_data| |
+----------------+

You can inspect all the data buffered by the Fledge system on the Assets page.  To access this page, click on “Assets & Readings” from the left-side menu bar.

This screen will display a list of every data asset in the system.  Alongside each asset are two icons; one to display a graph of the asset and another to download the data stored for that asset as a CSV file.

Display Graph
~~~~~~~~~~~~~

.. image:: images/graph_icon.jpg
   :align: left

By clicking on the graph button next to each asset name, you can view a graph of individual data readings. A graph will be displayed with a plot for each data point within the asset.

+--------------+
| |view_graph| |
+--------------+

It is possible to change the time period to which the graph refers by use of the plugin list in the top left of the graph.

+--------------+
| |view_times| |
+--------------+

Where an asset contains multiple data points each of these is displayed in a different colour. Graphs for particular data points can be toggled on and off by clicking on the key at the top of the graph. Those data points not should will be indicated by striking through the name of the data point.

+-------------+
| |view_hide| |
+-------------+

A summary tab is also available, this will show the minimum, maximum and average values for each of the data points. Click on *Summary* to show the summary tab.

+----------------+
| |view_summary| |
+----------------+

Download Data
~~~~~~~~~~~~~

.. image:: images/download_icon.jpg
   :align: left

By clicking on the download icon adjacent to each asset you can download the stored data for the asset. The format of the file is download is a CSV file that is designed to be loaded int a spreadsheet such as Excel, Numbers or OpenOffice Calc.

The file contains a header row with the names of the data points within the asset, the first column is always the timestamp when the reading was taken, the header for this being *timestamp*. The data is sorted in chronological order with the newest data first.

+--------------------+
| |view_spreadsheet| |
+--------------------+


Sending Data to Other Systems
=============================
+------------------+
| |north_services| |
+------------------+

Data destinations are managed from the North Services screen.  To access this screen, click on “North” from the menu bar on the left side of any screen.

The North Services screen displays the status of all data sending processes in the Fledge system.  Each data destination will display its status and the number of readings that have been collected.

Adding Data Destinations
########################

To add a data destination, click on “Create North Instance+” in the upper right of the North Services screen.  Fledge will display a series of 3 screens to add the data destination:

1. The first screen will ask you to select the plugin for the data destination from the list of installed plugins.  If you do not see the plugin you need, refer to the Installing Fledge section of this manual.  In addition, this screen allows you to specify a display name for the data destination. In addition, you can specify how frequently data will be forwarded to the destination in days, hours, minutes and seconds.  Enter the number of days in the interval in the left box and the number of hours, minutes and seconds in format HH:MM:SS in the right box.
2. The second screen allows you to configure the plugin and the data assets it will send.  See the section below for specifics of configuring a PI, EDS or OCS destination.
3. The final screen loads the plugin.  You can specify whether it will be enabled immediately for data sending or to await enabling in the future.

Configuring Data Destinations
#############################

To modify the configuration of a data destination, click on its name in the North Services screen. This will display a list of all parameters available for that data source.  If you make any changes, click on the “save” button in the top panel to save the new configuration.  Click on the “x” button in the upper right corner to return to the North Services screen.

Enabling and Disabling Data Destinations
########################################

To enable or disable a data source, click on its name in the North Services screen. Under the list of data source parameters, there is a check box to enable or disable the service.  If you make any changes, click on the “save” button in the bottom panel near the check box to save the new configuration.

Using the OMF plugin
####################

OSISoft data historians are one of the most common destinations for Fledge data.  Fledge supports the full range of OSISoft historians; the PI System, Edge Data Store (EDS) and OSISoft Cloud Services (OCS). To send data to a PI server you may use either the older PI Connector Relay or the newer PI Web API OMF endpoint. It is recommended that new users use the PI Web API OMF endpoint rather then the Connector Relay which is no longer supported by OSIsoft.

.. include:: OMF.rst

Backing up and Restoring Fledge
=================================
+----------+
| |backup| |
+----------+

You can make a complete backup of all Fledge data and configuration.  To do this, click on "Backup & Restore" in the left menu bar. This screen will show a list of all backups on the system and the time they were created.
To make a new backup, click the "Backup" button in the upper right corner of the screen.  You will briefly see a "Running" indicator in the lower left of the screen.  After a period of time, the new backup will appear in the list.  You may need to click the refresh button in the upper left of the screen to refresh the list.
You can restore, delete or download any backup simply by clicking the appropriate button next to the backup in the list.

Troubleshooting and Support Information
=======================================
+-----------+
| |support| |
+-----------+

Fledge keep detailed logs of system events for both auditing and troubleshooting use.  To access them, click "Logs" in the left menu bar.  There are five logs in the system:

  - **Audit:** Tracks all configuration changes and data uploads performed on the Fledge system.
  - **Notifications:** If you are using the Fledge notification service this log will give details of notifications that have been triggered
  - **Packages:** This log will give you information about the installation and upgrade of Fledge packages for services and plugins.
  - **System:** All events and scheduled tasks and their status.
  - **Tasks:** The most recent scheduled tasks that have run and their status

If you have a service contract for your Fledge system, your support technician may ask you to send system data to facilitate troubleshooting an issue.  To do this, click on “Support” in the left menu and then “Request New” in the upper right of the screen.  This will create an archive of information.  Click download to retrieve this archive to your system so you can email it to the technician.
