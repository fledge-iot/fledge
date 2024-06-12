#ifndef _STORAGE_SERVICE_H
#define _STORAGE_SERVICE_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <storage_api.h>
#include <logger.h>
#include <configuration.h>
#include <storage_plugin.h>
#include <plugin_configuration.h>
#include <service_handler.h>

#define SERVICE_NAME  "Fledge Storage"

/**
 * The StorageService class. This class is the core
 * of the service that offers access to the Fledge
 * storage layer. It maintains the API and provides
 * the hooks for incoming management API requests.
 */
class StorageService : public ServiceHandler {
	public:
		StorageService(const string& name);
		~StorageService();
		void 			start(std::string& coreAddress, unsigned short corePort);
		void 			stop();
		void			shutdown();
		void			restart();
		bool			isRunning() { return !m_shutdown; };
		void			configChange(const std::string&, const std::string&);
		void			configChildCreate(const std::string&, const std::string&, const std::string&){};
		void			configChildDelete(const std::string& , const std::string&){};
		string			getPluginName();
		string			getPluginManagedStatus();
		string			getReadingPluginName();
		void			setLogLevel(std::string level)
					{
						m_logLevel = level;
					};
	private:
		const string&		m_name;
		bool 			loadPlugin();
		StorageApi    		*api;
		StorageConfiguration	*config;
		Logger        		*logger;
		StoragePlugin 		*storagePlugin;
		StoragePlugin 		*readingPlugin;
		bool			m_shutdown;
		bool			m_requestRestart;
		std::string		m_logLevel;
		long			m_timeout;
};
#endif
