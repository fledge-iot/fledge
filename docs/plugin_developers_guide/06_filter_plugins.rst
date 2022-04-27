.. Filter Plugins

.. |br| raw:: html

   <br/>

.. Links
.. |expression filter| raw:: html

   <a href="../plugins/fledge-filter-expression/index.html">expression filter</a>

.. |Python 3.5 filter| raw:: html

   <a href="../plugins/fledge-filter-python35/index.html">Python 3.5 filter</a>

Filter Plugins
==============

Filter plugins provide a mechanism to alter the data stream as it flows
through a fledge instance, filters may be applied in south or north
micro-services and may form a pipeline of multiple processing elements
through which the data flows. Filters applied in a south service will only
process data that is received by the south service, whilst filters placed
in the north will process all data that flows out of that north interface.

Filters may;

  - augment data by adding static metadata or calculated values to the data

  - remove data from the stream

  - add data to the stream

  - modify data in the stream

It should be noted that there are some alternatives to creating a filter
if you wish to make simple changes to the data stream. There are a number of
existing filters that provide a degree of programmability. These include
the |expression filter| which allows an arbitrary mathematical formula
to be applied to the data or the |Python 3.5 filter| which allows a
small include Python script to be applied to the data.

Filter plugins may be written in C++ or Python and have a very simple interface. The plugin mechanism and a subset of the API is common between all types of plugins including filters.

Configuration
-------------

Filters use the same configuration mechanism as the rest of Fledge,
using a JSON document to describe the configuration parameters. As with
any other plugin the structure is defined by the plugin and retrieve
by the plugin_info entry point. This is then matched with the database
content to pass the configured values to the plugin_init entry point.

C++ Filter Plugin API
---------------------

The filter API consists of a small number of C function entry points,
these are called in a strict order and based on the same set of common
API entry points for all Fledge plugins.

Plugin Information
~~~~~~~~~~~~~~~~~~

The *plugin_info* entry point is the first entry point that is called
in a filter plugin and returns the plugin information structure. This is
the exact same call that every Fledge plugin must support and is used to
determine the type of the plugin and the configuration category defaults
for the plugin.

A typical implementation of *plugin_info* would merely return a pointer
to a static PLUGIN_INFORMATION structure.

.. code-block:: C


   PLUGIN_INFORMATION *plugin_info()
   {
        return &info;
   }

Plugin Initialise
~~~~~~~~~~~~~~~~~

The *plugin_init* entry point is called after *plugin_info* has been called and before any data is passed to the filter. It is called at the phase where the service is setting up the filter pipeline and provides the filter with its configuration category that now contains the user supplied values and the destination to which the filter will send the output of the filter.

.. code-block:: C

   PLUGIN_HANDLE plugin_init(ConfigCategory* config,
                          OUTPUT_HANDLE *outHandle,
                          OUTPUT_STREAM output)
   {
   }

The *config* parameter is the configuration category with the user supplied
values inserted, the *outHandle* is a handle for the next filter in the
chain and the *output* is a function pointer to call to send the data
to the next filter in the chain. The *outHandle* and *output* arguments
should be stored for future use in the *plugin_ingest* when data is to
be forwarded within the pipeline.

The *plugin_init* function returns a handle that will be passed to all
subsequent plugin calls. This handle can be used to store state that
needs to be passed between calls. Typically the *plugin_init* call will
create a C++ class that implements the filter and return a point to the
instance as the handle. The instance can then be used to store the state
of the filter, including the output handle and callback that needs to
be used.

Filter classes can also be used to buffer data between calls to the
*plugin_ingest* entry point, allowing a filter to defer the processing
of the data until it has a sufficient quantity of buffered data available
to it.

Plugin Ingest
~~~~~~~~~~~~~

