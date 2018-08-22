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
#include <condition_variable>
#include <filter_plugin.h>

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
		unsigned int threshold);
	~Ingest();

	void		ingest(const Reading& reading);
	bool		running();
	void		processQueue();
	void		waitForQueue();
	void		updateStats(void);
	int 		createStatsDbEntry(const std::string& assetName);

	static void	passToOnwardFilter(OUTPUT_HANDLE *outHandle,
					   READINGSET* readings);
	static void	useFilteredData(OUTPUT_HANDLE *outHandle,
					READINGSET* readings);

public:
	std::vector<FilterPlugin *>	m_filters;

private:
	StorageClient&			m_storage;
	unsigned long			m_timeout;
	unsigned int			m_queueSizeThreshold;
	bool				m_running;
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
	unsigned int			m_newReadings; // new readings since last update to statistics table
	unsigned int			m_discardedReadings; // discarded readings since last update to statistics table
	std::string			m_readingsAssetName; // asset name extracted from the Reading object
};

#endif
