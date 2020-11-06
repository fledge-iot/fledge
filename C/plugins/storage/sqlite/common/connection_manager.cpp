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
#include <unistd.h>

#include <connection_manager.h>
#include <connection.h>
#include <logger.h>

#define LOG_ALL_ERRORS	1

ConnectionManager *ConnectionManager::instance = 0;

/**
 * Default constructor for the connection manager.
 */
ConnectionManager::ConnectionManager()
{
	lastError.message = NULL;
	lastError.entryPoint = NULL;
	if (getenv("FLEDGE_TRACE_SQL"))
		m_trace = true;
	else
		m_trace = false;
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
 * Attach a database to all the connections, idle and  inuse
 *
 * @param path  - path of the database to attach
 * @param alias - alias to be assigned to the attached database
 */
bool ConnectionManager::attachNewDb(std::string &path, std::string &alias)
{
	int rc;
	std::string sqlCmd;
	sqlite3 *dbHandle;
	bool result;
	char *zErrMsg = NULL;

	result = true;

	sqlCmd = "ATTACH DATABASE '" + path + "' AS " + alias + ";";

	idleLock.lock();
	inUseLock.lock();

	// attach the DB to all idle connections
	{

		for ( auto conn : idle) {

			dbHandle = conn->getDbHandle();
			rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
			if (rc != SQLITE_OK)
			{
				Logger::getLogger()->error("attachNewDb - It was not possible to attach the db :%s: to an idle connection, error :%s:", path.c_str(), zErrMsg);
				result = false;
				break;
			}

			Logger::getLogger()->debug("attachNewDb idle dbHandle :%X: sqlCmd :%s: ", sqlCmd.c_str(), dbHandle);

		}
	}

	if (result)
	{
		// attach the DB to all inUse connections
		{

			for ( auto conn : inUse) {

				dbHandle = conn->getDbHandle();
				rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
				if (rc != SQLITE_OK)
				{
					Logger::getLogger()->error("attachNewDb - It was not possible to attach the db :%s: to an inUse connection, error :%s:", path.c_str() ,zErrMsg);
					result = false;
					break;
				}

				Logger::getLogger()->debug("attachNewDb inUse dbHandle :%X: sqlCmd :%s: ", sqlCmd.c_str(), dbHandle);
			}
		}
	}
	idleLock.unlock();
	inUseLock.unlock();

	return (result);
}

/**
 * Adds to all the connections a request to attach a database
 *
 *  *
 * @param newDbId  - database id to attach
 * @param dbHandle - dbhandle for which the attach request should NOT be added
 *
 */
bool ConnectionManager::attachRequestNewDb(int newDbId, sqlite3 *dbHandle)
{
	int rc;
	std::string sqlCmd;
	bool result;
	char *zErrMsg = NULL;

	result = true;

	idleLock.lock();
	inUseLock.lock();

	// attach the DB to all idle connections
	{

		for ( auto conn : idle) {

			if (dbHandle == conn->getDbHandle())
			{
				Logger::getLogger()->debug("attachRequestNewDb - idle skipped dbHandle :%X: sqlCmd :%s: ", conn->getDbHandle(), sqlCmd.c_str());

			} else
			{
				conn->setUsedDbId(newDbId);

				Logger::getLogger()->debug("attachRequestNewDb - idle, dbHandle :%X: sqlCmd :%s: ", conn->getDbHandle(), sqlCmd.c_str());
			}

		}
	}

	if (result)
	{
		// attach the DB to all inUse connections
		{

			for ( auto conn : inUse) {

				if (dbHandle == conn->getDbHandle())
				{
					Logger::getLogger()->debug("attachRequestNewDb - inUse skipped dbHandle :%X: sqlCmd :%s: ", conn->getDbHandle(), sqlCmd.c_str());
				} else
				{
					conn->setUsedDbId(newDbId);

					Logger::getLogger()->debug("attachRequestNewDb - inUse, dbHandle :%X: sqlCmd :%s: ", conn->getDbHandle(), sqlCmd.c_str());
				}
			}
		}
	}
	idleLock.unlock();
	inUseLock.unlock();

	return (result);
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

#define MAX_RETRIES			40	// Maximum no. of retries when a lock is encountered
#define RETRY_BACKOFF			100	// Multipler to backoff DB retry on lock

/**
 * SQLIte wrapper to retry statements when the database is locked
 *
 */
int ConnectionManager::SQLExec(sqlite3 *dbHandle, const char *sqlCmd, char **errMsg)
{
	int retries = 0, rc;


	do {
		if (errMsg == NULL)
		{
			rc = sqlite3_exec(dbHandle, sqlCmd, NULL, NULL, NULL);
		}
		else
		{
			rc = sqlite3_exec(dbHandle, sqlCmd, NULL, NULL, errMsg);
			Logger::getLogger()->debug("SQLExec: rc :%d: ", rc);
		}

		if (rc != SQLITE_OK)
		{
			int interval = (retries * RETRY_BACKOFF);
			usleep(interval);	// sleep retries milliseconds
			if (retries > 5)
			{
				Logger::getLogger()->warn("ConnectionManager::SQLExec - error :%s: dbHandle :%X: sqlCmd :%s: retry :%d: of :%d:",
										  sqlite3_errmsg(dbHandle),
										  dbHandle,
										  sqlCmd,
										  rc,
										  MAX_RETRIES);
			}
			retries++;
		}
	} while (retries < MAX_RETRIES && (rc  != SQLITE_OK));

	if (rc == SQLITE_LOCKED)
	{
		Logger::getLogger()->error("ConnectionManager::SQLExec - Database still locked after maximum retries");
	}
	if (rc == SQLITE_BUSY)
	{
		Logger::getLogger()->error("ConnectionManager::SQLExec - Database still busy after maximum retries");
	}

	return rc;
}
