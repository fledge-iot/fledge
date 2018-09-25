/*
 * FogLAMP south service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <south_plugin.h>
#include <config_category.h>

using namespace std;

/**
 * Constructor for the class that wraps the south plugin
 *
 * Create a set of function points that resolve to the loaded plugin and
 * enclose in the class.
 *
 */
SouthPlugin::SouthPlugin(PLUGIN_HANDLE handle, const ConfigCategory& category) : Plugin(handle)
{
	// Call the init method of the plugin
	PLUGIN_HANDLE (*pluginInit)(const void *) = (PLUGIN_HANDLE (*)(const void *))
					manager->resolveSymbol(handle, "plugin_init");
	instance = (*pluginInit)(&category);


	// Setup the function pointers to the plugin
  	pluginStartPtr = (void (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_start");
  	pluginPollPtr = (Reading (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_poll");
  	pluginReconfigurePtr = (void (*)(PLUGIN_HANDLE, std::string&))
				manager->resolveSymbol(handle, "plugin_reconfigure");
  	pluginShutdownPtr = (void (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_shutdown");
	if (isAsync())
	{
  		pluginRegisterPtr = (void (*)(PLUGIN_HANDLE, INGEST_CB cb, void *data))
				manager->resolveSymbol(handle, "plugin_register_ingest");
	}
}

/**
 * Call the start method in the plugin
 */
void SouthPlugin::start()
{
	return this->pluginStartPtr(instance);
}

/**
 * Call the poll method in the plugin
 */
Reading SouthPlugin::poll()
{
	return this->pluginPollPtr(instance);
}


/**
 * Call the reconfigure method in the plugin
 */
void SouthPlugin::reconfigure(string& newConfig)
{
	return this->pluginReconfigurePtr(instance, newConfig);
}

/**
 * Call the shutdown method in the plugin
 */
void SouthPlugin::shutdown()
{
	return this->pluginShutdownPtr(instance);
}

void SouthPlugin::registerIngest(INGEST_CB cb, void *data)
{
	return this->pluginRegisterPtr(instance, cb, data);
}
