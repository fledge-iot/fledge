.. Links
.. |DeveloperGuides| raw:: html

   <a href="plugin_developers_guide/index.html">Developer Guides</a>

.. |FledgeArchitecture| raw:: html

   <a href="fledge_architecture.html">Fledge Architecture</a>

.. |DataPipelines| raw:: html

   <a href="building_pipelines.html">Developing Data Pipelines</a>

Introduction to Fledge
=======================

Fledge is an open Industrial IoT system designed to make collecting, filtering, processing and using operational data simpler and more open. Core to Fledge is an extensible microservice based architecture enabling any data to be read, processed and sent to any system. Coupled with this extensibility Fledge’s Apache 2 license and community of developers results in an ever growing choice of components that can be used to solve your OT data needs well into the feature.

Fledge provides a scalable, secure, robust infrastructure for collecting data from sensors, processing data at the edge using intelligent data pipelines and transporting data to historian and other management systems. Fledge also allows for edge based event detection and notification and control flows as a result of events, stimulus from upstream systems or user action. Fledge can operate over the unreliable, intermittent and low bandwidth connections often found in industrial or rugged environments.

Typical Use Cases
-----------------

The depth and breadth of Industrial IoT use cases is considerable. Fledge is designed to address them. Below are some examples of typical Fledge deployments.

Unified data collection
    The industrial edge is one of the more challenging in computing. Today there are over 100 different protocols, no standards in machine data definitions, different types of data (time-series, vibration, array, image, radiometric, transactional, etc.), sensors producing bytes/hr to gigs/hr all in environments with network, power and environmental challenges. This diversity creates pain in managing, scaling, securing and orchestrating industrial data. Ultimately resulting in silos of data with competing context. Fledge is designed to eliminate those silos by providing a very flexible data collections and distribution mechanism all using the same APIs, features and functions.

Specialized Analytical Environments
    With the advent of cloud systems and sophisticated analytic tools it may no longer be possible to have a single system that is both your system of record and the place on which the analytics takes place. Fledge allows you to distribute your data to multiple systems, either in part or as a whole. This allows you to get just the data you need to the systems that need it without compromising your system of record.

Resilience
    Fledge provides mechanisms to store and forward your data. Data is no longer lost if a connection to some key system is unavailable.

Edge processing
    Using the Fledge intelligent data pipelines concept, Fledge allows for your data to be processed close to where it is gathered. This can save both network bandwidth and reduce costs when high bandwidth sensors such as vibration monitors or image capture is used. In addition it reduces the latency when timely action is required compared with shipping and processing data in the cloud or at some centralized IT location.

No code/Low code solutions
    Fledge provides tools that allow the OT engineer to create solutions by use of existing processing elements that can be combined and augmented with little or no coding required. This allows the OT organization to be able to quickly and independently obtain the data they need for their specific requirements.

Process Optimization & Operational Efficiency
    The Fledge intelligent pipelines, with their prebuilt processing elements and through use of machine learning techniques can be used to improve operational efficiency by giving operators immediate feedback on the state of the process of product being produced without remote analytics and the associated delays involved.


Architectural Overview
----------------------

Fledge is implemented as a collection of microservices which include:

  - Core services, including security, monitoring, and storage

  - Data transformation and alerting services

  - South services: Collect data from sensors and other Fledge systems

  - North services: Transmit and integrate data to historians and other systems

  - Edge data processing applications

  - Event detection and notification

  - Set point control

Services can easily be developed and incorporated into the Fledge framework. Fledge services may also be customized by creating new plugins, written in C/C++ or Python, for data collection, processing, export, rule evaluation and event notification. The |DeveloperGuides| describe how to do this.

More detail on the Fledge architecture can be found in the section |FledgeArchitecture|.

No-code/Low-code Development
----------------------------

Fledge can be extended by writing code to add new plugins. Additionally, it is easily tailored by combining pre-written data processing filters applied in linear pipelines to data as it comes into or goes out of the Fledge system. A number of filters exist that can be customized with small snippets of code written in the Python scripting language. These snippets of code allow the end user to produce custom processing without the need to develop more complex plugins or other code. The environment also allows them to experiment with these code snippets to obtain the results desired.

Data may be processed on the way into Fledge or on the way out. Processing on the way in allows the data to be manipulated to the way the organization wants it. Processing on the way out allows the data to be manipulate to suit the up stream system that will use the data without impacting the data that might go to another up stream system.

See the section |DataPipelines|.
