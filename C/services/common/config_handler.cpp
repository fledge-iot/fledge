/*
 * Fledge config manager.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <config_handler.h>

using namespace std;

ConfigHandler *ConfigHandler::instance = 0;


/**
 * ConfigHandler Singleton implementation
*/
ConfigHandler *
ConfigHandler::getInstance(ManagementClient *mgtClient)
{
	if (!instance)
		instance = new ConfigHandler(mgtClient);
	return instance;
}

/**
 * Config Handler Constructor
 */
ConfigHandler::ConfigHandler(ManagementClient *mgtClient)
					 : m_mgtClient(mgtClient)
{	
	m_logger = Logger::getLogger();
}

/**
 * Handle a callback from the core to propagate a configuration category
 * change and propagate that to all the local ServiceHandlers that have
 * registered for it.
 *
 * @param category	The name of the category that has changed
 * @param config	The configuration category itself
 */
void
ConfigHandler::configChange(const string& category, const string& config)
{
	m_logger->info("Configuration change notification for %s", category.c_str());
	std::unique_lock<std::mutex> lck(m_mutex);
	pair<CONFIG_MAP::iterator, CONFIG_MAP::iterator> res =
			 m_registrations.equal_range(category);
	for (CONFIG_MAP::iterator it = res.first; it != res.second; it++)
	{
		// The config change call could effect the registered handlers
		// we therefore need to guard against the map changing
		m_change = false;
		lck.unlock();
		it->second->configChange(category, config);
		lck.lock();
		if (m_change) // Something changed
		{
			return;	// Call any other subscribers to this category. In reality there are no others
		}
	}
}

/**
 * Register a service handler for a given configuration category
 *
 * @param handler	The service handler to call
 * @param category	The configuration category to register
 */
void
ConfigHandler::registerCategory(ServiceHandler *handler, const string& category)
{
	if (m_registrations.count(category) == 0)
	{
		int retryCount = 0;
		while (m_mgtClient->registerCategory(category) == false &&
				retryCount++ < 10)
		{
			sleep(2 * retryCount);
		}
		if (retryCount >= 10)
		{
			m_logger->error("Failed to register configuration category %s", category.c_str());
		}
		else
		{
			 m_logger->debug("Interest in %s registered", category.c_str());
		}
	}
	else
	{
		m_logger->info("Interest in %s already registered", category.c_str());
	}
	std::unique_lock<std::mutex> lck(m_mutex);
	m_registrations.insert(pair<string, ServiceHandler *>(category, handler));
	m_change = true;
}

// FIXME_I: fix text messages
void ConfigHandler::registerCategoryChild(ServiceHandler *handler, const string& category)
{
	if (m_registrationsChild.count(category) == 0)
	{
		int retryCount = 0;
		while (m_mgtClient->registerCategoryChild(category) == false &&
				retryCount++ < 10)
		{
			sleep(2 * retryCount);
		}
		if (retryCount >= 10)
		{
			m_logger->error("Failed to register configuration category %s", category.c_str());
		}
		else
		{
			 m_logger->debug("Interest in %s registered", category.c_str());
		}
	}
	else
	{
		m_logger->info("Interest in %s already registered", category.c_str());
	}
	std::unique_lock<std::mutex> lck(m_mutex);
	m_registrationsChild.insert(pair<string, ServiceHandler *>(category, handler));
	m_change = true;
}


/**
 * Unregister a configuration category from the ConfigHandler for
 * a particular registered ServiceHandler class
 *
 * @param handler The configuration handler we would call
 * @param category	The category to remove.
 */
void
ConfigHandler::unregisterCategory(ServiceHandler *handler, const string& category)
{
	std::unique_lock<std::mutex> lck(m_mutex);
	pair<CONFIG_MAP::iterator, CONFIG_MAP::iterator> res =
			 m_registrations.equal_range(category);
	for (CONFIG_MAP::iterator it = res.first; it != res.second; it++)
	{
		if (it->second == handler)
		{
			m_registrations.erase(it);
			break;
		}
	}
	// No remaining registration for this category
	if (m_registrations.count(category) == 0)
	{
		m_mgtClient->unregisterCategory(category);
	}
	m_change = true;
}