The *plugin_ingest* entry point is the workhorse of the filter, it is
called with sets of readings to process and then passes on the new set
of readings to the next filter in the pipeline. The process of passing on
the data to the next filter is via the *OUTPUT_STREAM* function pointer. A
filter does not have to output data each time it ingests data, it is free
to output no data or to output more or less data than it was called with.

.. code-block:: C

   void plugin_ingest(PLUGIN_HANDLE *handle,
                   READINGSET *readingSet)
   {
   }

The number of readings that a filter is called with will depend on the
environment it is run in and what any filters earlier in the filter
pipeline have produced. A filter that requires a particular sample size
in order to process a result should therefore be prepared to buffer data
across multiple calls to *plugin_ingest*. Several examples of filters
that so this are available for reference.

The *plugin_ingest* call may send data onwards in the filter pipeline
by using the stored *output* and *outHandle* parameters passed to
*plugin_init*.

.. code-block:: C

    (*output)(outHandle, readings);

Plugin Reconfigure
~~~~~~~~~~~~~~~~~~

As with other plugin types the filter may be reconfigured during its
lifetime. When a reconfiguration operation occurs the *plugin_reconfigure*
method will be called with the new configuration for the filter.

.. code-block:: C

   void plugin_reconfigure(PLUGIN_HANDLE *handle, const std::string& newConfig)
   {
   }

Plugin Shutdown
~~~~~~~~~~~~~~~

As with other plugins a shutdown call exists which may be used by
the plugin to perform any cleanup that is required when the filter is
shut down.

.. code-block:: C

   void plugin_shutdown(PLUGIN_HANDLE *handle)
   {
   }

C++ Helper Class
~~~~~~~~~~~~~~~~

It is expected that filters will be written as C++ classes, with the
plugin handle being used a a mechanism to store and pass the pointer to
the instance of the filter class. In order to make it easier to write
filters a base *FledgeFilter* class has been provided, it is recommended
that you derive your specific filter class from this base class in order
to simplify the implementation

.. code-block:: C

    class FledgeFilter {
            public:
                    FledgeFilter(const std::string& filterName,
                                  ConfigCategory& filterConfig,
                                  OUTPUT_HANDLE *outHandle,
                                  OUTPUT_STREAM output);
                    ~FledgeFilter() {};
                    const std::string&
                                        getName() const { return m_name; };
                    bool		isEnabled() const { return m_enabled; };
                    ConfigCategory&     getConfig() { return m_config; };
                    void		disableFilter() { m_enabled = false; };
                    void		setConfig(const std::string& newConfig);
            public:
                    OUTPUT_HANDLE*	m_data;
                    OUTPUT_STREAM	m_func;
            protected:
                    std::string	        m_name;
                    ConfigCategory	m_config;
                    bool		m_enabled;
    };

C++ Filter Example
------------------

The following example is a simple data processing example. It applies the log() function to numeric data in the data stream

Plugin Interface
~~~~~~~~~~~~~~~~

Most plugins written in C++ have a source file that encapsulates the C API to the plugin, this is traditionally called plugin.cpp. The example plugin follows this model with the content of plugin.cpp shown below.

The first section includes the filter class that is the actual implementation of the filter logic and defines the JSON configuration category. This uses the *QUOTE* macro in order to make the JSON definition more readable.

.. code-block:: C

   /*
    * Fledge "log" filter plugin.
    *
    * Copyright (c) 2020 Dianomic Systems
    *
    * Released under the Apache 2.0 Licence
    *
    * Author: Mark Riddoch
    */

   #include <logFilter.h>
   #include <version.h>

   #define FILTER_NAME "log"
   const static char *default_config = QUOTE({
                   "plugin" : {
                           "description" : "Log filter plugin",
                           "type" : "string",
                           "default" : FILTER_NAME,
                           "readonly": "true"
                           },
                    "enable": {
                           "description": "A switch that can be used to enable or disable execution of the log filter.", 
                           "type": "boolean",
                           "displayName": "Enabled",
                           "default": "false"
                           },
                   "match" : {
                           "description" : "An optional regular expression to match in the asset name.",
                           "type": "string",
                           "default": "",
                           "order": "1",
                           "displayName": "Asset filter"}
                   });

   using namespace std;

