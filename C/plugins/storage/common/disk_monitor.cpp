/*
 * Fledge storage service.
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <disk_monitor.h>
#include <logger.h>
#include <sys/vfs.h>
#include <string.h>

using namespace std;

/**
 * Construct a disk space monitor class
 *
 * It monitors the free space on two path, since the storage service may use
 * different locations for reading and configuration storage. If they are both
 * the same file system then the monitor is only done once.
 *
 * If the free space falls below 5% a fatal error is written to the error log
 * If it falls below 10% a warning is written advising that disk space should be released
 * It attempts to predict when storage will become exhausted. If it is less then 14 days
 * it will report this to the error log once a day.
 * If it is less than 72 hours it will report this once per hour.
 *
 * All reporting is to the system log
 *
 * NB In an ideal world we would make the thresholds and reporting interval configurable,
 * however we are running within the limited environment of a storage plugin and do not
 * have access to the manaagement client or configuration subsystem.
 */
DiskSpaceMonitor::DiskSpaceMonitor(const string& path1, const string& path2) :
	m_dbPath1(path1), m_dbPath2(path2), m_started(false), m_sameDevice(false), m_lastCheck(0),
	m_lastPerc1(0.0), m_lastPerc2(0.0), m_lastPrediction1(0.0), m_lastPrediction2(0.0), m_reported(0)
{
	m_logger = Logger::getLogger();
}

/**
 * Called periodically to monitor the disk usage
 *
 * @param interval	The number of seconds between calls
 */
void DiskSpaceMonitor::periodic(int interval)
{
	struct statfs stf1, stf2;

	if (!m_started)
	{
		// We have not yet started to monitor the disk usage.
		// Do the initial statfs calls to see if the configuration
		// and readings are on the same filesystem. If they are we 
		// only monitor one of them
		//
		// If the statfs fails log it and do not start monitoring. The
		// rate at which logs are created is limited to prevent flooding
		// the error log.
		if (statfs(m_dbPath1.c_str(), &stf1) != 0)
		{
			if (m_reported == 0)
			{
				m_logger->error("Can't statfs %s, %s. Disk space monitoring is disabled",
						m_dbPath1.c_str(), strerror(errno));
				m_reported++;
			}
			else if (++m_reported > FAILED_DISK_MONITOR_REPORT_INTERVAL)
			{
				m_reported = 0;
			}
			return;
		}
		if (statfs(m_dbPath2.c_str(), &stf2) != 0)
		{
			if (m_reported == 0)
			{
				m_logger->error("Can't statfs %s, %s. Disk space monitoring is disabled",
						m_dbPath2.c_str(), strerror(errno));
				m_reported++;
			}
			else if (++m_reported > FAILED_DISK_MONITOR_REPORT_INTERVAL)
			{
				m_reported = 0;
			}
			return;
		}
		if (memcmp(&stf1.f_fsid, &stf2.f_fsid, sizeof(fsid_t)) == 0)	// Same filesystem
		{
			m_sameDevice = true;
		}
		m_started = true;
	}
	m_lastCheck += interval;

	if (m_lastCheck < CHECK_THRESHOLD)
	{
		// Do not check too frerquently
		return;
	}
	m_lastCheck = 0;

	
	if (statfs(m_dbPath1.c_str(), &stf1) == 0)
	{
		unsigned long freespace = (unsigned long)stf1.f_bavail;
		unsigned long totalspace = (unsigned long)stf1.f_blocks;

		double perc = (double)(freespace  * 100.0) / totalspace;

		if (perc < 5.0)
		{
			m_logger->fatal("Disk space is critically low. Urgent action required, continuing may result in data corruption");
		}
		else if (perc < 10.0)
		{
			m_logger->error("Available disk space is becoming low, please consider releasing more disk space");
		}
		if (m_lastPerc1 > 0.0)
		{
			double diff = m_lastPerc1 - perc;
			if (diff > 0.0)
			{
				double prediction = (perc * CHECK_THRESHOLD)/ (3600.0 * diff);
				if (prediction <= 72.0 && m_lastPrediction1 - prediction > 1.0)
				{
					m_logger->error("At current rates disk space will be exhausted in %.0f hours", prediction);
					m_lastPrediction1 = prediction;
				}
				else if (prediction / 24.0 <= 14 && (m_lastPrediction1 == 0.0 || m_lastPrediction1 - prediction > 24.0))
				{
					m_lastPrediction1 = prediction;
					m_logger->warn("At current rates disk space will be exhausted in %.1f days", prediction / 24);
				}
			}
			else
			{
				m_lastPrediction1 = 0.0;
			}
		}
		m_lastPerc1 = perc;

	}
	if (m_sameDevice)
	{
		return;
	}
	if (statfs(m_dbPath2.c_str(), &stf1) == 0)
	{
		unsigned long freespace = (unsigned long)stf1.f_bavail;
		unsigned long totalspace = (unsigned long)stf1.f_blocks;

		double perc = (double)(freespace  * 100.0) / totalspace;

		if (perc < 5.0)
		{
			m_logger->fatal("Disk space is critically low. Urgent action required, continuing may result in data corruption");
		}
		else if (perc < 10.0)
		{
			m_logger->error("Available disk space is becoming low, please consider releasing more disk space");
		}
		if (m_lastPerc2 > 0.0)
		{
			double diff = m_lastPerc2 - perc;
			if (diff > 0.0)
			{
				double prediction = (perc * CHECK_THRESHOLD)/ (3600.0 * diff);
				if (prediction <= 72.0 && (m_lastPrediction2 == 0.0 || m_lastPrediction2 - prediction > 1.0))
				{
					m_logger->error("At current rates disk space will be exhausted in %.0f hours", prediction);
					m_lastPrediction2 = prediction;
				}
				else if (prediction / 24.0 <= 14 && m_lastPrediction1 - prediction > 24.0)
				{
					m_lastPrediction2 = prediction;
					m_logger->warn("At current rates disk space will be exhausted in %.1f days", prediction / 24);
				}
			}
			else
			{
				m_lastPrediction2 = 0.0;
			}
		}
		m_lastPerc2 = perc;
	}
}
