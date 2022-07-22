.. Links
.. |DeveloperGuides| raw:: html

   <a href="plugin_developers_guide/index.html">Developer Guides</a>

.. |FledgeArchitecture| raw:: html

   <a href="fledge_architecture.html">Fledge Architecture</a>

.. |DataPipelines| raw:: html


   <a href="building_pipelines.html">Developing Data Pipelines</a>

Introduction to Fledge
=======================

Fledge is a system designed to make the process of gathering, processing and using operational data simpler and more open. Core to the design of Fledge is extensible to enable any data to be read, processed and sent to any system. The processing and analytics that can be performed and the events that can be detected and how those events get notified to users and systems is also part of Fledge's extensible design. Coupled with this extensibility the open source nature of Fledge allows other to benefit from extensions, resulting in an ever growing choice of components that can be used to solve your OT data needs.

It provides a salable, secure, robust infrastructure for collecting data from sensors, processing data at the edge using intelligent data pipelines and transporting data to historian and other management systems. Fledge also allows for edge based event detection and notification and control flows as a result of events, stimulus from upstream systems or user action. Fledge can operate over the unreliable, intermittent and low bandwidth connections often found in industrial or rugged environments.

Typical Use Cases
-----------------

Fledge may be used in a number of different ways and for different reasons to suit your operational data requirements, listed here are just a few of the ways Fledge is being used.

Unified data collection
    There are many situation that have arisen over time whereby a heterogeneous control system allowed data to collected and processed in a single system. With the advent of the internet of things and a growing number of after market sensors becoming available this is no longer the case and many installations find themselves in a situation whereby they have silos of data that reside in different systems. Fledge is designed to help you illuminate those silos by providing a very flexible data collection and distribution mechanism.

Specialized Analytical Environments
    The advent of cloud systems and sophisticated analytic tools it may no longer be possible to have a single system that is both your system of record and the place on which the analytics takes place. Fledge allows you to distribute your data to multiple systems, either in part or as a whole. This allows you to get just the data you need to the systems that need it without compromising your system of record.

Resilience
    Fledge provides mechanisms to store and forward your data as and went connectivity, systems or bandwidth is available. Data is no longer lost if a connection to some key system is unavailable.

Edge processing
    Fledge allows for your data to be processed, using the Fledge intelligent data pipelines concept, close to where it is gathered. This can save both network bandwidth and reduce costs when high bandwidth sensors such as vibration monitors or image capture is used. In addition it reduces the latency when timely action is required compared with shipping and processing data in the cloud or at some centralized IT location.

No code/Low code solutions
    Fledge provides tools that allow the OT engineer to create solutions by use of existing processing elements that can be combined and augmented with little or no coding required. This allows the OT organization to be able to quickly obtain the data they need for their specific requirements.

Process Optimization & Operational Efficiency
    The Fledge intelligent pipelines, with their prebuilt processing elements and through use of machine learning techniques can be used to improve operational efficiency by giving operators immediate feedback on the state of the process of product being produced without remote analytics and the associated delays involved.


Architectural Overview
----------------------

Fledge is implemented as a collection of microservices which include:

  - Core services, including security, monitoring, and storage

  - Data transformation and alerting services

  - South services: Collect data from sensors and other Fledge systems

  - North services: Transmit data to historians and other systems

  - Edge data processing applications

  - Event detection and notification

  - Set point control

Services can easily be developed and incorporated into the Fledge framework. Fledge services may also be customized by creating new plugins, written in C/C++ or Python, for data collection, processing, export, rule evaluation and event notification. The |DeveloperGuides| describe how to do this.

More detail on the Fledge architecture can be found in the section |FledgeArchitecture|.

No-code/Low-code Development
----------------------------

Fledge can be extended by writing code to add new plugins, however it is also designed to allow it to be easily tailored by combining pre-written data processing filters to be applied in linear pipelines to data as it comes into or goes out of the Fledge system. In addition a number of filters exist that can be customized with small snippets of code written in the Python scripting language. These snippets of code allow the end user to produce custom processing without the need to develop more complex plugins or other code. The environment also allows them to experiment with these code snippets to obtain the results they want.

Data may be processed on the way into Fledge or on the way out. Processing on the way in allows the data to be manipulated to the way the organization wants it. Processing on the way out allows the data to be manipulate to suit the up stream system that will use the data without impacting the data that might go to another up stream system.

See the section |DataPipelines|.
