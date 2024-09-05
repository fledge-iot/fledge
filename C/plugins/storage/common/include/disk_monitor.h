#ifndef _DISK_SPACE_MONITOR_H
#define _DISK_SPACE_MONITOR_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <logger.h>

#define CHECK_THRESHOLD		300	// check every 5 minutes
/**
 * A class to monitor the free disk space used to store
 * the various storage databases
 */
class DiskSpaceMonitor {
	public:
		DiskSpaceMonitor(const std::string& db1, const std::string& db2);
		void		periodic(int interval);
	private:
		std::string	m_dbPath1;
		std::string	m_dbPath2;
		bool		m_started;
		bool		m_sameDevice;
		unsigned int	m_lastCheck;
		Logger		*m_logger;
		double		m_lastPerc1;
		double		m_lastPerc2;
		double		m_lastPrediction1;
		double		m_lastPrediction2;
};
#endif
