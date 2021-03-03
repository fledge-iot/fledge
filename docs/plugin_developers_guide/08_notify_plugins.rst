.. Filter Plugins

.. |br| raw:: html

   <br/>

.. Links
.. |mqtt| raw:: html

   <a href="../plugins/fledge-notify-mqtt/index.html">MQTT delivery plugin</a>

.. |code| raw:: html

   <a href="https://github.com/fledge-iot/fledge-notify-mqtt.git">MQTT notification delivery source code</a>

Notification Delivery Plugins
=============================

Notification delivery plugins are used by the notification system to
send a notification to some other system or device. They are the transport
that allows the event to be notified to that other system or device.


Notification delivery plugins may be written in C or C++ and have a very
simple interface. The plugin mechanism and a subset of the API is common
between all types of plugins including filters. This documentation is based
on the |code|. The |mqtt| sends MQTT messages to a configurable MQTT topic
when a notification is triggered and cleared.

Configuration
-------------

Notification Delivery plugins use the same configuration mechanism as the rest of
Fledge, using a JSON document to describe the configuration parameters. As
with any other plugin the structure is defined by the plugin and retrieve
by the *plugin_info* entry point. This is then matched with the database
content to pass the configured values to the *plugin_init* entry point.

Notification Delivery Plugin API
---------------------------------

The notification delivery plugin API consists of a small number of C
function entry points, these are called in a strict order and based on
the same set of common API entry points for all Fledge plugins.

Plugin Information
~~~~~~~~~~~~~~~~~~

The *plugin_info* entry point is the first entry point that is called
in a notification delivery plugin and returns the plugin information
structure. This is the exact same call that every Fledge plugin
must support and is used to determine the type of the plugin and the
configuration category defaults for the plugin.

A typical implementation of *plugin_info* would merely return a pointer
to a static PLUGIN_INFORMATION structure.

.. code-block:: C


   PLUGIN_INFORMATION *plugin_info()
   {
        return &info;
   }

Plugin Initialise
~~~~~~~~~~~~~~~~~

The second call that is made to the plugin is the *plugin_init* call, that is used to retrieve a handle on the plugin instance and to configure the plugin.

.. code-block:: C

   PLUGIN_HANDLE plugin_init(ConfigCategory* config)
   {
           MQTT *mqtt = new MQTT(config);
           return (PLUGIN_HANDLE)mqtt;
   }


The *config* parameter is the configuration category with the user supplied
values inserted, these values are used to configure the behavior of the
plugin. In the case of our MQTT example we use this to call the constructor
of our MQTT class.

.. code-block:: C

   /**
    * Construct a MQTT notification plugin
    *
    * @param category	The configuration of the plugin
    */
   MQTT::MQTT(ConfigCategory *category)
   {
           if (category->itemExists("broker"))
                   m_broker = category->getValue("broker");
           if (category->itemExists("topic"))
                   m_topic = category->getValue("topic");
           if (category->itemExists("trigger_payload"))
                   m_trigger = category->getValue("trigger_payload");
           if (category->itemExists("clear_payload"))
                   m_clear = category->getValue("clear_payload");
   }

This constructor merely stores values out of the configuration category
as private member variables of the MQTT class.

We return the pointer to our MQTT class as the handle for the plugin. This
allows subsequent calls to the plugin to reference the instance created
by the *plugin_init* call.

Plugin Delivery
~~~~~~~~~~~~~~~

This is the API call made whenever the plugin needs to send a triggered or cleared notification state. It may be called multiple times within the lifetime of a plugin.

.. code-block:: C

   bool plugin_deliver(PLUGIN_HANDLE handle,
                       const std::string& deliveryName,
                       const std::string& notificationName,
                       const std::string& triggerReason,
                       const std::string& message)
   {
           MQTT *mqtt = (MQTT *)handle;
           return mqtt->notify(notificationName, triggerReason, message);
   }

The delivery call is passed the handle, which gives us the MQTT class
instance on this case, the name of the notification, a trigger reason,
which is a JSON document and a message. The trigger reason JSON document
contains information about why the delivery call was made, including the
triggered or cleared status, the timestamp of the reading that caused
the notification to trigger and the name of the asset or assets involved
in the notification rule that triggered this delivery event.

.. code-block:: JSON

   {
       "reason": "triggered",
       "asset": ["sinusoid"],
       "timestamp": "2020-11-18 11:52:33.960530+00:00"
   }

