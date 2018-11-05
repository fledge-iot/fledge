#ifndef _INGEST_H
#define _INGEST_H
/*
 * FogLAMP reading ingest.
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
#include <thread>
#include <chrono>
#include <mutex>
#include <sstream>
#include <unordered_set>
#include <condition_variable>
#include <filter_plugin.h>
#include <asset_tracking.h>

#define SERVICE_NAME  "FogLAMP South"

/**
 * The ingest class is used to ingest asset readings.
 * It maintains a queue of readings to be sent to storage,
 * these are sent using a background thread that regularly
 * wakes up and sends the queued readings.
 */
class Ingest {

public:
	Ingest(StorageClient& storage,
		unsigned long timeout,
		unsigned int threshold,
		const std::string& serviceName,
		const std::string& pluginName,
		ManagementClient *mgmtClient);
	~Ingest();

	void		ingest(const Reading& reading);
	bool		running();
	void		processQueue();
	void		waitForQueue();
	void		updateStats(void);
	int 		createStatsDbEntry(const std::string& assetName);

	bool		loadFilters(const std::string& categoryName);
	bool		setupFiltersPipeline() const;
	static void	passToOnwardFilter(OUTPUT_HANDLE *outHandle,
					   READINGSET* readings);
	static void	useFilteredData(OUTPUT_HANDLE *outHandle,
					READINGSET* readings);

	void 		populateAssetTrackingCache(ManagementClient *m_mgtClient);
	bool 		checkAssetTrackingCache(AssetTrackingTuple& tuple);
	void 		addAssetTrackingTuple(AssetTrackingTuple& tuple);

public:
	std::vector<FilterPlugin *>	m_filters;

private:
	StorageClient&			m_storage;
	unsigned long			m_timeout;
	unsigned int			m_queueSizeThreshold;
	bool				m_running;
	std::string 			m_serviceName;
	std::string 			m_pluginName;
	ManagementClient		*m_mgtClient;
	// New data: queued
	std::vector<Reading *>*		m_queue;
	std::mutex			m_qMutex;
	std::mutex			m_statsMutex;
	std::thread*			m_thread;
	std::thread*			m_statsThread;
	Logger*				m_logger;
	std::condition_variable		m_cv;
	std::condition_variable		m_statsCv;
	// Data ready to be filtered/sent
	std::vector<Reading *>*		m_data;
	unsigned int			m_discardedReadings; // discarded readings since last update to statistics table
	
	std::unordered_set<AssetTrackingTuple*, std::hash<AssetTrackingTuple*>, AssetTrackingTuplePtrEqual>   assetTrackerTuplesCache;
	std::unordered_set<std::string>   		statsDbEntriesCache;  // confirmed stats table entries
	std::map<std::string, int>		statsPendingEntries;  // pending stats table entries
};

#endif
