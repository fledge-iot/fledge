/*
 * Fledge database handler class
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#ifndef _DATABASEHANDLER_H
#define _DATABASEHANDLER_H

#include <logger.h>
#include <dbcb.h>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <thread>

/**
 * A database handler class that handles the insert, update
 * and delete operations for one or more SQLite Databases
 */
class DatabaseHandler {
        public:
                DatabaseHandler();
                ~DatabaseHandler();
		bool		queueRequest(DBCB *request);
		void		handler();
		static void	handlerEntry(void *);
        private:
                Logger          *m_logger;
		std::mutex	m_mutex;
		std::condition_variable
				m_cv;
		std::queue<DBCB *>
				m_queue;
		std::thread	*m_thread;
		bool		m_shutdown;
};

#endif
