.. Fledge Glossary

.. |github| raw:: html

    <a href="https://github.com/fledge-iot/fledge">Fledge GitHub repository</a>

********
Glossary
********

The following are a set of definitions for terms used within the Fledge documentation and code, these are designed to be an aid to understanding some of the principles behind Fledge and improve the comprehension of the documentation by ensuring all readers have a common understanding of the terms used. If you feel any terms are missing or not fully explained please raise an issue against, or contribute to, the documentation in the |github|.

.. glossary::

    Asset
        A representation of a set of device or set of values about a device or entity that is being monitored and possibly controlled by Fledge. It may also be used to represent a subset of a device. These values are a collection of :term:`Datapoints<Datapoint>` that are the actual values. An asset contains a unique name that is used to reference the data about the asset. An asset is an abstract concept and has no real implementation with the fledge code, instead a :term:`reading<Reading>` is used to represent the state of an asset at a point in term. The phase asset is used to represent a time series collection of 0 or more :term:`readings<Reading>`.

    Control Service
        An optional microservice that is used by the control features of Fledge to route control messages from the various sources of control and send them to the :term:`south service<South Service>` which implements the control path for the :term:`assets<Asset>` under control.

    Core Service
        The :term:`service<Service>` within Fledge that is responsible for the oversight of all the other services. It provides configuration management, monitoring, registration and routing services. It is also responsible for the public API into the Fledge system and the execution of periodic tasks such as :term:`purge<Purge>`, statistics and backup.

    Datapoint
        A datapoint is a container for data, each datapoint represents a value that is known about an asset and has a name for that value and the value itself. Values may be one of many types; simpler scalar values, alpha numeric strings, arrays of scalar values, images, arbitrary binary objects or a collection of datapoints.

    Filter Plugin
        A filter plugin is a :term:`plugin<Plugin>` that implements an operation on one or more :term:`reading<Reading>` as it passes through the Fledge system. This processing may add, remove or augment the data as it passes through Fledge. Filters are arrange as linear :term:`pipelines<Pipeline>` in either the :term:`south service<South Service>` as data is ingested into Fledge or the :term:`north services<North Service>` and :term:`tasks<Task>` as data is passed upstream to the systems that receive data from Fledge.

    Microservice
        A microservice is a small service that implements parts of the Fledge functionality. They are also referred to as :term:`services<Service>`.

    Notification Delivery Plugin
        A notification delivery plugin is used by the :term:`notification service<Notification Service>` to delivery notifications when a :term:`notification rule<Notification Rule Plugin>` triggers. A notification delivery plugin may send notification data to external systems, trigger internal Fledge operations or create :term:`reading<Reading>` data within the Fledge :term:`storage service<Storage Service>`.

    Notification Rule Plugin
        A notification rule plugin is used by the notification service to determine if a notification should be sent. The rule plugin receives :term:`reading<Reading>` data from the Fledge :term:`storage service<Storage Service>`, evaluates a rule against that data and returns a triggered or cleared state to the notification service.

    Notification Service
        An optional :term:`service<Service>` within Fledge that is responsible for the execution and delivery of notifications when events occurs in the data that is being ingested into Fledge.

    North
        An abstract term for any service or system to which Fledge sends data that is has ingested. Fledge may also receive control message from the north as well as from other locations.

    North Plugin
        A :term:`plugin<Plugin>` that implements to connection to an upstream system. North plugins are responsible to both implement the communication to the north systems and also the translation from internal data representations to the representation used in the external system.

    North Service
        A :term:`service<Service>` responsible for connections upstream from Fledge. These are usually systems that will receive data that Fledge has ingested and/or processed. There may also be control data flows that operate from the north systems into the Fledge system.

    North Task
        A :term:`task<Task>` that is run to send data to upstream systems from Fledge. It is very similar in operation and concept to a :term:`north service<North Service>`, but differs from a north service in that it does not always run, it is scheduled using a time based schedule and is designed for situation where connection to the upstream system is not always available or desirable.

    Pipeline
        A linear collection of zero or more :term:`filters<Filter>` connected between with the :term:`south plugin<South Plugin>` that ingests data and the :term:`storage service<Storage Service>`, or between the :term:`storage service<Storage Service>` and the :term:`north plugin<North Plugin>` as data exits Fledge to be sent to upstream systems.

    Plugin
        A dynamically loadable code fragment that is used to enhance the capabilities of Fledge. These plugins may implement a :term:`south<South>` interface to devices and systems, a :term:`north<North>` interface to systems that receive data from Fledge, a :term:`storage plugin<Storage Plugin>` used to buffer :term:`readings<Reading>`, a :term:`filter plugin<Filter Plugin>` used to process data, a :term:`notification rule<Notification Rule Plugin>` or :term:`notification delivery<Notification Delivery Plugin>` plugin. Plugins have well defined interfaces, they can be written by third parties without recourse to modifying the Fledge services and are shipped externally to Fledge to allow for diverse installations of Fledge. Plugins are the major route by which Fledge is customized for individual use cases.

    Purge
        The process by which :term:`readings<Reading>` are removed from the :term:`storage service<Storage Service>`.

    Reading
        A reading is the presentation of an :term:`asset<Asset>` at a point in time. It contains the asset name, two timestamps and the collection of :term:`datapoints<Datapoint>` that represent the state of the asset at that point in time. A reading has two timestamps to allow for the time to be recorded when Fledge first read the data and also for the device itself to give a time that it sets for when the data was created. Not all devices are capable of reporting timestamps and hence this second timestamp may be the same as the first.

    Service
        Fledge is implemented as a set of services, each of which runs constantly and implements a subset of the system functionality. There are a small set of fixed services, such as the :term:`core service<Core Service>` or :term:`storage service<Storage Service>`, optional services for enhanced functionality, such as the :term:`notification service<Notification Service>` and :term:`control service<Control Service>`. There are also a set of non-fixed services of various types used to interact with downstream or :term:`south<South>` devices and upstream or :term:`north<North>` systems.

    South
        An abstract term for any device or service from which Fledge ingests data or over which Fledge exerts control.

    South Service
        A :term:`service<Service>` responsible for communication with a device or service from which Fledge is ingesting data. Each south service connections to a single device and can collect data from that device and optionally send control signals to that device. A south service may represent one or more :term:`assets<Asset>`.

    South Plugin
        A south plugin is a :term:`plugin<Plugin>` that implements the interface to a device or system from which Fledge is collecting data and optionally to which Fledge is sending control signals.

    Storage
        A :term:`microservice<Microservice>` that implements either permanent or transient storage services used to both buffer :term:`readings<Reading>` within Fledge and also to store Fledge's configuration information. The storage services uses either one or two :term:`storage plugins<Storage Plugin>` to store the configuration data and the :term:`readings<Reading>` data.

    Storage Plugin
        A :term:`plugin<Plugin>` that implements the storage requirements of the Fledge :term:`storage service<Storage Service>`. A plugin may implement the storage of both configuration and :term:`readings<Reading>` or it may just implement :term:`readings<Reading>` storage. In this later case Fledge will use two storage plugins, one to store the configuration and the other to store the readings.

    Task
        A task implements functionality that only runs for specific times within Fledge. It is used to initiate periodic operations that are not required to be always running. Amongst the tasks that form part of Fledge are the :term:`purge task<Purge>`, :term:`north tasks<North Task>`, backup and statistics gathering tasks.
