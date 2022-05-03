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
	m_instance = (*pluginInit)(&category);

	if (!m_instance)
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

	pluginStartPtr = (void (*)(const PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_start");
	pluginStartDataPtr = (void (*)(const PLUGIN_HANDLE, const string& storedData))
				manager->resolveSymbol(handle, "plugin_start");
	if (hasControl())
	{
		pluginRegisterPtr = (void (*)(const PLUGIN_HANDLE handle, bool ( *write)(char *name, char *value, ControlDestination destination, ...),
                                     int (* operation)(char *operation, int paramCount, char *names[], char *parameters[], ControlDestination destination, ...)))manager->resolveSymbol(handle, "plugin_register");
	}
	else
	{
		pluginRegisterPtr = NULL;
	}
}

NorthPlugin::~NorthPlugin()
{
}

/**
 * Call the start method in the plugin
 * with no persisted data
 */
void NorthPlugin::start()
{
	// Check pluginStart function pointer exists
	if (this->pluginStartPtr)
	{
		this->pluginStartPtr(m_instance);
	}
}

/**
 * Call the start method in the plugin
 * passing persisted data
 */
void NorthPlugin::startData(const string& storedData)
{
	// Ccheck pluginStartData function pointer exists
	if (this->pluginStartDataPtr)
	{
		this->pluginStartDataPtr(m_instance, storedData);
	}
}

/**
 * Call the send method in the plugin
 */
uint32_t NorthPlugin::send(const vector<Reading *>& readings)
{
	lock_guard<mutex> guard(mtx2);
	try {
		return this->pluginSendPtr(m_instance, readings);
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
		if (persistData())
		{
		}
		else
		{
			(*pluginShutdownPtr)(m_instance);
			PLUGIN_HANDLE (*pluginInit)(const void *) = (PLUGIN_HANDLE (*)(const void *))
					manager->resolveSymbol(handle, "plugin_init");
			ConfigCategory category("new", newConfig);
			m_instance = (*pluginInit)(&category);
		}
		return;
	}
	lock_guard<mutex> guard(mtx2);
	try {
		this->pluginReconfigurePtr(&m_instance, newConfig);
		if (!m_instance)
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
	if (this->pluginShutdownPtr)
	{
		try {
			return this->pluginShutdownPtr(m_instance);
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
}

/**
 * Call the shutdown method in the plugin
 * and return plugin data to parsist as JSON string
 */
string NorthPlugin::shutdownSaveData()
{
	string ret("");
	// Check pluginShutdownData function pointer exists
	if (this->pluginShutdownDataPtr)
	{
		ret = this->pluginShutdownDataPtr(m_instance);
	}
	return ret;
}

/**
 * Call the plugin_register entry point of the plugin if one has been defined
 */
void NorthPlugin::pluginRegister(bool ( *write)(char *name, char *value, ControlDestination destination, ...), 
                                     int (* operation)(char *operation, int paramCount, char *names[], char *parameters[], ControlDestination destination, ...))
{
	if (hasControl() && pluginRegisterPtr)
	{
		(*pluginRegisterPtr)(m_instance, write, operation);
	}
}
