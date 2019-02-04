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
#include <logger.h>
#include <exception>
#include <typeinfo>
#include <stdexcept>

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

	if (!instance)
	{
		Logger::getLogger()->error("plugin_init returned NULL, cannot proceed");
		throw new exception();
	}

	// Setup the function pointers to the plugin
  	pluginStartPtr = (void (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_start");
	
	const char *pluginInterfaceVer = manager->getInfo(handle)->interface;
	if (pluginInterfaceVer[0]=='1' && pluginInterfaceVer[1]=='.')
	{
  		pluginPollPtr = (Reading (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_poll");
	}
	else if (pluginInterfaceVer[0]=='2' && pluginInterfaceVer[1]=='.')
	{
		pluginPollPtrV2 = (vector<Reading *>* (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_poll");
	}
	else
	{
		Logger::getLogger()->error("Invalid plugin interface version '%s', assuming version 1.x", pluginInterfaceVer);
		pluginPollPtr = (Reading (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_poll");
	}
	
  	pluginReconfigurePtr = (void (*)(PLUGIN_HANDLE*, const std::string&))
				manager->resolveSymbol(handle, "plugin_reconfigure");
  	pluginShutdownPtr = (void (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_shutdown");
	if (isAsync())
	{
		if (pluginInterfaceVer[0]=='1' && pluginInterfaceVer[1]=='.')
		{
	  		pluginRegisterPtr = (void (*)(PLUGIN_HANDLE, INGEST_CB cb, void *data))
				manager->resolveSymbol(handle, "plugin_register_ingest");
		}
		else if (pluginInterfaceVer[0]=='2' && pluginInterfaceVer[1]=='.')
		{
			pluginRegisterPtrV2 = (void (*)(PLUGIN_HANDLE, INGEST_CB2 cb, void *data))
				manager->resolveSymbol(handle, "plugin_register_ingest");
		}
		else
		{
			Logger::getLogger()->error("Invalid plugin interface version '%s', assuming version 1.x", pluginInterfaceVer);
			pluginRegisterPtr = (void (*)(PLUGIN_HANDLE, INGEST_CB cb, void *data))
				manager->resolveSymbol(handle, "plugin_register_ingest");
		}
	}

	pluginShutdownDataPtr = (string (*)(const PLUGIN_HANDLE))
				 manager->resolveSymbol(handle, "plugin_shutdown");
	pluginStartDataPtr = (void (*)(const PLUGIN_HANDLE, const string& storedData))
			      manager->resolveSymbol(handle, "plugin_start");
}

/**
 * Call the start method in the plugin
 */
void SouthPlugin::start()
{
	try {
		return this->pluginStartPtr(instance);
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin start(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin start(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

/**
 * Call the poll method in the plugin
 */
Reading SouthPlugin::poll()
{
	try {
		return this->pluginPollPtr(instance);
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin poll(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin poll(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

/**
 * Call the poll method in the plugin supporting interface ver 2.x
 */
vector<Reading *>* SouthPlugin::pollV2()
{
	try {
		return this->pluginPollPtrV2(instance);
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in v2 south plugin poll(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in v2 south plugin poll(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

/**
 * Call the reconfigure method in the plugin
 */
void SouthPlugin::reconfigure(const string& newConfig)
{
	try {
		this->pluginReconfigurePtr(&instance, newConfig);
		if (!instance)
		{
			Logger::getLogger()->error("plugin_reconfigure returned NULL, cannot proceed");
			throw new exception();
		}
		return;
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin reconfigure(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin reconfigure(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

/**
 * Call the shutdown method in the plugin
 */
void SouthPlugin::shutdown()
{
	try {
		return this->pluginShutdownPtr(instance);
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin shutdown(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin shutdown(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

void SouthPlugin::registerIngest(INGEST_CB cb, void *data)
{
	try {
		return this->pluginRegisterPtr(instance, cb, data);
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin registerIngest(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin registerIngest(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

void SouthPlugin::registerIngestV2(INGEST_CB2 cb, void *data)
{
	try {
		return this->pluginRegisterPtrV2(instance, cb, data);
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin registerIngestV2(), %s",
			e.what());
		throw;
	} catch (...) {
		std::exception_ptr p = std::current_exception();
		Logger::getLogger()->fatal("Unhandled exception raised in south plugin registerIngestV2(), %s",
			p ? p.__cxa_exception_type()->name() : "unknown exception");
		throw;
	}
}

