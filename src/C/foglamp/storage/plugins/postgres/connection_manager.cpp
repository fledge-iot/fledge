/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <connection_manager.h>
#include <connection.h>


ConnectionManager *ConnectionManager::instance = 0;

/**
 * Default constructor for the connection manager.
 */
ConnectionManager::ConnectionManager()
{
	lastError.message = NULL;
	lastError.entryPoint = NULL;
}

/**
 * Called at shutdown. Shrink the idle pool, this will
 * have the side effect of closing the connections to the database.
 */
void ConnectionManager::shutdown()
{
	shrinkPool(idle.size());
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