We then define the plugin information contents that will be returned by the *plugin_info* call.

.. code-block:: C

   /**
    * The Filter plugin interface
    */
   extern "C" {

   /**
    * The plugin information structure
    */
   static PLUGIN_INFORMATION info = {
           FILTER_NAME,              // Name
           VERSION,                  // Version
           0,                        // Flags
           PLUGIN_TYPE_FILTER,       // Type
           "1.0.0",                  // Interface version
           default_config	          // Default plugin configuration
   };

The final section of this file consists of the entry points themselves
and the implementation. The majority of this consist of calls to the
LogFilter class that in this case implements the logic of the filter.

.. code-block:: C

   /**
    * Return the information about this plugin
    */
   PLUGIN_INFORMATION *plugin_info()
   {
           return &info;
   }

   /**
    * Initialise the plugin, called to get the plugin handle.
    * We merely create an instance of our LogFilter class
    *
    * @param config	The configuration category for the filter
    * @param outHandle	A handle that will be passed to the output stream
    * @param output	The output stream (function pointer) to which data is passed
    * @return		An opaque handle that is used in all subsequent calls to the plugin
    */
   PLUGIN_HANDLE plugin_init(ConfigCategory* config,
                             OUTPUT_HANDLE *outHandle,
                             OUTPUT_STREAM output)
   {
           LogFilter *log = new LogFilter(FILTER_NAME,
                                           *config,
                                           outHandle,
                                           output);

           return (PLUGIN_HANDLE)log;
   }

   /**
    * Ingest a set of readings into the plugin for processing
    *
    * @param handle	The plugin handle returned from plugin_init
    * @param readingSet	The readings to process
    */
   void plugin_ingest(PLUGIN_HANDLE *handle,
                      READINGSET *readingSet)
   {
           LogFilter *log = (LogFilter *) handle;
           log->ingest(readingSet);
   }

   /**
    * Plugin reconfiguration method
    *
    * @param handle	The plugin handle
    * @param newConfig	The updated configuration
    */
   void plugin_reconfigure(PLUGIN_HANDLE *handle, const std::string& newConfig)
   {
           LogFilter *log = (LogFilter *)handle;
           log->reconfigure(newConfig);
   }

   /**
    * Call the shutdown method in the plugin
    */
   void plugin_shutdown(PLUGIN_HANDLE *handle)
   {
           LogFilter *log = (LogFilter *) handle;
           delete log;
   }

   // End of extern "C"
   };

Filter Class
~~~~~~~~~~~~

Although it is not mandatory it is good practice to encapsulate the filter login in a class, these classes are derived from the FledgeFilter class

.. code-block:: C

   #ifndef _LOG_FILTER_H
   #define _LOG_FILTER_H
   /*
    * Fledge "Log" filter plugin.
    *
    * Copyright (c) 2020 Dianomic Systems
    *
    * Released under the Apache 2.0 Licence
    *
    * Author: Mark Riddoch           
    */     
   #include <filter.h>               
   #include <reading_set.h>
   #include <config_category.h>
   #include <string>                 
   #include <logger.h>
   #include <mutex>
   #include <regex>
   #include <math.h>


   /**
    * Convert the incoming data to use a logarithmic scale
    */
   class LogFilter : public FledgeFilter {
           public:
                   LogFilter(const std::string& filterName,
                           ConfigCategory& filterConfig,
                           OUTPUT_HANDLE *outHandle,
                           OUTPUT_STREAM output);
                   ~LogFilter();
                   void	ingest(READINGSET *readingSet);
                   void	reconfigure(const std::string& newConfig);
           private:
                   void				handleConfig(ConfigCategory& config);
                   std::string			m_match;
                   std::regex			*m_regex;
                   std::mutex			m_configMutex;
   };


   #endif

