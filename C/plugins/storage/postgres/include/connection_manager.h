#ifndef _CONNECTION_MANAGER_H
#define _CONNECTION_MANAGER_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <plugin_api.h>
#include <list>
#include <mutex>

class Connection;

/**
 * Singleton class to manage Postgres connection pool
 */
class ConnectionManager {
	public:
		static ConnectionManager  *getInstance();
		void                      growPool(unsigned int);
		unsigned int              shrinkPool(unsigned int);
		Connection                *allocate();
		void                      release(Connection *);
		void			  shutdown();
		void			  setError(const char *, const char *, bool);
		PLUGIN_ERROR		  *getError()
					  {
						return &lastError;
					  }
		void			  setMaxReadingRows(long rows)
					  {
						  m_maxReadingRows = rows;
					  }

	private:
		ConnectionManager();
		static ConnectionManager     *instance;
		std::list<Connection *>      idle;
		std::list<Connection *>      inUse;
		std::mutex                   idleLock;
		std::mutex                   inUseLock;
		std::mutex                   errorLock;
		PLUGIN_ERROR		     lastError;
		bool			     m_logSQL;
		long			     m_maxReadingRows;
};

#endif
