.. |br| raw:: html

   <br />

.. Links
.. _download page: http://dianomic.com/download-fledge
.. _fledge-pkg: https://github.com/fledge-iot/fledge-pkg

*******************************************
Building and using Fledge on RedHat/CentOS
*******************************************

Fledge can be built or installed on Red Hat or CentOS, it is currently tested against:

- Red Hat 7
- CentOS  7

You may follow the instructions in the README file to build,
install and run Fledge on Red Hat or CentOS.

*******************************************************
Install Fledge on Red Hat/CentOS using the RPM package
*******************************************************

The Fledge RPM is available in the download page of the documentation available at `download page`_.

The RPM can also be created from the Fledge sources through the repository `fledge-pkg`_ using the make_rpm script and following the instruction in the README.rst.


Installation on Red Hat
=======================

It is necessary to install a Red Hat package before Fledge can be installed successfully. The installation sequence is as follows:

.. code-block:: console 

   $ sudo yum-config-manager --enable 'Red Hat Software Collections RPMs for Red Hat Enterprise Linux 7 Server from RHUI'
   $ sudo yum -y  localinstall ~/fledge-1.8.0-1.00.x86_64.rpm


Installation on CentOS
======================

It is necessary to install a CentOS package before Fledge can be installed successfully. The installation sequence is as follows:

.. code-block:: console 

   $ sudo yum install -y  centos-release-scl-rh
   $ sudo yum -y  localinstall ~/fledge-1.8.0-1.00.x86_64.rpm

.. note::
   By default, /var/log/messages are created with read-write permissions for ‘root’ user only.
   Make sure to set the correct READ permissions.

   `sudo chmod 644 /var/log/messages`

**********************************
Build of Fledge on Red Hat/CentOS
**********************************

A gcc version newer than 4.9.0 is needed to properly use <regex> and build Fledge.

The *requirements.sh* script, executed as follows:

.. code-block:: console 

	$ sudo ./requirements.sh

installs *devtoolset-7* that provides the newer compiler.

It must be enabled before building Fledge using:

.. code-block:: console 

	$ source scl_source enable devtoolset-7

It is possible to use the following command to verify which version is currently active:

.. code-block:: console 

	$ gcc --version

The previously installed gcc will be by default enabled again after a logoff/login.

Build and use Fledge with PostgreSQL for Red Hat/CentOS
========================================================

The *rh-postgresql13* environment should be enabled using:

.. code-block:: console

	$ source scl_source enable rh-postgresql13

before building Fledge if the intention is to use the Postgres plugin.
