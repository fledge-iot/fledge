#ifndef _SOUTH_SERVICE_H
#define _SOUTH_SERVICE_H
/*
 * Fledge south service.
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
#include <config_category.h>
#include <ingest.h>
#include <filter_plugin.h>
#include <plugin_data.h>
#include <audit_logger.h>
#include <perfmonitors.h>

#define MAX_SLEEP	5		// Maximum number of seconds the service will sleep during a poll cycle

#define SERVICE_NAME  "Fledge South"

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
 * State bits for the south pipeline debugger
 */
#define DEBUG_ATTACHED		0x01
#define DEBUG_SUSPENDED		0x02
#define DEBUG_ISOLATED		0x04


class SouthServiceProvider;

/**
 * The SouthService class. This class is the core
 * of the service that provides south side services
 * to Fledge.
 */
class SouthService : public ServiceAuthHandler {
	public:
		SouthService(const std::string& name,
			const std::string& token = "");
		virtual				~SouthService();
		void 				start(std::string& coreAddress,
						      unsigned short corePort);
		void 				stop();
		void				shutdown();
		void				restart();
		void				configChange(const std::string&, const std::string&);
		void				processConfigChange(const std::string&, const std::string&);
		void				configChildCreate(const std::string&,
								const std::string&,
								const std::string&){};
		void				configChildDelete(const std::string&,
								const std::string&){};
		bool				isRunning() { return !m_shutdown; };
		bool				setPoint(const std::string& name, const std::string& value);
		bool				operation(const std::string& name, std::vector<PLUGIN_PARAMETER *>& );
		void				setDryRun() { m_dryRun = true; };
		void				handlePendingReconf();
		// Debugger Entry point
		bool				attachDebugger()
						{
							if (m_ingest)
							{
								m_debugState = DEBUG_ATTACHED;
								return m_ingest->attachDebugger();
							}
							return false;
						};
		void				detachDebugger()
						{
							if (m_ingest)
								m_ingest->detachDebugger();
							suspendDebugger(false);
							isolateDebugger(false);
							m_debugState = 0;
						};
		void				setDebuggerBuffer(unsigned int size)
						{
							if (m_ingest)
								m_ingest->setDebuggerBuffer(size);
						};
		std::string			getDebuggerBuffer()
						{
							if (m_ingest)
								return m_ingest->getDebuggerBuffer();
							return "";
						};
		void				suspendDebugger(bool suspend)
						{
							suspendIngest(suspend);
							if (suspend)
								m_debugState |= DEBUG_SUSPENDED;
							else
								m_debugState &= ~(unsigned int)DEBUG_SUSPENDED;
						};
		void				isolateDebugger(bool isolate)
						{
							if (m_ingest)
								m_ingest->isolate(isolate);
							if (isolate)
								m_debugState |= DEBUG_ISOLATED;
							else
								m_debugState &= ~(unsigned int)DEBUG_ISOLATED;
						};
		void				stepDebugger(unsigned int steps)
						{
							std::lock_guard<std::mutex> guard(m_suspendMutex);
							m_steps = steps;
						}
		void				replayDebugger()
						{
							if (m_ingest)
								m_ingest->replayDebugger();
						};
		std::string			debugState();
		bool				debuggerAttached()
						{
							return m_debugState & DEBUG_ATTACHED;
						}
		
	private:
		void				addConfigDefaults(DefaultConfigCategory& defaults);
		bool 				loadPlugin();
		int 				createTimerFd(struct timeval rate);
		void 				createConfigCategories(DefaultConfigCategory configCategory,
									std::string parent_name,
									std::string current_name);
		void				throttlePoll();
		void				processNumberList(const ConfigCategory& cateogry, const std::string& item, std::vector<unsigned long>& list);
		void				calculateTimerRate();
		bool				syncToNextPoll();
		bool				onDemandPoll();
		void				checkPendingReconfigure();
		void				suspendIngest(bool suspend)
						{
							std::lock_guard<std::mutex> guard(m_suspendMutex);
							m_suspendIngest = suspend;
							m_steps = 0;
						};
		bool				isSuspended()
						{
							std::lock_guard<std::mutex> guard(m_suspendMutex);
							return m_suspendIngest;
						};
		bool				willStep()
						{
							std::lock_guard<std::mutex> guard(m_suspendMutex);
							if (m_suspendIngest && m_steps > 0)
							{
								m_steps--;
								return true;
							}
							return false;
						};
		void 				getResourceLimit();
	private:
		std::thread			*m_reconfThread;
		std::deque<std::pair<std::string,std::string>>	m_pendingNewConfig;
		std::mutex			m_pendingNewConfigMutex;
		std::condition_variable		m_cvNewReconf;
	
		SouthPlugin			*southPlugin;
		Logger        			*logger;
		AssetTracker			*m_assetTracker;
		bool				m_shutdown;
		ConfigCategory			m_config;
		ConfigCategory			m_configAdvanced;
		ConfigCategory			m_configResourceLimit;
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
		const std::string		m_token;
		unsigned int			m_repeatCnt;
		PluginData			*m_pluginData;
		std::string			m_dataKey;
		bool				m_dryRun;
		bool				m_requestRestart;
		std::string			m_rateUnits;
		enum { POLL_INTERVAL, POLL_FIXED, POLL_ON_DEMAND }
						m_pollType;
		std::vector<unsigned long>	m_hours;
		std::vector<unsigned long>	m_minutes;
		std::vector<unsigned long>	m_seconds;
		std::string			m_hoursStr;
		std::string			m_minutesStr;
		std::string			m_secondsStr;
		std::condition_variable		m_pollCV;
		std::mutex			m_pollMutex;
		bool				m_doPoll;
		AuditLogger			*m_auditLogger;
		PerformanceMonitor		*m_perfMonitor;
		bool				m_suspendIngest;
		unsigned int			m_steps;
		std::mutex			m_suspendMutex;
		unsigned int			m_debugState;
		SouthServiceProvider		*m_provider;
		ServiceBufferingType			m_serviceBufferingType;
		unsigned int			m_serviceBufferSize;
		DiscardPolicy			m_discardPolicy;
};

/**
 *
 * A data provider class to return data in the south service ping response
 */
class SouthServiceProvider : public JSONProvider {
	public:
		SouthServiceProvider(SouthService *south) : m_south(south) {};
		virtual ~SouthServiceProvider() {};
		void 	asJSON(std::string &json) const
			{
				if (m_south)
				{
					json = "\"debug\" : " + m_south->debugState();
				}
			};
	private:
		SouthService	*m_south;
};
#endif