Filter Class Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following is the code that implements the filter logic

.. code-block:: C

   /*
    * Fledge "Log" filter plugin.
    *
    * Copyright (c) 2020 Dianomic Systems
    *
    * Released under the Apache 2.0 Licence
    *
    * Author: Mark Riddoch           
    */     
   #include <logFilter.h>               

   using namespace std;

   /**
    * Constructor for the LogFilter.
    *
    * We call the constructor of the base class and handle the initial
    * configuration of the filter.
    *
    * @param	filterName      The name of the filter
    * @param	filterConfig    The configuration category for this filter
    * @param	outHandle       The handle of the next filter in the chain
    * @param	output          A function pointer to call to output data to the next filter
    */
   LogFilter::LogFilter(const std::string& filterName,
                           ConfigCategory& filterConfig,
                           OUTPUT_HANDLE *outHandle,
                           OUTPUT_STREAM output) : m_regex(NULL),
                                   FledgeFilter(filterName, filterConfig, outHandle, output)
   {
           handleConfig(filterConfig);
   }

   /**
    * Destructor for this filter class
    */
   LogFilter::~LogFilter()
   {
           if (m_regex)
                   delete m_regex;
   }

   /**
    * The actual filtering code
    *
    * @param readingSet	The reading data to filter
    */
   void
   LogFilter::ingest(READINGSET *readingSet)
   {
           lock_guard<mutex> guard(m_configMutex);

           if (isEnabled())	// Filter enable, process the readings
           {
                   const vector<Reading *>& readings = ((ReadingSet *)readingSet)->getAllReadings();
                   for (vector<Reading *>::const_iterator elem = readings.begin();
                                   elem != readings.end(); ++elem)
                   {
                           // If we set a matching regex then compare to the name of this asset
                           if (!m_match.empty())
                           {
                                   string asset = (*elem)->getAssetName();
                                   if (!regex_match(asset, *m_regex))
                                   {
                                           continue;
                                   }
                           }

                           // We are modifying this asset so put an entry in the asset tracker
                           AssetTracker::getAssetTracker()->addAssetTrackingTuple(getName(), (*elem)->getAssetName(), string("Filter"));

                           // Get a reading DataPoints
                           const vector<Datapoint *>& dataPoints = (*elem)->getReadingData();

                           // Iterate over the datapoints
                           for (vector<Datapoint *>::const_iterator it = dataPoints.begin(); it != dataPoints.end(); ++it)
                           {
                                   // Get the reference to a DataPointValue
                                   DatapointValue& value = (*it)->getData();

                                   /*
                                    * Deal with the T_INTEGER and T_FLOAT types.
                                    * Try to preserve the type if possible but
                                    * if a floating point log function is applied
                                    * then T_INTEGER values will turn into T_FLOAT.
                                    * If the value is zero we do not apply the log function
                                    */
                                   if (value.getType() == DatapointValue::T_INTEGER)
                                   {
                                           long ival = value.toInt();
                                           if (ival != 0)
                                           {
                                                   double newValue = log((double)ival);
                                                   value.setValue(newValue);
                                           }
                                   }
                                   else if (value.getType() == DatapointValue::T_FLOAT)
                                   {
                                           double dval = value.toDouble();
                                           if (dval != 0.0)
                                           {
                                                   value.setValue(log(dval));
                                           }
                                   }
                                   else
                                   {
                                           // do nothing for other types
                                   }
                           }
                   }
           }

           // Pass on all readings in this case
           (*m_func)(m_data, readingSet);
   }

   /**
    * Reconfiguration entry point to the filter.
    *
    * This method runs holding the configMutex to prevent
    * ingest using the regex class that may be destroyed by this
    * call.
    *
    * Pass the configuration to the base FilterPlugin class and
    * then call the private method to handle the filter specific 
    * configuration.
    *
    * @param newConfig	The JSON of the new configuration
    */
   void
   LogFilter::reconfigure(const std::string& newConfig)
   {
           lock_guard<mutex> guard(m_configMutex);
           setConfig(newConfig);		// Pass the configuration to the base class
           handleConfig(m_config);
   }

   /**
    * Handle the filter specific configuration. In this case
    * it is just the single item "match" that is a regex
    * expression
    *
    * @param config	The configuration category
    */
   void
   LogFilter::handleConfig(ConfigCategory& config)
   {
           if (config.itemExists("match"))
           {
                   m_match = config.getValue("match");
                   if (m_regex)
                           delete m_regex;
                   m_regex = new regex(m_match);
           }
   }

