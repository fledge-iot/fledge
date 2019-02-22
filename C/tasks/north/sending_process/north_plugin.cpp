/*
 * FogLAMP north plugin
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <north_plugin.h>
#include <iostream>

using namespace std;

/**
 * Constructor for the class that wraps the OMF north plugin
 *
 * Create a set of function pointers.
 * @param handle    The loaded plugin handle
 */
NorthPlugin::NorthPlugin(const PLUGIN_HANDLE handle) : Plugin(handle)
{
        // Setup the function pointers to the plugin
        pluginInit = (PLUGIN_HANDLE (*)(const ConfigCategory* config))
					manager->resolveSymbol(handle, "plugin_init");

	pluginShutdown = (void (*)(const PLUGIN_HANDLE))
				   manager->resolveSymbol(handle, "plugin_shutdown");
	pluginShutdownData = (string (*)(const PLUGIN_HANDLE))
					 manager->resolveSymbol(handle, "plugin_shutdown");

	pluginSend = (uint32_t (*)(const PLUGIN_HANDLE, const vector<Reading* >& readings))
				   manager->resolveSymbol(handle, "plugin_send");

	pluginStart = (void (*)(const PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_start");
	pluginStartData = (void (*)(const PLUGIN_HANDLE, const string& storedData))
				manager->resolveSymbol(handle, "plugin_start");

	// Persist data initialised
	m_plugin_data = NULL;
}

// Destructor
NorthPlugin::~NorthPlugin()
{
	delete m_plugin_data;
}

/**
 * Initialise the plugin with configuration data
 *
 * @param config    The configuration data
 * @return          The plugin handle
 */
PLUGIN_HANDLE NorthPlugin::init(const ConfigCategory& config)
{
	// Pass input data pointer
	m_instance = this->pluginInit(&config);
	return &m_instance;
}

/**
 * Call the start method in the plugin
 * with no persisted data
 */
void NorthPlugin::start()
{
	// Ccheck pluginStart function pointer exists
	if (this->pluginStart)
	{
		this->pluginStart(m_instance);
	}
}

/**
 * Call the start method in the plugin
 * passing persisted data
 */
void NorthPlugin::startData(const string& storedData)
{
	// Ccheck pluginStartData function pointer exists
	if (this->pluginStartData)
	{
		this->pluginStartData(m_instance, storedData);
	}
}

/**
 * Send vector (by reference) of readings pointer to historian server
 *
 * @param  readings    The readings data
 * @return             The readings sent or 0 in case of any error
 */
uint32_t NorthPlugin::send(const vector<Reading* >& readings) const
{
	return this->pluginSend(m_instance, readings);
}

/**
 * Call the shutdown method in the plugin
 */
void NorthPlugin::shutdown()
{
	// Ccheck pluginShutdown function pointer exists
	if (this->pluginShutdown)
	{
		return this->pluginShutdown(m_instance);
	}
}

/**
 * Call the shutdown method in the plugin
 * and return plugin data to parsist as JSON string
 */
string NorthPlugin::shutdownSaveData()
{
	string ret("");
	// Check pluginShutdownData function pointer exists
	if (this->pluginShutdownData)
	{
		ret = this->pluginShutdownData(m_instance);
	}
	return ret;
}
