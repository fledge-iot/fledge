Fledge Plugins
==============

The following set of plugins are available for Fledge. These plugins
extend the functionality by adding new sources of data, new destinations,
processing filters that can enhance or modify the data, rules for
notification delivery and notification delivery mechanisms.

South Plugins
-------------

South plugins add new ways to get data into Fledge, a number of south
plugins are available ready built or users may add new south plugins of
their own by writing them in Python or C/C++.

.. list-table:: Fledge South Plugins
    :widths: 20 50
    :header-rows: 1

    * - Name
      - Description
    * - am2315
      - Fledge south plugin for an AM2315 temperature and humidity sensor
    * - benchmark
      - A Fledge benchmark plugin to measure the ingestion rates on particular hardware
    * - cc2650
      - A Fledge south plugin for the Texas Instruments SensorTag CC2650
    * - coap
      - A south plugin for Fledge that pulls data from a COAP sensor
    * - csv
      - A Fledge south plugin in C++ for reading CSV files
    * - csv-async
      - A Fledge asynchronous plugin for reading CSV data
    * - dht
      - A Fledge south plugin in C++ that interfaces to a DHT-11 temperature and humidity sensor
    * - dht11
      - A Fledge south plugin that interfaces a DHT-11 temperature sensor
    * - dnp3
      - A south plugin for Fledge that implements the DNP3 protocol
    * - envirophat
      - A Fledge south service for the Raspberry Pi EnviroPhat sensors
    * - expression
      - A Fledge south plugin that uses a user define expression to generate data
    * - FlirAX8
      - A Fledge hybrid south plugin that uses fledge-south-modbus-c to get temperature data from a Flir Thermal camera
    * - game
      - The south plugin used for the Fledge lab session game involving remote controlled cars
    * - http
      - A Python south plugin for Fledge used to connect one Fledge instance to another
    * - ina219
      - A Fledge south plugin for the INA219 voltage and current sensor
    * - modbus-c
      - A Fledge south plugin that implements modbus-tcp and modbus-rtu
    * - modbustcp
      - A Fledge south plugin that implements modbus-tcp in Python
    * - mqtt-sparkplug
      - A Fledge south plugin that implements the Sparkplug API over MQTT
    * - opcua
      - A Fledge south service that pulls data from an OPC-UA server
    * - openweathermap
      - A Fledge south plugin to pull weather data from OpenWeatherMap
    * - playback
      - A Fledge south plugin to replay data stored in a CSV file
    * - pt100
      - A Fledge south plugin for the PT100 temperature sensor
    * - random
      - A south plugin for Fledge that generates random numbers
    * - randomwalk
      - A Fledge south plugin that returns data that with randomly generated steps
    * - roxtec
      - A Fledge south plugin for the Roxtec cable gland project
    * - sensehat
      - A Fledge south plugin for the Raspberry Pi Sensehat sensors
    * - sensorphone
      - A Fledge south plugin the task to the iPhone SensorPhone app
    * - sinusoid
      - A Fledge south plugin that produces a simulated sine wave
    * - systeminfo
      - A Fledge south plugin that gathers information about the system it is running on.
    * - usb4704
      - A Fledge south plugin the Advantech USB-4704 data acquisition module
    * - wind-turbine
      - A Fledge south plugin for a number of sensor connected to a wind turbine demo


North Plugins
-------------

North plugins add new destinations to which data may be sent by Fledge. A
number of north plugins are available ready built or users may add new
north plugins of their own by writing them in Python or C/C++.

.. list-table:: Fledge North Plugins
    :widths: 20 50
    :header-rows: 1

    * - Name
      - Description
    * - gcp
      - null
    * - http
      - A Python implementation of a north plugin to send data between Fledge instances using HTTP
    * - http-c
      - A Fledge north plugin that sends data between Fledge instances using HTTP/HTTPS
    * - kafka
      - A Fledge plugin for sending data north to Apache Kafka
    * - opcua
      - A north plugin for Fledge that makes it act as an OPC-UA server for the data it reads from sensors
    * - thingspeak
      - A Fledge north plugin to send data to Matlab's ThingSpeak cloud


