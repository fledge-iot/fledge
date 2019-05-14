.. |br| raw:: html

   <br />

.. Links
.. _download page: https://foglamp.readthedocs.io/en/master/92_downloads.html
.. _foglamp-pkg: https://github.com/foglamp/foglamp-pkg

*******************************************
Building and using FogLAMP on RedHat/CentOS
*******************************************

FogLAMP can be build or installed on Red Hat or CentOS, it is currently tested against:

- Red Hat 7.6
- CentOS  7.6-1810

You may follow the instructions in the README file to build,
install and run FogLAMP on Red Hat or CentOS.

*******************************************************
Install FogLAMP on Red Hat/CentOS using the RPM package
*******************************************************

The FogLAMP RPM is available in the download page of the documentation available at `download page`_.

The RPM can also be created from the FogLAMP sources through the repository `foglamp-pkg`_ using the make_rpm script and following the instruction in the README.rst.


Installation on Red Hat
=======================

A Red Hat package should be installed before the FogLAMP RPM, follow the instructions :
::
   sudo yum-config-manager --enable 'Red Hat Enterprise Linux Server 7 RHSCL (RPMs)'
   sudo yum -y  localinstall ~/foglamp-1.5.2-0.00.x86_64.rpm


Installation on CentOS
======================

A CentOS package should be installed before the FogLAMP RPM, follow the instructions :
::
   sudo yum install -y  centos-release-scl-rh
   sudo yum -y  localinstall ~/foglamp-1.5.2-0.00.x86_64.rpm
