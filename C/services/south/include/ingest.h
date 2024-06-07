#ifndef _INGEST_H
#define _INGEST_H
/*
 * Fledge reading ingest.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto, Amandeep Singh Arora
 */
#include <storage_client.h>
#include <reading.h>
#include <logger.h>
#include <vector>
#include <queue>
#include <thread>
#include <chrono>
#include <mutex>
#include <sstream>
#include <unordered_set>
#include <condition_variable>
#include <filter_plugin.h>
#include <filter_pipeline.h>
#include <asset_tracking.h>
#include <service_handler.h>
#include <set>
#include <perfmonitors.h>

#define SERVICE_NAME  "Fledge South"

#define INGEST_SUFFIX	"-Ingest"	// Suffix for per service ingest statistic

#define FLUSH_STATS_INTERVAL 5		// Period between flushing of stats to storage (seconds)

#define STATS_UPDATE_FAIL_THRESHOLD 10	// After this many update fails try creating new stats

#define DEPRECATED_CACHE_AGE	600	// Maximum allowed aged of the deprecated asset cache

/*
 * Constants related to flow control for async south services.
 *
 */
#define	AFC_SLEEP_INCREMENT	20	// Number of milliseconds to wait for readings to drain
#define AFC_SLEEP_MAX		200	// Maximum sleep tiem in ms between tests
#define AFC_MAX_WAIT		5000	// Maximum amount of time we wait for the queue to drain

/**
 * The ingest class is used to ingest asset readings.
 * It maintains a queue of readings to be sent to storage,
 * these are sent using a background thread that regularly
 * wakes up and sends the queued readings.
 */
class Ingest : public ServiceHandler {

public:
	Ingest(StorageClient& storage,
		const std::string& serviceName,
		const std::string& pluginName,
		ManagementClient *mgmtClient);
	~Ingest();

	void		ingest(const Reading& reading);
	void		ingest(const std::vector<Reading *> *vec);
	void		start(long timeout, unsigned int threshold);
	bool		running();
    	bool		isStopping();
	bool		isRunning() { return !m_shutdown; };
	void		processQueue();
	void		waitForQueue();
	size_t		queueLength();
	void		updateStats(void);
	int 		createStatsDbEntry(const std::string& assetName);

	bool		loadFilters(const std::string& categoryName);
	static void	passToOnwardFilter(OUTPUT_HANDLE *outHandle,
					   READINGSET* readings);
	static void	useFilteredData(OUTPUT_HANDLE *outHandle,
					READINGSET* readings);

	void		setTimeout(const long timeout) { m_timeout = timeout; };
	void		setThreshold(const unsigned int threshold) { m_queueSizeThreshold = threshold; };
	void		configChange(const std::string&, const std::string&);
	void		configChildCreate(const std::string& , const std::string&, const std::string&){};
	void		configChildDelete(const std::string& , const std::string&){};
	void		shutdown() {};	// Satisfy ServiceHandler
	void		restart() {};	// Satisfy ServiceHandler
	void		unDeprecateAssetTrackingRecord(AssetTrackingTuple* currentTuple,
							const std::string& assetName,
							const std::string& event);
	void		unDeprecateStorageAssetTrackingRecord(StorageAssetTrackingTuple* currentTuple,
							const std::string& assetName,
							const std::string&,
							const unsigned int&);
	void		setStatistics(const std::string& option);

	std::string  	getStringFromSet(const std::set<std::string> &dpSet);
	void		setFlowControl(unsigned int lowWater, unsigned int highWater) { m_lowWater = lowWater; m_highWater = highWater; };
	void		flowControl();
	void		setPerfMon(PerformanceMonitor *mon)
			{
				m_performance = mon;
			};

private:
	void				signalStatsUpdate() {
						// Signal stats thread to update stats
						std::lock_guard<std::mutex> guard(m_statsMutex);
						m_statsCv.notify_all();
					};
	void				logDiscardedStat() {
						std::lock_guard<std::mutex> guard(m_statsMutex);
						m_discardedReadings++;
					};
	long				calculateWaitTime();
	int 				createServiceStatsDbEntry();

	StorageClient&			m_storage;
	long				m_timeout;
	bool				m_shutdown;
	unsigned int			m_queueSizeThreshold;
	bool				m_running;
	std::string 			m_serviceName;
	std::string 			m_pluginName;
	ManagementClient		*m_mgtClient;
	// New data: queued
	std::vector<Reading *>*		m_queue;
	std::mutex			m_qMutex;
	std::mutex			m_statsMutex;
	std::mutex			m_pipelineMutex;
	std::thread*			m_thread;
	std::thread*			m_statsThread;
	Logger*				m_logger;
	std::condition_variable		m_cv;
	std::condition_variable		m_statsCv;
	// Data ready to be filtered/sent
	std::vector<Reading *>*		m_data;
	std::vector<std::vector<Reading *>*>
					m_resendQueues;
	std::queue<std::vector<Reading *>*>
					m_fullQueues;
	std::mutex			m_fqMutex;
	unsigned int			m_discardedReadings; // discarded readings since last update to statistics table
	FilterPipeline*			m_filterPipeline;
	
	std::unordered_set<std::string> statsDbEntriesCache;  // confirmed stats table entries
	std::map<std::string, int>	statsPendingEntries;  // pending stats table entries
	bool				m_highLatency;	      // Flag to indicate we are exceeding latency request
	bool				m_10Latency;	      // Latency within 10%
	time_t				m_reportedLatencyTime;// Last tiem we reported high latency
	int				m_failCnt;
	bool				m_storageFailed;
	int				m_storesFailed;
	int				m_statsUpdateFails;
	enum { STATS_BOTH, STATS_ASSET, STATS_SERVICE }
					m_statisticsOption;
	unsigned int			m_highWater;
	unsigned int			m_lowWater;
	AssetTrackingTable		*m_deprecated;
	time_t				m_deprecatedAgeOut;
	time_t				m_deprecatedAgeOutStorage;
	PerformanceMonitor		*m_performance;
};

#endif
