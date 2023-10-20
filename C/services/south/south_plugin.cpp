/*
 * Fledge south service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <south_plugin.h>
#include <south_service.h>
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
 * Constructor for the class that wraps the south plugin
 *
 * Create a set of function points that resolve to the loaded plugin and
 * enclose in the class.
 *
 */
SouthPlugin::SouthPlugin(PLUGIN_HANDLE handle, const ConfigCategory& category) : Plugin(handle)
{
	m_started = false; // Set started indicator, overrided by async plugins only

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
		pluginPollPtrV2 = (std::vector<Reading*>* (*)(PLUGIN_HANDLE))
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

	pluginWritePtr = NULL;
	pluginOperationPtr = NULL;

	if (hasControl())
	{
		pluginWritePtr = (bool (*)(const PLUGIN_HANDLE,
					const std::string&,
					const std::string&))
			manager->resolveSymbol(handle, "plugin_write");
		pluginOperationPtr = (bool (*)(const PLUGIN_HANDLE,
					const std::string&,
					int,
					PLUGIN_PARAMETER **))
			manager->resolveSymbol(handle, "plugin_operation");
	}
}

/**
 * South plugin destructor
 */
SouthPlugin::~SouthPlugin()
{
}

/**
 * Call the start method in the plugin
 */
void SouthPlugin::start()
{
	lock_guard<mutex> guard(mtx2);
	try {
		this->pluginStartPtr(instance);
		m_started = true; // Set start indicator
		return;
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
 * Call the start method in the plugin
 */
void SouthPlugin::startData(const string& data)
{
	lock_guard<mutex> guard(mtx2);
	try {
		this->pluginStartDataPtr(instance, data);
		m_started = true; // Set start indicator
		return;
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
	lock_guard<mutex> guard(mtx2);
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
ReadingSet* SouthPlugin::pollV2()
{
	lock_guard<mutex> guard(mtx2);
	try {
		std::vector<Reading *> *vec = this->pluginPollPtrV2(instance);
		if(vec)
		{
			ReadingSet *set = new ReadingSet(vec);
			vec->clear();
			delete vec;
			return set;  // this->pluginPollPtrV2(instance);
        	}
		else
			return NULL;
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
	lock_guard<mutex> guard(mtx2);
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

/**
 * Call the shutdown method in the plugin
 */
string SouthPlugin::shutdownSaveData()
{
	lock_guard<mutex> guard(mtx2);
	try {
		return this->pluginShutdownDataPtr(instance);
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
	lock_guard<mutex> guard(mtx2);
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
	lock_guard<mutex> guard(mtx2);
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

/**
 * Call the write entry point of the plugin
 *
 * @param name	The name of the parameter to change
 * @param value	The value to set the parameter
 */
bool SouthPlugin::write(const string& name, const string& value)
{
	try {
		if (pluginWritePtr)
		{
			bool run = true;
			// Check plugin_start is done for async plugin before calling pluginWritePtr
			if (isAsync()) {
				int tries = 0;
				while (!m_started) {
					std::this_thread::sleep_for(std::chrono::milliseconds(100));
					Logger::getLogger()->debug("South plugin write call is on hold, try %d", tries);
					if (tries > 20) {
						break;
					}
					tries++;
				}
				run = m_started;
			}

			if (run) {
				return this->pluginWritePtr(instance, name, value);
			}
                        else
			{
				Logger::getLogger()->error("South plugin write canceled after waiting for 2 seconds");
				return false;
			}
		}
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception in plugin write operation: %s", e.what());
	}
	return false;
}

/**
 * Call the plugin operation entry point with the operation to execute
 *
 * @param name	The name of the operation
 * @param parameters	The paramters for the operation.
 * @return bool	Status of the operation
 */
bool SouthPlugin::operation(const string& name, vector<PLUGIN_PARAMETER *>& parameters)
{
	bool status = false;

	if (! this->pluginOperationPtr)
	{
		Logger::getLogger()->error(
				"Attempt to invoke an operation '%s' on a plugin that does not provide operation entry point",
				name.c_str());
		return status;
	}
	unsigned int count = parameters.size();
	PLUGIN_PARAMETER **params = (PLUGIN_PARAMETER **)malloc(sizeof(PLUGIN_PARAMETER *) * (count + 1));
	if (params == NULL)
	{
		Logger::getLogger()->fatal("Unable to allocate parameters, out of memory");
		return status;
	}

	for (unsigned int i = 0; i < parameters.size(); i++)
	{
		params[i] = parameters[i];
	}
	params[count] = NULL;
	try {
		bool run = true;
		// Check plugin_start is done for async plugin before calling pluginOperationPtr
		if (isAsync()) {
			int tries = 0;
			while (!m_started) {
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
				Logger::getLogger()->debug("South plugin operation is on hold, try %d", tries);
				if (tries > 20) {
					break;
				}
				tries++;
			}
			run = m_started;
		}

		if (run) {
			status = this->pluginOperationPtr(instance, name, (int)count, params);
		}
		else
		{
			Logger::getLogger()->error("South plugin operation canceled after waiting for 2 seconds");
			return false;
		}
	} catch (exception& e) {
		Logger::getLogger()->fatal("Unhandled exception in plugin operation: %s", e.what());
	}
	free(params);
	return status;
}
