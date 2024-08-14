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
IngestRate::IngestRate(ManagementClient *mgmtClient) : m_mgmtClient(mgmtClient), m_currentInterval(0),
							m_currentMinute(0), m_fullMinute(false),
							m_have15(false), m_have5(false)
{
	m_numIntervals = 60 / FLUSH_STATS_INTERVAL;
	for (int i = 0; i < m_numIntervals; i++)
		m_perInterval[i] = 0;
	for (int i = 0; i < 15; i++)
		m_perMinute[i] = 0;
}

/**
 * Destructor for the ingest rate class
 */
IngestRate::~IngestRate()
{
}

/**
 * Called each time we ingest any readings.
 *
 * @param numberReadings	The number of readings ingested
 */
void IngestRate::ingest(unsigned int numberReadings)
{
	lock_guard<mutex> guard(m_mutex);
	m_perInterval[m_currentInterval] += numberReadings;
}

/**
 * Called periodically by the stats update thread. Called every FLUSH_STATS_INTERVAL seconds
 */
void IngestRate::periodic()
{
	updateCounters();
	if (m_have15)
	{
		Logger::getLogger()->warn("Ingest rates: %.3f, %03f, %.3f",
				m_last15Minutes, m_last5Minutes, m_lastMinute);
	}
}

/**
 * The periodic work that needs to be done holding the mutex
 */
void IngestRate::updateCounters()
{
	lock_guard<mutex> guard(m_mutex);
	m_currentInterval++;
	if (m_fullMinute || m_currentInterval == m_numIntervals)
	{
		m_fullMinute = true;
		// A minutes worth of data in m_perInterval
		unsigned long tot = 0;
		for (int i = 0; i < m_numIntervals; i++)
		{
			tot += m_perInterval[i];
		}
		m_lastMinute = tot / 60.0;
		if (m_currentInterval == m_numIntervals)
		{
			m_currentInterval = 0;
			// We have completed a minute
			m_perMinute[m_currentMinute] = tot;
			m_currentMinute++;
			if (m_currentMinute >= 15)
			{
				m_currentMinute = 0;
				m_have15 = true;
			}
			if (m_currentMinute >= 5)
			{
				m_have5 = true;
			}
			if (m_have5)
			{
				int i = m_currentMinute  - 1;
				tot = 0;
				for (int j = 0; j < 5; j++)
				{
					if (i < 0)
						i += 15;
					tot += m_perMinute[i];
				}
				m_last5Minutes = tot / (5 * 60);
			}
			if (m_have15)
			{
				tot = 0;
				for (int i = 0; i < 15; i++)
				{
					tot += m_perMinute[i];
				}
				m_last15Minutes = tot / (15 * 60);
			}
		}
	}
	m_perInterval[m_currentInterval] = 0;
}
