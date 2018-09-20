.. Links to open in new tabs:
.. |FogLAMP Package Archive| raw:: html

   <a href="https://FogLAMP.readthedocs.io/en/master/92_downloads.html" target="_blank">FogLAMP Package Archive</a>

.. |FogLAMP on GitHub| raw:: html

   <a href="https://github.com/foglamp" target="_blank">https://github.com/foglamp</a>
   
.. =============================================

*****************
Quick Start Guide
*****************

Introduction to FogLAMP
=======================

FogLAMP is a distributed data management framework for the Internet of Things (IoT).  It provides a scalable, secure, robust
infrastructure for collecting data from sensors, processing data at the edge and transporting data to historianlibrarian and other
management systems. FogLAMP can operate over the unreliable, intermittent and low bandwidth connections often found in IoT applications. 

FogLAMP is implemented as a collection of microservices which include:

- Core services, including security, monitoring, and storage
- Data transformation and alerting services
- South services: Collect data from sensors and other FogLAMP systems
- North services: Transmit data to librarians and other systems
- Edge data processing applications

Services can easily be developed and incorporated into the FogLAMP framework. The FogLAMP Developers Guide describes how to do this.

Installing FogLAMP
==================

FogLAMP is extremely lightweight and can run on inexpensive edge devices, sensors and actuator boards.  For the purposes of this manual,
we assume that all services are running on a Raspberry Pi running the Raspbian operating system.

You can obtain FogLAMP in two ways.  

- As prebuilt binaries for Debian using either Intel or ARM architectures. The binaries can be downloaded from the |FogLAMP Package Archive|. This is the recommended method, especially for new users.
- As source code from |FogLAMP on GitHub|.  Instructions for downloading and building FogLAMP source code can be found in the FogLAMP Developer’s Guide.

In general, FogLAMP installation will require the following packages

- FogLAMP core
- FogLAMP user interface
- One or more FogLAMP South services
- One or more FogLAMP North service (OSI PI and OCS north services are included in FogLAMP core)

