.. Rules Plugins

.. |br| raw:: html

   <br/>

.. Links
.. |average| raw:: html

   <a href="../plugins/fledge-rule-Average/index.html">Moving Average Rule plugin</a>

.. |code| raw:: html

   <a href="https://github.com/fledge-iot/fledge-rule-average.git">Moving Average Rule source code</a>


Notification Rule Plugins
=========================

Notification rule  plugins are used by the notification system to
evaluate a rule and trigger a notification based on the result of
that evaluation. They are where the decisions are made that results
in event notification to other systems or devices.

Notification rule plugins may be written in C or C++ and have a very
simple interface. The plugin mechanism and a subset of the API is common
between all types of plugins including notification rules.  This documentation
is based on the |code|. The |average| calculates a moving average of the values
sent to the notification instance and will trigger the notification to be sent
when the value of a datapoint varies from the calculated average by more than
a specified percentage.

Configuration
-------------

Notification Rule  plugins use the same configuration mechanism as the rest of
Fledge, using a JSON document to describe the configuration parameters. In
common with all other plugins the structure is defined by the plugin and retrieved
via the *plugin_info* entry point. This is then merged with the database
content to pass the configured values to the *plugin_init* entry point.

Notification Rule Plugin API
----------------------------

The notification rule plugin API consists of a small number of C
function entry points, these are called in a strict order and based on
the same set of common API entry points for all Fledge plugins.

Plugin Information
~~~~~~~~~~~~~~~~~~

The *plugin_info* entry point is the first entry point that is called
in a notification rule plugin and returns the plugin information
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
           AverageRule *average = new AverageRule(config);
           average->configure(config);
           return (PLUGIN_HANDLE)average;
   }


The *config* parameter is the configuration category with the user supplied
values inserted, these values are used to configure the behavior of the
plugin. In the case of our moving average example we use this to construct
an instance of our AverageRule class and then call the configure method of that
newly constructed instance of the class.

.. code-block:: C

    /**
     * Average rule constructor
     *      
     * Call parent class BuiltinRule constructor
     */     
    AverageRule::AverageRule() : BuiltinRule()
    {       
    }

.. note::

    We call the base class *BuiltinRule* as part of the construction of a
    notification rule. This does some common initialisation required for all
    notification rules.

The *configure* method for our AverageRule class is shown below.

.. code-block:: C

    /**
     * Configure the rule plugin
     *
     * @param    config     The configuration object to process
     */
    void AverageRule::configure(const ConfigCategory& config)
    {
            // Remove current triggers
            // Configuration change is protected by a lock
            lockConfig();
            if (hasTriggers())
            {
                    removeTriggers();
            }
            // Release lock
            unlockConfig();

            string assetName = config.getValue("asset");
            if (!assetName.empty())
            {
                    addTrigger(assetName, NULL);
            }
            m_source = config.getValue("source");

            m_deviation = strtol(config.getValue("deviation").c_str(), NULL, 10);
            m_direction = config.getValue("direction");
            string aveType = config.getValue("averageType");
            if (aveType.compare("Simple Moving Average") == 0)
            {
                    m_aveType = SMA;
            }
            else
            {
                    m_aveType = EMA;
            }
            m_factor = strtol(config.getValue("factor").c_str(), NULL, 10);
            for (auto it = m_averages.begin(); it != m_averages.end(); it++)
            {
                    it->second->setAverageType(m_aveType, m_factor);
            }
    }

We return the pointer to our AverageRule class as the handle for the plugin. This
allows subsequent calls to the plugin to reference the instance created
by the *plugin_init* call.

Plugin Triggers
~~~~~~~~~~~~~~~

This is the API call made by the notification service to determine the data it needs to send to the plugin for the purposes of evaluating the rule. Typically the notification rule configuration will include the data it requires to execute the evaluation of the rule.

The return from the *plugin_triggers* API call is a string that contains a JSON document. This document include the type and name of the data to be sent to the evaluation entry point of the plugin. The table below lists the valid trigger types and the data associated with each.

