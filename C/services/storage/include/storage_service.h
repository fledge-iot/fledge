#ifndef _STORAGE_SERVICE_H
#define _STORAGE_SERVICE_H
/*
 * FogLAMP storage service.
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
#include <service_handler.h>

#define SERVICE_NAME  "FogLAMP Storage"

/**
 * The StorageService class. This class is the core
 * of the service that offers access to the FogLAMP
 * storage layer. It maintains the API and provides
 * the hooks for incoming management API requests.
 */
class StorageService : public ServiceHandler {
	public:
		StorageService(const string& name);
		void 			start(std::string& coreAddress, unsigned short corePort);
		void 			stop();
		void			shutdown();
		void			configChange(const std::string&, const std::string&);
		string			getPluginName();
		string			getPluginManagedStatus();
	private:
		const string&		m_name;
		bool 			loadPlugin();
		StorageApi    		*api;
		StorageConfiguration	*config;
		Logger        		*logger;
		StoragePlugin 		*storagePlugin;
		bool			m_shutdown;
};
#endif
