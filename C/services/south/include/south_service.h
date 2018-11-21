#ifndef _SOUTH_SERVICE_H
#define _SOUTH_SERVICE_H
/*
 * FogLAMP south service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <logger.h>
#include <south_plugin.h>
#include <service_handler.h>
#include <management_client.h>
#include <config_category.h>
#include <ingest.h>
#include <filter_plugin.h>

#define SERVICE_NAME  "FogLAMP South"

/**
 * The SouthService class. This class is the core
 * of the service that provides south side services
 * to FogLAMP.
 */
class SouthService : public ServiceHandler {
	public:
		SouthService(const std::string& name);
		void 				start(std::string& coreAddress,
						      unsigned short corePort);
		void 				stop();
		void				shutdown();
		void				configChange(const std::string&,
						const std::string&);
	private:
		void				addConfigDefaults(DefaultConfigCategory& defaults);
		bool 				loadPlugin();
		int 				createTimerFd(int usecs);
		void 				createConfigCategories(DefaultConfigCategory configCategory, std::string parent_name,std::string current_name);
	private:
		SouthPlugin			*southPlugin;
		const std::string&		m_name;
		Logger        			*logger;
		bool				m_shutdown;
		ConfigCategory			m_config;
		ConfigCategory			m_configAdvanced;
		ManagementClient		*m_mgtClient;
		unsigned long			m_readingsPerSec;
		unsigned int			m_threshold;
		unsigned long			m_timeout;
};
#endif
