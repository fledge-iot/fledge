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
		bool 				loadFilters(const std::string& categoryName,
							    Ingest& ingest) const;
		bool				setupFiltersPipeline(const Ingest& ingest) const;
	private:
		SouthPlugin			*southPlugin;
		const std::string&		m_name;
		Logger        			*logger;
		bool				m_shutdown;
		ConfigCategory			m_config;
		ManagementClient		*m_mgtClient;
		unsigned long			m_pollInterval;
		unsigned int			m_threshold;
		unsigned long			m_timeout;
};
#endif