..  list-table::
    :widths: 15 55 30
    :header-rows: 1

    * - Key
      - Description
      - Example
    * - asset
      - Readings for the specified asset. The value of the *asset* key is the name of the asset
      - { "triggers" : [ { "asset" : "sinusoid" } ] }
    * - statistic
      - The cumulative statistics counter.
      - { "triggers" : [ { "statistic" : "Sine-Ingest" } ] }
    * - statisticRate
      - The delta of the statistics counter for the statistic history period. By default this will be the increase in the statistic for a 15 second time interval.
      - { "triggers" : [ { "statisticRate" : "Sine-Ingest" } ] }
    * - audit
      - The audit log code of the audit log events sent to the evaluate entry point. In this example we use the service failed audit log code.
      - { "triggers" : [ { "audit" : "SRVFL" } ] }
    * - interval
      - The interval between which calls are made to the evaluate entry point. The *interval* type takes an additional *evaluate* parameter that determines if evaluation is called if any data arrives or only if the interval expires.
      - { "triggers" : [ { "interval" : 500, "evaluate" "any" } ] }


Multiple trigger source may be combined, to request that the evaluate entry point be called at a particular interval and for a particular asset, the document below would be returned.

.. code-block:: JSON

   {
       "triggers" : [
           { "asset" : "status" },
           { "interval" : 1000, "evaluate" : "any" }
           ]
   }

The above will cause the *plugin_eval* call to be called if the interval expires or if any readings for the asset *status* arrive. The alternate below will only be called at the defined interval. The data will still contain the buffered readings of the asset *status*, but will call *plugin_eval* every 1000 milliseconds.

.. code-block:: JSON

   {
       "triggers" : [
           { "asset" : "status" },
           { "interval" : 1000, "evaluate" : "interval" }
           ]
   }

The code for the Moving Average rule plugin's *plugin_trigger* entry point is shown below.

.. code-block:: C

    /**
     * Return triggers JSON document
     *
     * @return	JSON string
     */
    string plugin_triggers(PLUGIN_HANDLE handle)
    {
            string ret;
            AverageRule *rule = (AverageRule *)handle;

            if (!rule)
            {
                    ret = "{\"triggers\" : []}";
                    return ret;
            }

            // Configuration fetch is protected by a lock
            rule->lockConfig();

            if (!rule->hasTriggers())
            {
                    rule->unlockConfig();
                    ret = "{\"triggers\" : []}";
                    return ret;
            }

            ret = "{\"triggers\" : [ ";
            std::map<std::string, RuleTrigger *> triggers = rule->getTriggers();
            for (auto it = triggers.begin();
                      it != triggers.end();
                      ++it)
            {
                    string source = rule->getSource();
                    if (source.compare("Readings") == 0)
                            ret += "{ \"asset\"  : \"" + (*it).first + "\"";
                    else if (source.compare("Statistics") == 0)
                            ret += "{ \"statistic\"  : \"" + (*it).first + "\"";
                    else if (source.compare("Statistics History") == 0)
                            ret += "{ \"statisticRate\"  : \"" + (*it).first + "\"";
                    else
                    {
                            ret += "{ ";	// Keep JSON valid
                            Logger::getLogger()->error("Unsupported data source %s, rule will not subscribe to any data", source.c_str());
                    }
                    ret += " }";
                    
                    if (std::next(it, 1) != triggers.end())
                    {
                            ret += ", ";
                    }
            }

            ret += " ] }";

            // Release lock
            rule->unlockConfig();

            return ret;
    }

Plugin Evaluation
~~~~~~~~~~~~~~~~~

The *plugin_eval* API entry point is called with the plugin handle and the data, as a string, which holds the values to be evaluated. The return value of this call is a boolean that is the result of the evaluation. A value of true is returned if conditions the conditions of the rule are met. Otherwise the entry point will return false.

Below is the code for the Moving Average plugin.

