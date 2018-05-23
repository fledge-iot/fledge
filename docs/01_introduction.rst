.. FogLAMP documentation master file, created by
   sphinx-quickstart on Fri Sep 22 02:34:49 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. Images
.. |foglamp_all_round| image:: images/foglamp_all_round_solution.jpg

.. Links
.. _FogLAMP project on GitHub: https://github.com/foglamp/FogLAMP/issues


************
Introduction
************

What Is FogLAMP?
================

FogLAMP is an open source platform for the **Internet of Things** and an
essential component in **Fog Computing**.  It uses a modular
**microservices architecture** including sensor data collection, storage, processing and forwarding to historians, Enterprise systems and Cloud-based services. FogLAMP can run in highly available, stand alone, unattended environments that assume unreliable network connectivity.  

By providing a modular and distributable framework under an open source Apache v2 license, FogLAMP is the best platform to manage the data infrastructure for IoT. The modules can be distributed in any layer - Edge, Fog and Cloud - and they act together to provide scalability, elasticity and resilience.

FogLAMP offers an "all-round" solution for data managementi, combining a bi-directional **Northbound/Southbound** data and metadata communication with a **Eastbound/Westbound** service and object distribution.


FogLAMP Positioning in an IoT and IIoT Infrastructure
-----------------------------------------------------

FogLAMP can be used in IoT and IIoT infrastructure at Edge and in the Fog.
It stretches bi-directionally South-North/North-South and it is distributed
East-West/West-East (see figure below).

|foglamp_all_round|

.. note:: In this scenario we refer to “Cloud” as the layer above the Fog. “Fog” is where historians, gateways and middle servers coexist. In practice, the Cloud may also represent internal Enterprise systems, concentrated in regional or global corporate data centers, where larger historians, Big Data and analytical systems reside.

In practical terms, this means that:

- Intra-layer communication and data exchange:

  - At the **Edge**, microservices are installed on devices, sensors and actuators. 
  - In the **Fog**, data is collected and aggregated in gateways and regional servers.
  - In the **Cloud**, data is distributed and analysed on multiple servers, such as Big Data Systems and Data Historians.

- Inter-layer communication and data exchange:

  - From **Edge to Fog**, data is retrieved from multiple sensors and devices and it is aggregated on resilient and highly available middle servers and gateways, either in traditional Data Historians and in the new edge of Machine Learning systems.
  - From **Fog to Edge**, configuration information, metadata and other valuable data is transferred to sensors and devices.
  - From **Fog to Cloud**, the data collected and optionally transformed is transferred to more powerful distributed Cloud and Enterprise systems. 
  - From **Cloud to Fog**, results of complex analysis and other valuable information are sent to the designated gateways and middle servers that will interact with the Edge.

- Intra-layer service distribution:

  - A microservice architecture based on secure communication allows lightweight service distribution and information exchange among **Edge to Edge** devices.
  - FogLAMP provides high availability, scalability and data distribution among **Fog-to-Fog** systems. Due to its portability and modularity, FogLAMP can be installed on a large number of intermediate servers and gateways, as application instances, appliances, containers or virtualized environments.
  - **Cloud to Cloud FogLAMP server** capabilities provide scalability and elasticity in data storage, retrieval and analytics. The data collected at the Edge and Fog, also combined with external data, can be distributed to multiple systems within a Data Center and replicated to multiple Data Centers to guarantee local and faster access.

All these operations are **scheduled, automated** and **executed securely, unattended** and in a **transactional** fashion (i.e. the system can always revert to a previous state in case of failures or unexpected events).


FogLAMP Features
================

In a nutshell, these are main features of FogLAMP:

- Transactional, always on, server platform designed to work unattended and with zero maintenance.
- Microservice architecture with secured inter-communication:

  - Core System
  - Storage Layer
  - South side, sensors and device communication
  - North side, Cloud and Enterprise communication
  - Application Modules, internal application logic

- Pluggable modules for:

  - South side: multiple, data and metadata bi-directional communication
  - North side: multiple, data and metadata bi-directional communication
  - East/West side: IN/OUT Communicator with external applications
  - Plus:

    - Data and communication authentication
    - Data and status monitoring and alerting
    - Data transformation
    - Data storage and retrieval

- Small memory and processing footprint. FogLAMP can be installed and executed on inexpensive Edge devices; microservices can be distributed on sensors and actuator boards.
- Resilient and optionally highly available.
- Discoverable and cluster-based.
- Based on APIs (RESTful and non-RESTful) to communicate with sensors and other devices, to interact with user applications, to manage the platform and to be integrated with a Cloud or Data Center-based data infrastructure.
- Hardened with default secure communication that can be optionally relaxed.


FogLAMP vs Other Software
=========================

FogLAMP can solve many problems and facilitate the design and implementation of many IoT projects. That said, it is absolutely important that architects and developers have a clear idea of what to expect from FogLAMP and when it is a good fit or when other products may be a better option.

In this section, we compare FogLAMP to some other options. We have clearly prepared this section to the best of our knowledge, we welcome feedback from anybody filing an issue to the `FogLAMP project on GitHub`_.


Open Source Platforms
---------------------

EdgeX Foundry
^^^^^^^^^^^^^

EdgeX Foundry is a vendor-neutral project launched under the Linux Foundation.  EdgeX and FogLAMP share the same concepts of microservice architecture and plugins, security and hardware agnostic platform, but the objective is significantly different. 
At a closer look, the two projects are complementary and it is up to the systems and data architects to contemplate one or both projects together. The main objective of EdgeX Foundry is to build a standardized Edge computing infrastructure, whilst FogLAMP is focused on data management in the broadest definition of Fog, i.e. covering several layers from the Edge up to the Cloud. Furthermore, FogLAMP does not strictly provide control over Edge devices: there are indeed options of bi-directionality so that administrators, manual or automatic mode, can modify the configuration of software running on devices, but the goal is always related to the acquisition of data coming from the Edge, and any control is executed by integrating FogLAMP with external comp nents. Regarding EdgeX, cases focus on the control and operations of Edge devices. For this reason, is it fair to say that an IoT architect may consider to implement data management and acquisition with FogLAMP and integrate FogLAMP data check and analysis via the internal REST API with services provided by EdgeX to control the Edge devices.

In a nutshell, if your objective is to use a comprehensive Edge platform to control your IoT environment, you should consider EdgeX. If you are looking for a platform that can handle data management, collection, storage and forward connected to other systems, you should consider FogLAMP.


Kura
^^^^

Kura is an open source project developed under the IoT initiative in the Eclipse Foundation. It is Java-based and hardware platform agnostic. Plugins and bundles are implemented with `OSGi <https://www.osgi.org/>`_. The objective of Kura is similar to FogLAMP, i.e. data is collected, managed, transformed, analyzed and forwarded. The key difference resides in the choice of the platform and the solution: Kura is entirely Java-based, while FogLAMP, due to the microservice application, is language and platform agnostic.


Closed Source Platforms
-----------------------

FogHorn
^^^^^^^

The FogHorn platform is focused on Machine Learning applied at the Edge and consequently at controlling Edge devices. It also has its own set of tools and SDK that are used to manage the whole process of collecting and analyzing data, then implementing ML algorithms. The memory footprint for the smallest implementation starts at 256MB of memory and it appears to have no microservice distribution. 

Putting the obvious difference between open and closed source aside, FogHorn and FogLAMP are designed to accomplish similar goals but in a different way. FogHorn is very specialized in handling and using ML algorithms. FogLAMP provides a platform for ML, but it does not implement it: it is up to the user to select their favorite ML library and implementation and integrate it in FogLAMP.

