#ifndef _DATA_SENDER_H
#define _DATA_SENDER_H

#include <north_plugin.h>
#include <reading_set.h>
#include <logger.h>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <perfmonitors.h>

// Send statistics to storage in seconds
#define FLUSH_STATS_INTERVAL 5
// Failure counter before re-recreating statics rows
#define STATS_UPDATE_FAIL_THRESHOLD 3

class DataLoad;
class NorthService;

class DataSender {
	public:
		DataSender(NorthPlugin *plugin, DataLoad *loader, NorthService *north);
		~DataSender();
		void			sendThread();
		void			updatePlugin(NorthPlugin *plugin) { m_plugin = plugin; };
		void			pause();
		void			release();
		void			setPerfMonitor(PerformanceMonitor *perfMonitor) { m_perfMonitor = perfMonitor; };
		bool			isRunning() { return !m_shutdown; };
		void			flushStatistics();
	private:
		void			updateStatistics(uint32_t increment);
		bool 			createStats(const std::string &key, int value);
		unsigned long		send(ReadingSet *readings);
		void			blockPause();
		void			releasePause();
	private:
		NorthPlugin		*m_plugin;
		DataLoad		*m_loader;
		NorthService		*m_service;
		volatile bool		m_shutdown;
		std::thread		*m_thread;
		Logger			*m_logger;
		bool			m_paused;
		bool			m_sending;
		std::mutex		m_pauseMutex;
		std::condition_variable m_pauseCV;
		PerformanceMonitor	*m_perfMonitor;
		// Statistics send via thread
		std::thread		*m_statsThread;
		std::mutex		m_flushStatsMtx;
		// Statistics save map
		std::condition_variable m_statsCv;
		std::mutex		m_statsMtx;
		std::map<std::string, int>
					m_statsPendingEntries;
		int			m_statsUpdateFails;
		// confirmed stats table entries
		std::unordered_set<std::string>
					m_statsDbEntriesCache;
};
#endif
