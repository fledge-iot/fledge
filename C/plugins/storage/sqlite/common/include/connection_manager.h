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

#define NO_DESCRIPTORS_PER_DB	3	// 3 deascriptors per database when using WAL mode
#define DESCRIPTOR_THRESHOLD	75	// Percentage of descriptors that can be used on database connections

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
		bool 			  detachNewDb(std::string &alias);
		void                      release(Connection *);
		void			  shutdown();
		void			  setError(const char *, const char *, bool);
		PLUGIN_ERROR		  *getError()
					  {
						return &lastError;
					  }
		void			  background();
		void			  setVacuumInterval(long hours)
					  {
						m_vacuumInterval = 60 * 60 * hours;
					  };
		bool			  allowMoreDatabases();

	protected:
		ConnectionManager();

	private:
		static ConnectionManager     *instance;
		int		       	     SQLExec(sqlite3 *dbHandle, const char *sqlCmd,
							char **errMsg);
		void			     noConnectionsDiagnostic();

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
		unsigned int		     m_descriptorLimit;
		unsigned int		     m_attachedDatabases;
};

#endif
