#ifndef _CONNECTION_MANAGER_H
#define _CONNECTION_MANAGER_H

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

	private:
		ConnectionManager();
		static ConnectionManager     *instance;
		std::list<Connection *>      idle;
		std::list<Connection *>      inUse;
		std::mutex                   idleLock;
		std::mutex                   inUseLock;
		std::mutex                   errorLock;
		PLUGIN_ERROR		     lastError;
};

#endif