.. code-block:: C

    /**
     * Evaluate notification data received
     *
     * @param    assetValues	JSON string document
     *				with notification data.
     * @return			True if the rule was triggered,
     *				false otherwise.
     */
    bool plugin_eval(PLUGIN_HANDLE handle,
                     const string& assetValues)
    {
            Document doc;
            doc.Parse(assetValues.c_str());
            if (doc.HasParseError())
            {
                    return false;
            }

            bool eval = false; 
            AverageRule *rule = (AverageRule *)handle;
            map<std::string, RuleTrigger *>& triggers = rule->getTriggers();

            // Iterate through all configured assets
            // If we have multiple asset the evaluation result is
            // TRUE only if all assets checks returned true
            for (auto t = triggers.begin(); t != triggers.end(); ++t)
            {
                    string assetName = t->first;
                    string assetTimestamp = "timestamp_" + assetName;
                    if (doc.HasMember(assetName.c_str()))
                    {
                            // Get all datapoints for assetName
                            const Value& assetValue = doc[assetName.c_str()];

                            for (Value::ConstMemberIterator itr = assetValue.MemberBegin();
                                                itr != assetValue.MemberEnd(); ++itr)
                            {
                                    if (itr->value.IsInt64())
                                    {
                                            eval |= rule->evaluate(assetName, itr->name.GetString(), (long)itr->value.GetInt64());
                                    }
                                    else if (itr->value.IsDouble())
                                    {
                                            eval |= rule->evaluate(assetName, itr->name.GetString(), itr->value.GetDouble());
                                    }
                            }
                            // Add evaluation timestamp
                            if (doc.HasMember(assetTimestamp.c_str()))
                            {
                                    const Value& assetTime = doc[assetTimestamp.c_str()];
                                    double timestamp = assetTime.GetDouble();
                                    rule->setEvalTimestamp(timestamp);
                            }
                    }
            }

            // Set final state: true is any calls to evaluate() returned true
            rule->setState(eval);

            return eval;
    }

In this case the code iterates through the trigger names and calls the *evaluate* method in the *AverageRule* class for each trigger and with each value in the incoming data stream.

Various calls are made that will set the state of the evaluation, namely the *setValTimestamp* and *setState*. These states may later be used in the *plugin_reason* API.

Plugin Reason
~~~~~~~~~~~~~

The *plugin_reason* API call is made to the rule plugin by the notification service when it needs to send a notification. Depending on the result of the last *plugin_evaluate* call this may a notification of the condition either triggering or clearing. The code for the Moving Average plugin is shown below.

.. code-block:: C

    /**
     * Return rule trigger reason: trigger or clear the notification. 
     *
     * @return	 A JSON string
     */
    string plugin_reason(PLUGIN_HANDLE handle)
    {
            AverageRule* rule = (AverageRule *)handle;
            BuiltinRule::TriggerInfo info;
            rule->getFullState(info);

            string ret = "{ \"reason\": \"";
            ret += info.getState() == BuiltinRule::StateTriggered ? "triggered" : "cleared";
            ret += "\"";
            ret += ", \"asset\": " + info.getAssets();
            if (rule->getEvalTimestamp())
            {
                    ret += string(", \"timestamp\": \"") + info.getUTCTimestamp() + string("\"");
            }
            ret += " }";

            return ret;
    }

The code first fetches the state information that was set by the previous *plugin_eval* call, using the *getFullState()* entry point of the base *BuiltinRule* class.

The *plugin_reason* call returns a JSON document, within a string. The reason document returns why the notification is being sent, the name of the item that triggered the notification and the timestamp of the data that triggered the notification. Below is a example reason document.

.. code-block:: JSON

   {
       "reason" : "triggered",
       "asset" : "sinusoid",
       "timestamp" : "2025/03/16 12:33:04.026"
   }

.. note::

   The data that triggered the notification is always passed with a key of *asset*, but it may be an asset in a reading, a statistic name or an audit log code.

Plugin Reconfigure
~~~~~~~~~~~~~~~~~~

As with other plugin types the notification delivery plugin  may be
reconfigured during its lifetime. When a reconfiguration operation occurs
the *plugin_reconfigure* method will be called with the new configuration
for the plugin.

.. code-block:: C

   void plugin_reconfigure(PLUGIN_HANDLE *handle, const std::string& newConfig)
   {
        AverageRule *average = (AverageRule *)handle;
        average->configure(newConfig);
        return;
   }

In the case of the Moving Average plugin this calls the same *configure* method that was called by the *plugin_init* entry point during initialisation and is shown above.

Plugin Shutdown
~~~~~~~~~~~~~~~

In common with all Fledge plugins a shutdown call exists which is used by
the plugin to perform any cleanup that is required when the plugin is
shut down.

.. code-block:: C

   void plugin_shutdown(PLUGIN_HANDLE *handle)
   {
        AverageRule *average = (AverageRule *)handle;
        delete average;
   }

In the case of our Moving Average example we merely destroy the instance of the
AverageRule class and allow the destructor of that class to do any cleanup that
is required.
