#ifndef _DATA_SENDER_H
#define _DATA_SENDER_H

#include <north_plugin.h>
#include <reading_set.h>
#include <logger.h>
#include <thread>

class DataLoad;

class DataSender {
	public:
		DataSender(NorthPlugin *plugin, DataLoad *loader);
		~DataSender();
		void			sendThread();
	private:
		long			send(ReadingSet *readings);
	private:
		NorthPlugin		*m_plugin;
		DataLoad		*m_loader;
		bool			m_shutdown;
		std::thread		*m_thread;
		Logger			*m_logger;
};
#endif
