.. |br| raw:: html

   <br />

.. Links
.. _download page: http://dianomic.com/download-packages
.. _foglamp-pkg: https://github.com/foglamp/foglamp-pkg

*******************************************
Building and using FogLAMP on RedHat/CentOS
*******************************************

FogLAMP can be built or installed on Red Hat or CentOS, it is currently tested against:

- Red Hat 7.6
- CentOS  7.6

You may follow the instructions in the README file to build,
install and run FogLAMP on Red Hat or CentOS.

*******************************************************
Install FogLAMP on Red Hat/CentOS using the RPM package
*******************************************************

The FogLAMP RPM is available in the download page of the documentation available at `download page`_.

The RPM can also be created from the FogLAMP sources through the repository `foglamp-pkg`_ using the make_rpm script and following the instruction in the README.rst.


Installation on Red Hat
=======================

It is necessary to install a Red Hat package before FogLAMP can be installed successfully. The installation sequence is as follows:
::
   sudo yum-config-manager --enable 'Red Hat Enterprise Linux Server 7 RHSCL (RPMs)'
   sudo yum -y  localinstall ~/foglamp-1.5.2-0.00.x86_64.rpm


Installation on CentOS
======================

It is necessary to install a CentOS package before FogLAMP can be installed successfully. The installation sequence is as follows:
::
   sudo yum install -y  centos-release-scl-rh
   sudo yum -y  localinstall ~/foglamp-1.5.2-0.00.x86_64.rpm

.. note::
   By default, /var/log/messages are created with read-write permissions for ‘root’ user only.
   Make sure to set the correct READ permissions.

   `sudo chmod 644 /var/log/messages`

**********************************
Build of FogLAMP on Red Hat/CentOS
**********************************

A gcc version newer than 4.9.0 is needed to properly use <regex> and build FogLAMP.

The *requirements.sh* script, executed as follows:
::
	sudo ./requirements.sh

installs *devtoolset-7* that provides the newer compiler.

It must be enabled before building FogLAMP using:
::
	source scl_source enable devtoolset-7

It is possible to use the following command to verify which version is currently active:
::
	gcc --version

The previously installed gcc will be by default enabled again after a logoff/login.

Build and use FogLAMP with PostgreSQL for Red Hat/CentOS
========================================================

The *rh-postgresql96* environment should be enabled using:
::
	source scl_source enable rh-postgresql96

before building FogLAMP if the intention is to use the Postgres plugin.