Python Filter API
-----------------

Filters may also be written in Python, the API is very similar to that of a C++ filter and consists of the same set of entry points.

Plugin Information
~~~~~~~~~~~~~~~~~~

As with C++ filters this is the first entry point called, it returns a Python dictionary that describes the filter.

.. code-block:: python

   def plugin_info():
       """ Returns information about the plugin
       Args:
       Returns:
           dict: plugin information
       Raises:
       """

Plugin Initialisation
~~~~~~~~~~~~~~~~~~~~~

The *plugin_init* call is used to pass the resolved configuration to the
plugin and also pass in the handle of the next filter in the pipeline
and a callback that should be called with the output data of the filter.

.. code-block:: python

  def plugin_init(config, ingest_ref, callback):
      """ Initialise the plugin
      Args:
          config: JSON configuration document for the Filter plugin configuration category
          ingest_ref: filter ingest reference
          callback: filter callback
      Returns:
          data: JSON object to be used in future calls to the plugin
      Raises:
      """

Plugin Ingestion
~~~~~~~~~~~~~~~~

The *plugin_ingest* method is used to pass data into the plugin, the plugin will then process that data and call the callback that was passed into the *plugin_init* entry point with the *ingest_ref* handle and the data to send along the filter pipeline.

.. code-block:: python

   def plugin_ingest(handle, data):
       """ Modify readings data and pass it onward

       Args:
           handle: handle returned by the plugin initialisation call
           data: readings data
       """

The *data* is arranged as an array of Python dictionaries, each of which is a *Reading*. Typically the data can be processed by traversing the array

.. code-block:: python

   for elem in data:
       process(elem)

Plugin Reconfigure
~~~~~~~~~~~~~~~~~~

The *plugin_reconfigure* entry point is called whenever a configuration change occurs for the filters configuration category.

.. code-block:: python

   def plugin_reconfigure(handle, new_config):
       """ Reconfigures the plugin

       Args:
           handle: handle returned by the plugin initialisation call
           new_config: JSON object representing the new configuration category for the category
       Returns:
           new_handle: new handle to be used in the future calls
       """

Plugin Shutdown
~~~~~~~~~~~~~~~

Called when the plugin is to be shutdown to allow it to perform any cleanup operations.

.. code-block:: python

   def plugin_shutdown(handle):
       """ Shutdowns the plugin doing required cleanup.

       Args:
           handle: handle returned by the plugin initialisation call
       Returns:
           plugin shutdown
       """

Python Filter Example
---------------------

The following is an example of a Python filter that calculates an exponential moving average.

