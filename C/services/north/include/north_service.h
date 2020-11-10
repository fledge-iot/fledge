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
#include <config_category.h>
#include <filter_plugin.h>

#define SERVICE_NAME  "Fledge North"


/**
 * The NorthService class. This class is the core
 * of the service that provides north side services
 * to Fledge.
 */
class NorthService : public ServiceHandler {
	public:
		NorthService(const std::string& name);
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
		NorthPlugin			*northPlugin;
		const std::string&		m_name;
		Logger        			*logger;
		AssetTracker			*m_assetTracker;
		bool				m_shutdown;
		ConfigCategory			m_config;
		ConfigCategory			m_configAdvanced;
		static ManagementClient		*m_mgtClient;
		unsigned long			m_readingsPerSec;	// May not be per second, new rate defines time units
		unsigned int			m_threshold;
		unsigned long			m_timeout;
		bool				m_throttle;
		bool				m_throttled;
		unsigned int			m_highWater;
		unsigned int			m_lowWater;
		struct timeval			m_lastThrottle;
		struct timeval			m_desiredRate;
		struct timeval			m_currentRate;
		int				m_timerfd;
};
#endif