The return from the *plugin_deliver* entry point is a boolean that
indicates if the delivery succeeded or not.

In the case of our MQTT example we call the notify method of the class,
this then interacts with the MQTT broker.

.. code-block:: C

   /**
    * Send a notification via MQTT broker
    *
    * @param notificationName 	The name of this notification
    * @param triggerReason		Why the notification is being sent
    * @param message		The message to send
    */
   bool MQTT::notify(const string& notificationName, const string& triggerReason, const string& message)
   {
   string 		payload = m_trigger;
   MQTTClient	client;

           lock_guard<mutex> guard(m_mutex);

           // Parse the JSON that represents the reason data
           Document doc;
           doc.Parse(triggerReason.c_str());
           if (!doc.HasParseError() && doc.HasMember("reason"))
           {
                   if (!strcmp(doc["reason"].GetString(), "cleared"))
                           payload = m_clear;
           }

           // Connect to the MQTT broker
           MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
           MQTTClient_message pubmsg = MQTTClient_message_initializer;
           MQTTClient_deliveryToken token;
           int rc;

           if ((rc = MQTTClient_create(&client, m_broker.c_str(), CLIENTID,
                   MQTTCLIENT_PERSISTENCE_NONE, NULL)) != MQTTCLIENT_SUCCESS)
           {
                   Logger::getLogger()->error("Failed to create client, return code %d\n", rc);
                   return false;
           }

           conn_opts.keepAliveInterval = 20;
           conn_opts.cleansession = 1;
           if ((rc = MQTTClient_connect(client, &conn_opts)) != MQTTCLIENT_SUCCESS)
           {
                   Logger::getLogger()->error("Failed to connect, return code %d\n", rc);
                   return false;
           }

           // Construct the payload
           pubmsg.payload = (void *)payload.c_str();
           pubmsg.payloadlen = payload.length();
           pubmsg.qos = 1;
           pubmsg.retained = 0;

           // Publish the message
           if ((rc = MQTTClient_publishMessage(client, m_topic.c_str(), &pubmsg, &token)) != MQTTCLIENT_SUCCESS)
           {
                   Logger::getLogger()->error("Failed to publish message, return code %d\n", rc);
                   return false;
           }

           // Wait for completion and disconnect
           rc = MQTTClient_waitForCompletion(client, token, TIMEOUT);
           if ((rc = MQTTClient_disconnect(client, 10000)) != MQTTCLIENT_SUCCESS)
                   Logger::getLogger()->error("Failed to disconnect, return code %d\n", rc);
           MQTTClient_destroy(&client);
           return true;
   }

Plugin Reconfigure
~~~~~~~~~~~~~~~~~~

As with other plugin types the notification delivery plugin  may be
reconfigured during its lifetime. When a reconfiguration operation occurs
the *plugin_reconfigure* method will be called with the new configuration
for the plugin.

.. code-block:: C

   void plugin_reconfigure(PLUGIN_HANDLE *handle, const std::string& newConfig)
   {
        MQTT *mqtt = (MQTT *)handle;
        mqtt->reconfigure(newConfig);
        return;
   }

In the case of our MQTT example we call the reconfigure method of our
MQTT class. In this method the new values are copied into the local
member variables of the instance.

.. code-block:: C

   /**
    * Reconfigure the MQTT delivery plugin
    *
    * @param newConfig	The new configuration
    */
   void MQTT::reconfigure(const string& newConfig)
   {
           ConfigCategory category("new", newConfig);
           lock_guard<mutex> guard(m_mutex);
           m_broker = category.getValue("broker");
           m_topic = category.getValue("topic");
           m_trigger = category.getValue("trigger_payload");
           m_clear = category.getValue("clear_payload");
   }

The mutex is used here to prevent the plugin reconfiguration occurring
when we are delivering a notification. The same mutex is held in the
notify method of the MQTT class.

Plugin Shutdown
~~~~~~~~~~~~~~~

As with other plugins a shutdown call exists which may be used by
the plugin to perform any cleanup that is required when the plugin is
shut down.

.. code-block:: C

   void plugin_shutdown(PLUGIN_HANDLE *handle)
   {
        MQTT *mqtt = (MQTT *)handle;
        delete mqtt;
   }

In the case of our MQTT example we merely destroy the instance of the
MQTT class and allow the destructor of that class to do any cleanup that
is required. In the case of this example there is no cleanup required.