.. code-block:: python


   # -*- coding: utf-8 -*-

   # Fledge_BEGIN
   # See: http://fledge-iot.readthedocs.io/
   # Fledge_END

   """ Module for EMA filter plugin

   Generate Exponential Moving Average
   The rate value (x) allows to include x% of current value
   and (100-x)% of history
   A datapoint called 'ema' is added to each reading being filtered
   """

   import time
   import copy
   import logging

   from fledge.common import logger
   import filter_ingest

   __author__ = "Massimiliano Pinto"
   __copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
   __license__ = "Apache 2.0"
   __version__ = "${VERSION}"

   _LOGGER = logger.setup(__name__, level = logging.INFO)

   PLUGIN_NAME = 'ema'

   _DEFAULT_CONFIG = {
       'plugin': {
           'description': 'Exponential Moving Average filter plugin',
           'type': 'string',
           'default': PLUGIN_NAME,
           'readonly': 'true'
       },
       'enable': {
           'description': 'Enable ema plugin',
           'type': 'boolean',
           'default': 'false',
           'displayName': 'Enabled',
           'order': "3"
       },
       'rate': {
           'description': 'Rate value: include % of current value',
           'type': 'float',
           'default': '0.07',
           'displayName': 'Rate',
           'order': "2"
       },
       'datapoint': {
           'description': 'Datapoint name for calculated ema value',
           'type': 'string',
           'default': PLUGIN_NAME,
           'displayName': 'EMA datapoint',
           'order': "1"
       }
   }


   def compute_ema(handle, reading):
       """ Compute EMA

       Args:
           A reading data
       """
       rate = float(handle['rate']['value'])
       for attribute in list(reading):
           if not handle['latest']:
               handle['latest'] = reading[attribute]
       handle['latest'] = reading[attribute] * rate + handle['latest'] * (1 - rate)
       reading[handle['datapoint']['value']] = handle['latest']


   def plugin_info():
       """ Returns information about the plugin
       Args:
       Returns:
           dict: plugin information
       Raises:
       """
       return {
           'name': PLUGIN_NAME,
           'version': '1.9.2',
           'mode': 'none',
           'type': 'filter',
           'interface': '1.0',
           'config': _DEFAULT_CONFIG
       }


   def plugin_init(config, ingest_ref, callback):
       """ Initialise the plugin
       Args:
           config: JSON configuration document for the Filter plugin configuration category
           ingest_ref: filter ingest reference
           callback: filter callback
       Returns:
           data: JSON object to be used in future calls to the plugin
       Raises:
       """
       _config = copy.deepcopy(config)
       _config['ingestRef'] = ingest_ref
       _config['callback'] = callback
       _config['latest'] = None
       _config['shutdownInProgress'] = False
       return _config


   def plugin_reconfigure(handle, new_config):
       """ Reconfigures the plugin

       Args:
           handle: handle returned by the plugin initialisation call
           new_config: JSON object representing the new configuration category for the category
       Returns:
           new_handle: new handle to be used in the future calls
       """
       _LOGGER.info("Old config for ema plugin {} \n new config {}".format(handle, new_config))

       new_handle = copy.deepcopy(new_config)
       new_handle['shutdownInProgress'] = False
       new_handle['latest'] = None
       new_handle['ingestRef'] = handle['ingestRef']
       new_handle['callback'] = handle['callback']
       return new_handle


   def plugin_shutdown(handle):
       """ Shutdowns the plugin doing required cleanup.

       Args:
           handle: handle returned by the plugin initialisation call
       Returns:
           plugin shutdown
       """
       handle['shutdownInProgress'] = True
       time.sleep(1)
       handle['callback'] = None
       handle['ingestRef'] = None
       handle['latest'] = None

       _LOGGER.info('{} filter plugin shutdown.'.format(PLUGIN_NAME))


   def plugin_ingest(handle, data):
       """ Modify readings data and pass it onward

       Args:
           handle: handle returned by the plugin initialisation call
           data: readings data
       """
       if handle['shutdownInProgress']:
           return

       if handle['enable']['value'] == 'false':
           # Filter not enabled, just pass data onwards
           filter_ingest.filter_ingest_callback(handle['callback'], handle['ingestRef'], data)
           return

       # Filter is enabled: compute EMA for each reading
       for elem in data:
           compute_ema(handle, elem['readings'])

       # Pass data onwards
       filter_ingest.filter_ingest_callback(handle['callback'], handle['ingestRef'], data)

       _LOGGER.debug("{} filter_ingest done.".format(PLUGIN_NAME))

