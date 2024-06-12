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
 * Singleton class to manage SQLite3 Memory connection pool
 */
class MemConnectionManager {
	public:
		static MemConnectionManager  *getInstance();
		void                         growPool(unsigned int);
		unsigned int                 shrinkPool(unsigned int);
		Connection                   *allocate();
		void                         release(Connection *);
		void		   	     shutdown();
		void			     setError(const char *, const char *, bool);
		PLUGIN_ERROR		     *getError()
					     {
						return &lastError;
					     }
		void			     setPersist(bool persist, const std::string& filename = "")
					     {
						     m_persist = persist;
						     m_filename = filename;
					     }
		bool			     persist() { return m_persist; };
		std::string		     filename() { return m_filename; };
		void			     setPurgeBlockSize(unsigned long purgeBlockSize);

	private:
		MemConnectionManager();
		static MemConnectionManager  *instance;
		std::list<Connection *>      idle;
		std::list<Connection *>      inUse;
		std::mutex                   idleLock;
		std::mutex                   inUseLock;
		std::mutex                   errorLock;
		PLUGIN_ERROR		     lastError;
		bool			     m_trace;
		bool			     m_persist;
		std::string		     m_filename;
		unsigned long		     m_purgeBlockSize;
};

#endif
