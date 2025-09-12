/*
 * Fledge readings ingest rate.
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <ingest_rate.h>
#include <thread>
#include <logger.h>

using namespace std;

/**
 * Constructor for ingest rate class
 *
 * @param mgmtClient	The management Client interface
 */
IngestRate::IngestRate(ManagementClient *mgmtClient, const std::string& service) : m_mgmtClient(mgmtClient), m_service(service),
	m_currentInterval(0), m_thisInterval(0), m_mean(0), m_dsq(0), m_count(0), m_factor(3), m_alerted(false), m_primed(false)
{
	m_numIntervals = 60 / FLUSH_STATS_INTERVAL;
}

/**
 * Destructor for the ingest rate class
 */
IngestRate::~IngestRate()
{
}

/**
 * Update the configuration of the ingest rate mechanism
 *
 * @param interval	Number of minutes to average over
 * @param factor	Number of standard deviations to tolarate
 */
void IngestRate::updateConfig(int interval, int factor)
{
	bool restart = false;
	if (interval * 60 != m_numIntervals * FLUSH_STATS_INTERVAL)
	{
		m_numIntervals = (interval * 60) / FLUSH_STATS_INTERVAL;
		restart = true;
	}
	if (m_factor != factor)
	{
		m_factor = factor;
	}
	if (restart)
	{
		relearn();
	}
}

/**
 * The configuration has changed so we need to reset our state
 * and go back into the mode of determining what a good mean and
 * standard deviation is for the select interval.
 */
void IngestRate::relearn()
{
	lock_guard<mutex> guard(m_mutex);
	m_count = 0;
	m_thisInterval = 0;
	m_currentInterval = 0;
	m_dsq = 0;
	m_mean = 0;
}

/**
 * Called each time we ingest any readings.
 *
 * @param numberReadings	The number of readings ingested
 */
void IngestRate::ingest(unsigned int numberReadings)
{
	if (m_numIntervals == 0)
		return;
	lock_guard<mutex> guard(m_mutex);
	m_thisInterval += numberReadings;
}

/**
 * Called periodically by the stats update thread. Called every FLUSH_STATS_INTERVAL seconds
 */
void IngestRate::periodic()
{
	if (m_numIntervals == 0)
		return;
	updateCounters();
}

/**
 * The periodic work that needs to be done holding the mutex
 */
void IngestRate::updateCounters()
{
	lock_guard<mutex> guard(m_mutex);
	m_currentInterval++;
	if (m_currentInterval == m_numIntervals)
	{
		if (m_count > IGRSAMPLES)
		{
			Logger::getLogger()->debug("Ingest rate checking for service %s is enabled", m_service.c_str());
			double sigma = sqrt(m_dsq / m_count);
			if (m_thisInterval < (m_mean - (m_factor * sigma))  || m_thisInterval > (m_mean + (m_factor * sigma)))
			{
				if (m_primed)
				{
					// Outlier detected
					string key = "SouthIngestRate" + m_service;
					string message = "Ingest rate of the south service " +
					       m_service + " falls outside of normal boundaries";
					m_mgmtClient->raiseAlert(key, message);
					Logger::getLogger()->warn("Current ingest rate falls outside normal boundaries, rate is %ld with average rate of %f", m_thisInterval, m_mean);
					m_alerted = true;
				}
				else
				{
					// We have had one outlier, prime the alert on the second consequtive outlier
					m_primed = true;
				}
			}
			else if (m_alerted)
			{
				string key = "SouthIngestRate" + m_service;
				m_mgmtClient->clearAlert(key);
				m_primed = false;
				m_alerted = false;
			}
			else
			{
				m_primed = false;
			}
		}
		m_count++;
		double meanDiff = (m_thisInterval - m_mean) / m_count;
		double newMean = m_mean + meanDiff;
		double dsqInc = (m_thisInterval - newMean) * (m_thisInterval - m_mean);
		m_dsq += dsqInc;
		m_mean = newMean;
		m_thisInterval = 0;
		m_currentInterval = 0;
	}
}
