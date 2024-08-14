#ifndef _INGEST_RATE_H
#define _INGEST_RATE_H
/*
 * Fledge reading ingest rate.
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <logger.h>
#include <vector>
#include <queue>
#include <chrono>
#include <mutex>
#include <condition_variable>
#include <filter_plugin.h>
#include <filter_pipeline.h>
#include <asset_tracking.h>
#include <service_handler.h>
#include <set>
#include <ingest.h>

/**
 * A class used to track and report on the ingest rates of a data stream
 */
class IngestRate {
	public:
		IngestRate(ManagementClient *mgmtClient);
		~IngestRate();
		void		ingest(unsigned int numberReadings);
		void		periodic();
	private:
		void		updateCounters();
	private:
		ManagementClient	*m_mgmtClient;
		int			m_currentInterval;
		int			m_numIntervals;
		unsigned long		m_perInterval[60 / FLUSH_STATS_INTERVAL];
		unsigned long		m_perMinute[15];
		int			m_currentMinute;
		double			m_lastMinute;
		double			m_last5Minutes;
		double			m_last15Minutes;
		bool			m_fullMinute;
		bool			m_have15;
		bool			m_have5;
		std::mutex		m_mutex;
};
#endif
