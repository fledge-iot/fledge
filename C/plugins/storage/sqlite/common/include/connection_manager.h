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

#include <sqlite3.h>

#include <plugin_api.h>
#include <list>
#include <mutex>
#include <thread>

class Connection;

/**
 * Singleton class to manage SQLite3 connection pool
 */
class ConnectionManager {
	public:
		static ConnectionManager  *getInstance();
		void                      growPool(unsigned int);
		unsigned int              shrinkPool(unsigned int);
		Connection                *allocate();
		bool                      attachNewDb(std::string &path, std::string &alias);
		bool                      attachRequestNewDb(int newDbId, sqlite3 *dbHandle);
		bool 					  detachNewDb(std::string &alias);
		void                      release(Connection *);
		void			  shutdown();
		void			  setError(const char *, const char *, bool);
		PLUGIN_ERROR		  *getError()
					  {
						return &lastError;
					  }
		void			  background();
		void			  setVacuumInterval(long hours) {
							m_vacuumInterval = 60 * 60 * hours;
						};

	protected:
		ConnectionManager();

	private:
		static ConnectionManager     *instance;
		int SQLExec(sqlite3 *dbHandle, const char *sqlCmd, char **errMsg);

	protected:
		std::list<Connection *>      idle;
		std::list<Connection *>      inUse;
		std::mutex                   idleLock;
		std::mutex                   inUseLock;
		std::mutex                   errorLock;
		PLUGIN_ERROR		     lastError;
		bool			     m_trace;
		bool			     m_shutdown;
		std::thread		     *m_background;
		long                         m_vacuumInterval;
};

#endif
