/*
 * Fledge plugin filter class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <filter_plugin.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

#define JSON_CONFIG_FILTER_ELEM "filter"
#define JSON_CONFIG_PIPELINE_ELEM "pipeline"

using namespace std;

/**
 * FilterPlugin class constructor
 *
 * This class wraps the filter plugin C interface and creates
 * set of function pointers that resolve to the loaded plugin and
 * enclose in the class.
 *
 * @param name		The filter name
 * @param handle	The loaded plugin handle
 *
 * Set the function pointers to Filter Plugin C API
 */
FilterPlugin::FilterPlugin(const std::string& name,
			   PLUGIN_HANDLE handle) : Plugin(handle), m_name(name)
{
	// Setup the function pointers to the plugin
	pluginInit = (PLUGIN_HANDLE (*)(const ConfigCategory *,
					OUTPUT_HANDLE *,
					OUTPUT_STREAM output))
					manager->resolveSymbol(handle,
							       "plugin_init");
  	pluginShutdownPtr = (void (*)(PLUGIN_HANDLE))
				      manager->resolveSymbol(handle,
							     "plugin_shutdown");
  	pluginIngestPtr = (void (*)(PLUGIN_HANDLE, READINGSET *))
				      manager->resolveSymbol(handle,
							     "plugin_ingest");
	pluginShutdownDataPtr = (string (*)(const PLUGIN_HANDLE))
				 manager->resolveSymbol(handle, "plugin_shutdown");
	pluginStartDataPtr = (void (*)(const PLUGIN_HANDLE, const string& storedData))
			      manager->resolveSymbol(handle, "plugin_start");
	pluginStartPtr = (void (*)(const PLUGIN_HANDLE))
			      manager->resolveSymbol(handle, "plugin_start");
  	pluginReconfigurePtr = (void (*)(PLUGIN_HANDLE, const string&))
				      manager->resolveSymbol(handle,
							     "plugin_reconfigure");

	// Set m_instance default value
	m_instance = NULL;

	// Persist data initialised
	m_plugin_data = NULL;	
}

/**
 * FilterPlugin destructor
 */
FilterPlugin::~FilterPlugin()
{
	delete m_plugin_data;
}

/**
 * Call the loaded plugin "plugin_init" method
 *
 * @param config	The filter configuration
 * @param outHandle	The ouutput_handled passed with
 *			filtered data to OUTPUT_STREAM function
 * @param outputFunc	The output_stream function pointer
 * 			the filter uses to pass data out
 * @return		The PLUGIN_HANDLE object
 */
PLUGIN_HANDLE FilterPlugin::init(const ConfigCategory& config,
				 OUTPUT_HANDLE *outHandle,
				 OUTPUT_STREAM outputFunc)
{
	m_instance = this->pluginInit(&config,
				      outHandle,
				      outputFunc);
	return (m_instance ? &m_instance : NULL);
}

/**
 * Call the loaded plugin "plugin_shutdown" method
 */
void FilterPlugin::shutdown()
{
	// Check if m_instance has been set
	// and function pointer exists
	if (m_instance && this->pluginShutdownPtr)
	{
		return this->pluginShutdownPtr(m_instance);
	}
}

/**
 * Call the loaded plugin "plugin_shutdown" method
 * returning plugind data (as string)
 *
 * @return	Plugin data as JSON string (to be saved into strage layer)
 */
string FilterPlugin::shutdownSaveData()
{
	string ret("");
	// Check if m_instance has been set
	// and function pointer exists
	if (m_instance && this->pluginShutdownDataPtr)
	{
		ret = this->pluginShutdownDataPtr(m_instance);
	}
	return ret;
}

/**
 * Call plugin_start
 */
void FilterPlugin::start()
{
	if (pluginStartPtr)
	{
        	return this->pluginStartPtr(m_instance);
	}
}

/**
 * Call plugin_reconfigure method
 *
 * @param configuration	The new filter configuration
 */
void FilterPlugin::reconfigure(const string& configuration)
{
	if (pluginReconfigurePtr)
	{
        	return this->pluginReconfigurePtr(m_instance, configuration);
	}
}

/**
 * Call plugin_start passing plugin data.
 *
 * @param storedData	Plugin data to pass (from storage layer)
 */
void FilterPlugin::startData(const string& storedData)
{
	// Check pluginStartData function pointer exists
	if (this->pluginStartDataPtr)
	{
		this->pluginStartDataPtr(m_instance, storedData);
	}
}

/**
 * Call the loaded plugin "plugin_ingest" method
 *
 * This call ingest the readings through the filters chain
 *
 * @param readings	The reading set to ingest
 */
void FilterPlugin::ingest(READINGSET* readings)
{
	if (this->pluginIngestPtr)
	{
        	return this->pluginIngestPtr(m_instance, readings);
	}
}