Filter Plugins
--------------

Filter plugins add new ways in which data may be modified, enhanced
or cleaned as part of the ingress via a south service or egress to a
destination system. A number of north plugins are available ready built
or users may add new north plugins of their own by writing them in Python
or C/C++.

It is also possible, using particular filters, to supply expressions
or script snippets that can operate on the data as well. This provides a
simple way to process the data in Fledge as it is read from devices or
written to destination systems.

.. list-table:: Fledge Filter Plugins
    :widths: 20 50
    :header-rows: 1

    * - Name
      - Description
    * - asset
      - A Fledge processing filter that is used to block or allow certain assets to pass onwards in the data stream
    * - change
      - A Fledge processing filter plugin that only forwards data that changes by more than a configurable amount
    * - delta
      - A Fledge processing filter plugin that removes duplicates from the stream of data and only forwards new values that differ from previous values by more than a given tolerance
    * - expression
      - A Fledge processing filter plugin that applies a user define formula to the data as it passes through the filter
    * - fft
      - A Fledge processing filter plugin that calculates a Fast Fourier Transform across sensor data
    * - Flir-Validity
      - A Fledge processing filter used for processing temperature data from a Flir thermal camera
    * - metadata
      - A Fledge processing filter plugin that adds metadata to the readings in the data stream
    * - python27
      - A Fledge processing filter that allows Python 2 code to be run on each sensor value.
    * - python35
      - A Fledge processing filter that allows Python 3 code to be run on each sensor value.
    * - rate
      - A Fledge processing filter plugin that sends reduced rate data until an expression triggers sending full rate data
    * - rms
      - A Fledge processing filter plugin that calculates RMS value for sensor data
    * - scale
      - A Fledge processing filter plugin that applies an offset and scale factor to the data
    * - scale-set
      - A Fledge processing filter plugin that applies a set of sale factors to the data
    * - threshold
      - A Fledge processing filter that only forwards data when a threshold is crossed


Notification Rule Plugins
-------------------------

Notification rule plugins provide the logic that is used by the
notification service to determine if a condition has been met that should
trigger or clear that condition and hence send a notification. A number of
notification plugins are available as standard, however as with any plugin the
user is able to write new plugins in Python or C/C++ to extend the set of
notification rules.

.. list-table:: Fledge Notification Rule Plugins
    :widths: 20 50
    :header-rows: 1

    * - Name
      - Description
    * - average
      - A Fledge notification rule plugin that evaluates an expression based sensor data notification rule plugin that triggers when sensors values depart from the moving average by more than a configured limit.
    * - outofbound
      - A Fledge notification rule plugin that triggers when sensors values exceed limits set in the configuration of the plugin.
    * - simple-expression
      - A Fledge notification rule plugin that evaluates an expression based sensor data


Notification Delivery Plugins
-----------------------------

Notification delivery plugins provide the mechanisms to deliver the
notification messages to the systems that will receive them.  A number
of notification delivery plugins are available as standard, however as
with any plugin the user is able to write new plugins in Python or C/C++
to extend the set of notification rules.

.. list-table:: Fledge Notification Delivery Plugins
    :widths: 20 50
    :header-rows: 1

    * - Name
      - Description
    * - alexa-notifyme
      - A Fledge notification delivery plugin that sends notifications to the Amazon Alexa platform
    * - asset
      - A Fledge notification delivery plugin that creates an asset in Fledge when a notification occurs
    * - blynk
      - A Fledge notification delivery plugin that sends notifications to the Blynk service
    * - email
      - A Fledge notification delivery plugin that sends notifications via email
    * - google-hangouts
      - A Fledge notification delivery plugin that sends alerts on the Google hangout platform
    * - ifttt
      - A Fledge notification delivery plugin that triggers an action of IFTTT
    * - python35
      - A Fledge notification delivery plugin that runs an arbitrary Python 3 script
    * - slack
      - A Fledge notification delivery plugin that sends notifications via the slack instant messaging platform
    * - telegram
      - A Fledge notification delivery plugin that sends notifications via the telegram service

