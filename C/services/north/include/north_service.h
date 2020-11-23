#ifndef _NORTH_SERVICE_H
#define _NORTH_SERVICE_H
/*
 * Fledge north service.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <logger.h>
#include <north_plugin.h>
#include <service_handler.h>
#include <management_client.h>
#include <storage_client.h>
#include <config_category.h>
#include <filter_plugin.h>

#define SERVICE_NAME  "Fledge North"

class DataLoad;
class DataSender;

/**
 * The NorthService class. This class is the core
 * of the service that provides north side services
 * to Fledge.
 */
class NorthService : public ServiceHandler {
	public:
		NorthService(const std::string& name);
		~NorthService();
		void 				start(std::string& coreAddress,
						      unsigned short corePort);
		void 				stop();
		void				shutdown();
		void				configChange(const std::string&,
						const std::string&);
		static ManagementClient *	getMgmtClient();
	private:
		void				addConfigDefaults(DefaultConfigCategory& defaults);
		bool 				loadPlugin();
		void 				createConfigCategories(DefaultConfigCategory configCategory, std::string parent_name,std::string current_name);
	private:
		DataLoad			*m_dataLoad;
		NorthPlugin			*northPlugin;
		const std::string&		m_name;
		Logger        			*logger;
		AssetTracker			*m_assetTracker;
		bool				m_shutdown;
		ConfigCategory			m_config;
		ConfigCategory			m_configAdvanced;
		static ManagementClient		*m_mgtClient;
		StorageClient			*m_storage;
};
#endif
