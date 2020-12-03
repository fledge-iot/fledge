/*
 * Fledge north service.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <north_plugin.h>
#include <config_category.h>
#include <logger.h>
#include <exception>
#include <typeinfo>
#include <stdexcept>
#include <mutex>

using namespace std;

// mutex between various plugin methods, since reconfigure changes the handle 
// object itself and marks previous handle as garbage collectible by Python runtime
std::mutex mtx2;

/**
 * Constructor for the class that wraps the north plugin
 *
 * Create a set of function points that resolve to the loaded plugin and
 * enclose in the class.
 *
 */
NorthPlugin::NorthPlugin(PLUGIN_HANDLE handle, const ConfigCategory& category) : Plugin(handle)
{
	// Call the init method of the plugin
	PLUGIN_HANDLE (*pluginInit)(const void *) = (PLUGIN_HANDLE (*)(const void *))
					manager->resolveSymbol(handle, "plugin_init");
	instance = (*pluginInit)(&category);

	if (!instance)
	{
		Logger::getLogger()->error("plugin_init returned NULL, cannot proceed");
		throw new exception();
	}

	// Setup the function pointers to the plugin
  	pluginSendPtr = (uint32_t (*)(PLUGIN_HANDLE, const std::vector<Reading *>& readings))
				manager->resolveSymbol(handle, "plugin_send");
	
  	pluginReconfigurePtr = (void (*)(PLUGIN_HANDLE*, const std::string&))
				manager->resolveSymbol(handle, "plugin_reconfigure");
  	pluginShutdownPtr = (void (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_shutdown");

	pluginShutdownDataPtr = (string (*)(const PLUGIN_HANDLE))
				 manager->resolveSymbol(handle, "plugin_shutdown");
}

/**
 * Call the send method in the plugin
 */
uint32_t NorthPlugin::send(const vector<Reading *>& readings)
{
	lock_guard<mutex> guard(mtx2);
	try {
		return this->pluginSendPtr(instance, readings);
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in north plugin send(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in north plugin send(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

/**
 * Call the reconfigure method in the plugin
 */
void NorthPlugin::reconfigure(const string& newConfig)
{
	if (!pluginReconfigurePtr)
	{
		/*
		 * The plugin does not support reconfiguration, shutdown
		 * and restart the plugin.
		 */
		lock_guard<mutex> guard(mtx2);
		(*pluginShutdownPtr)(instance);
		PLUGIN_HANDLE (*pluginInit)(const void *) = (PLUGIN_HANDLE (*)(const void *))
					manager->resolveSymbol(handle, "plugin_init");
		ConfigCategory category("new", newConfig);
		instance = (*pluginInit)(&category);
		return;
	}
	lock_guard<mutex> guard(mtx2);
	try {
		this->pluginReconfigurePtr(&instance, newConfig);
		if (!instance)
		{
			Logger::getLogger()->error("plugin_reconfigure returned NULL, cannot proceed");
			throw new exception();
		}
		return;
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in north plugin reconfigure(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in north plugin reconfigure(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

/**
 * Call the shutdown method in the plugin
 */
void NorthPlugin::shutdown()
{
	lock_guard<mutex> guard(mtx2);
	try {
		return this->pluginShutdownPtr(instance);
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in north plugin shutdown(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in north plugin shutdown(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}
