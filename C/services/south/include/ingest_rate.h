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

#define IGRSAMPLES	10	// The number of samples used to calculate initial average

/**
 * A class used to track and report on the ingest rates of a data stream
 *
 * It collects the number of readings ingested in a configurable period, the
 * period being defined in minutes. It then calculates the mean of the collection
 * rates and the standard deviation. If the current collection rate differs from
 * the averaged collection rate by more than a configured number of standard 
 * deviations an alert is raised. A "priming" mechanism is used to require two
 * consecutive deviations from the norm to be required before an alert is trigger.
 * This reduces the occurance of false positives caused by transient spikes in colection.
 * These spikes may occur when heavy operations are performed on the Fledge instance.
 *
 * When the rate returns to within the number of defined standard deviations of
 * the average then the alert is cleared.
 *
 * Before alerting is enabled a number of the defined time periods, IGRSAMPLES,
 * must have passed, during this time an average is calculated and used for the
 * intial comparision.
 *
 * If the user reconfigures the collection rate of the plugin then the accumulated
 * average is discarded and the process starts again by collecting a new average
 */
class IngestRate {
	public:
		IngestRate(ManagementClient *mgmtClient, const std::string& service);
		~IngestRate();
		void		ingest(unsigned int numberReadings);
		void		periodic();
		void		updateConfig(int interval, int factor);
		void		relearn();
	private:
		void		updateCounters();
	private:
		ManagementClient	*m_mgmtClient;
		std::string		m_service;
		int			m_currentInterval;
		int			m_numIntervals;
		unsigned long		m_thisInterval;
		double			m_mean;
		double			m_dsq;
		unsigned long		m_count;
		double			m_factor;
		std::mutex		m_mutex;
		bool			m_alerted;
		bool			m_primed;
};
#endif
