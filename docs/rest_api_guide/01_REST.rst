.. REST API Guide
.. https://docs.google.com/document/d/1JJDP7g25SWerNVCxgff02qp9msHbqA9nt3RAFx8-Qng

.. |br| raw:: html

   <br />

.. |ar| raw:: html

   <div align="right">

.. Images


.. Links


.. =============================================


********************
The Fledge REST API
********************

Users, administrators and applications interact with Fledge via a REST API. This section presents a full reference of the API.

.. note:: The Fledge REST API should not be confused with the internal REST API used by Fledge tasks and microservices to communicate with each other.


Introducing the Fledge REST API
================================

The REST API is the route into the Fledge appliance, it provides all user and program interaction to configure, monitor and manage the Fledge system. A separate specification will define the contents of the API, in summary however it is designed to allow for: 

- The complete configuration of the Fledge appliance
- Access to monitoring statistics for the Fledge appliance
- User and role management for access to the API
- Access to the data buffer contents


Port Usage
----------

In general Fledge components use dynamic port allocation to determine which port to use, the admin API is however an exception to this rule. The Admin API port has to be known to end-users and any user interface or management system that uses it, therefore the port on which the admin API listens must be consistent and fixed between invocations. This does not mean however that it can not be changed by the user. The user must have the option to define the port to use by the admin API to listen on. To achieve this the port will be stored in the configuration data for the admin API, using the configuration category *AdminAPI*, see Configuration. Administrators who have access to the appliance can find information regarding the port and the protocol to used (i.e. HTTP or HTTPS) in the *pid* file stored in *$FLEDGE_DATA/var/run/*:

.. code-block:: console

  $ cat data/var/run/fledge.core.pid
  { "adminAPI"  : { "protocol"  : "HTTP",
                    "port"      : 8081,
                    "addresses" : [ "0.0.0.0" ] },
    "processID" : 3585 }
  $


Fledge is shipped with a default port for the admin API to use, however the user is free to change this after installation. This can be done by first connecting to the port defined as the default and then modifying the port using the admin API. Fledge should then be restarted to make use of this new port.


Infrastructure
--------------

There are two REST API’s that allow external access to Fledge, the **Administration API** and the **User API**. The User API is intended to allow access to the data in the Fledge storage layer which buffers sensor readings, and it is not part of this current version.

The Administration API is the first API is concerned with all aspects of managing and monitoring the Fledge appliance. This API is used for all configuration operations that occur beyond basic installation.


