/*
 * FogLAMP north service.
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
        pluginInit = (PLUGIN_HANDLE (*)(const map<string, string>& config))
					manager->resolveSymbol(handle, "plugin_init");

	pluginShutdownPtr = (void (*)(const PLUGIN_HANDLE))
				      manager->resolveSymbol(handle, "plugin_shutdown");

	pluginSend = (uint32_t (*)(const PLUGIN_HANDLE, const vector<Reading* >& readings))
				   manager->resolveSymbol(handle, "plugin_send");

	pluginGetConfig = (map<const string, const string>& (*)())manager->resolveSymbol(handle, "plugin_config");
}

// Destructor
NorthPlugin::~NorthPlugin()
{
}

/**
 * Initialise the plugin with configuration data
 *
 * @param config    The configuration data
 * @return          The plugin handle
 */
PLUGIN_HANDLE NorthPlugin::init(const map<string, string>& config)
{
	m_instance = this->pluginInit(config);
	return &m_instance;
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
 * Return plugin specific configuration
 */
map<const string, const string>& NorthPlugin::config() const
{
	return this->pluginGetConfig();
}

/**
 * Call the shutdown method in the plugin
 */
void NorthPlugin::shutdown()
{
        return this->pluginShutdownPtr(m_instance);
}
