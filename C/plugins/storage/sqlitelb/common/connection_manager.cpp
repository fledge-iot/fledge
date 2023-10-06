/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <connection_manager.h>
#include <connection.h>
#include <unistd.h>

ConnectionManager *ConnectionManager::instance = 0;

/**
 * Background thread entry point
 */
static void managerBackground(void *arg)
{
	ConnectionManager *mgr = (ConnectionManager *)arg;
	mgr->background();
}

/**
 * Default constructor for the connection manager.
 */
ConnectionManager::ConnectionManager() : m_shutdown(false), m_vacuumInterval(6 * 60 * 60), m_purgeBlockSize(10000)
{
	lastError.message = NULL;
	lastError.entryPoint = NULL;
	if (getenv("FLEDGE_TRACE_SQL"))
		m_trace = true;
	else
		m_trace = false;
	m_background = new std::thread(managerBackground, this);
}

/**
 * Called at shutdown. Shrink the idle pool, this will
 * have the side effect of closing the connections to the database.
 */
void ConnectionManager::shutdown()
{
	m_shutdown = true;
	shrinkPool(idle.size());
	if (m_background)
		m_background->join();
}

/**
 * Return the singleton instance of the connection manager.
 * if none was created then create it.
 */
ConnectionManager *ConnectionManager::getInstance()
{
	if (instance == 0)
	{
		instance = new ConnectionManager();
	}
	return instance;
}

/**
 * Set the purge block size in each of the connections
 *
 * @param purgeBlockSize	The requested purgeBlockSize
 */
void ConnectionManager::setPurgeBlockSize(unsigned long purgeBlockSize)
{
	m_purgeBlockSize = purgeBlockSize;
	idleLock.lock();
	for (auto& c : idle)
		c->setPurgeBlockSize(purgeBlockSize);
	idleLock.unlock();
}

/**
 * Grow the connection pool by the number of connections
 * specified.
 *
 * @param delta	The number of connections to add to the pool
 */
void ConnectionManager::growPool(unsigned int delta)
{
	while (delta-- > 0)
	{
		Connection *conn = new Connection();
		conn->setPurgeBlockSize(m_purgeBlockSize);
		if (m_trace)
			conn->setTrace(true);
		idleLock.lock();
		idle.push_back(conn);
		idleLock.unlock();
	}
}

/**
 * Attempt to shrink the number of connections in the idle pool
 *
 * @param delta		Number of connections to attempt to remove
 * @return The number of connections removed.
 */
unsigned int ConnectionManager::shrinkPool(unsigned int delta)
{
unsigned int removed = 0;
Connection   *conn;

	while (delta-- > 0)
	{
		idleLock.lock();
		conn = idle.back();
		idle.pop_back();
		idleLock.unlock();
		if (conn)
		{
			delete conn;
			removed++;
		}
		else
		{
			break;
		}
	}
	return removed;
}

/**
 * Allocate a connection from the idle pool. If
 * no connection is available add a new connection
 */
Connection *ConnectionManager::allocate()
{
Connection *conn = 0;

	idleLock.lock();
	if (idle.empty())
	{
		conn = new Connection();
	}
	else
	{
		conn = idle.front();
	    	idle.pop_front();
	}
	idleLock.unlock();
	if (conn)
	{
		inUseLock.lock();
		inUse.push_front(conn);
		inUseLock.unlock();
	}
	return conn;
}

/**
 * Release a connection back to the idle pool for
 * reallocation.
 *
 * @param conn	The connection to release.
 */
void ConnectionManager::release(Connection *conn)
{
	inUseLock.lock();
	inUse.remove(conn);
	inUseLock.unlock();
	idleLock.lock();
	idle.push_back(conn);
	idleLock.unlock();
}

/**
 * Set the last error information for a plugin.
 *
 * @param source	The source of the error
 * @param description	The error description
 * @param retryable	Flag to determien if the error condition is transient
 */
void ConnectionManager::setError(const char *source, const char *description, bool retryable)
{
	errorLock.lock();
	if (lastError.entryPoint)
		free(lastError.entryPoint);
	if (lastError.message)
		free(lastError.message);
	lastError.retryable = retryable;
	lastError.entryPoint = strdup(source);
	lastError.message = strdup(description);
	errorLock.unlock();
}

/**
 * Background thread used to execute periodic tasks and oversee the database activity.
 *
 * We will runt he SQLite vacuum command periodically to allow space to be reclaimed
 */
void ConnectionManager::background()
{
	time_t nextVacuum = time(0) + m_vacuumInterval;

	while (!m_shutdown)
	{
		sleep(15);
		time_t tim = time(0);
		if (m_vacuumInterval && tim > nextVacuum)
		{
			Connection *con = allocate();
			con->vacuum();
			release(con);
			nextVacuum = time(0) + m_vacuumInterval;
		}
	}
}
