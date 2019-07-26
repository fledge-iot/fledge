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

/*
 * Control the throttling of poll based plugins
 *
 * If the ingest queue grows then we reduce the poll rate, i.e. increase
 * the interval between poll calls. If the ingest queue then drops below
 * the threshold set in the advance configuration we then bring the poll
 * rate back up.
 */
#define SOUTH_THROTTLE_HIGH_PERCENT	50	// Percentage above buffer threshold where we throttle down
#define SOUTH_THROTTLE_LOW_PERCENT	10	// Percentage above buffer threshold where we throttle up
#define SOUTH_THROTTLE_PERCENT		10	// The percentage we throttle poll by
#define SOUTH_THROTTLE_DOWN_INTERVAL	10	// Interval between throttle down attmepts
#define SOUTH_THROTTLE_UP_INTERVAL	15	// Interval between throttle up attempts

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
		int 				createTimerFd(struct timeval rate);
		void 				createConfigCategories(DefaultConfigCategory configCategory, std::string parent_name,std::string current_name);
		void				throttlePoll();
	private:
		SouthPlugin			*southPlugin;
		const std::string&		m_name;
		Logger        			*logger;
		AssetTracker			*m_assetTracker;
		bool				m_shutdown;
		ConfigCategory			m_config;
		ConfigCategory			m_configAdvanced;
		ManagementClient		*m_mgtClient;
		unsigned long			m_readingsPerSec;	// May not be per second, new rate defines time units
		unsigned int			m_threshold;
		unsigned long			m_timeout;
		Ingest				*m_ingest;
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
