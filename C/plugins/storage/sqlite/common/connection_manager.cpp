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
#include <sys/time.h>
#include <sys/resource.h>

#include <connection_manager.h>
#include <connection.h>
#include <readings_catalogue.h>
#include <logger.h>

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
ConnectionManager::ConnectionManager() : m_shutdown(false),
					m_vacuumInterval(6 * 60 * 60),
					m_attachedDatabases(0)
{
	lastError.message = NULL;
	lastError.entryPoint = NULL;
	if (getenv("FLEDGE_TRACE_SQL"))
		m_trace = true;
	else
		m_trace = false;
	m_background = new std::thread(managerBackground, this);

        struct rlimit lim;
        getrlimit(RLIMIT_NOFILE, &lim);
	m_descriptorLimit = lim.rlim_cur;

	
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
 * Grow the connection pool by the number of connections
 * specified.
 *
 * @param delta	The number of connections to add to the pool
 */
void ConnectionManager::growPool(unsigned int delta)
{
	int poolSize = idle.size() + inUse.size();

	if ((delta + poolSize) * m_attachedDatabases * NO_DESCRIPTORS_PER_DB
			> (DESCRIPTOR_THRESHOLD * m_descriptorLimit) / 100)
	{
		Logger::getLogger()->warn("Request to grow database connection pool rejected"
			       " due to excessive file descriptor usage");
		return;
	}
	int failures = 0;
	while (delta-- > 0)
	{
		try {
			Connection *conn = new Connection();
			if (m_trace)
				conn->setTrace(true);
			idleLock.lock();
			idle.push_back(conn);
			idleLock.unlock();
		} catch (...) {
			failures++;
		}
	}
	if (failures > 0)
	{
		idleLock.lock();
		int idleCount = idle.size();
		idleLock.unlock();
		inUseLock.lock();
		int inUseCount = inUse.size();
		inUseLock.unlock();
		Logger::getLogger()->warn("Connection pool growth restricted due to failure to create %d connections, %d idle connections & %d connection in use currently", failures, idleCount, inUseCount);
		noConnectionsDiagnostic();
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
		try {
			conn = new Connection();
		} catch (...) {
			conn = NULL;
			Logger::getLogger()->error("Failed to create database connection to allocate");
			noConnectionsDiagnostic();
		}
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

	int poolSize = idle.size() + inUse.size();
	if (poolSize * m_attachedDatabases * NO_DESCRIPTORS_PER_DB 
			> (DESCRIPTOR_THRESHOLD * m_descriptorLimit) / 100)
	{
		Logger::getLogger()->warn("Request to attach new database rejected"
			       " due to excessive file descriptor usage");
		return false;
	}
	result = true;

	sqlCmd = "ATTACH DATABASE '" + path + "' AS " + alias + ";";

	idleLock.lock();
	inUseLock.lock();

	// attach the DB to all idle connections
	for (auto conn : idle)
	{
		dbHandle = conn->getDbHandle();
		rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
		if (rc != SQLITE_OK)
		{
			Logger::getLogger()->error("attachNewDb - It was not possible to attach the db :%s: to an idle connection, error :%s:", path.c_str(), zErrMsg);
			sqlite3_free(zErrMsg);
			result = false;
			// TODO We are potentially left in an inconsistant state with the new database
			// attached to some connections but not all. 
			break;
		}


		Logger::getLogger()->debug("attachNewDb idle dbHandle :%X: sqlCmd :%s: ", dbHandle, sqlCmd.c_str());

	}

	if (result)
	{
		// attach the DB to all inUse connections
		for (auto conn : inUse)
		{
			dbHandle = conn->getDbHandle();
			rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
			if (rc != SQLITE_OK)
			{
				Logger::getLogger()->error("attachNewDb - It was not possible to attach the db :%s: to an inUse connection, error :%s:", path.c_str() ,zErrMsg);
				sqlite3_free(zErrMsg);
				result = false;
				// TODO We are potentially left in an inconsistant state with the new
				// database attached to some connections but not all. 
				break;
			}

			Logger::getLogger()->debug("attachNewDb inUse dbHandle :%X: sqlCmd :%s: ", dbHandle, sqlCmd.c_str());
		}
	}
	m_attachedDatabases++;

	inUseLock.unlock();
	idleLock.unlock();

	return (result);
}

/**
 * Detach a database from all the connections
 *
 */
bool ConnectionManager::detachNewDb(std::string &alias)
{
	int rc;
	std::string sqlCmd;
	sqlite3 *dbHandle;
	bool result;
	char *zErrMsg = NULL;

	result = true;

	sqlCmd = "DETACH  DATABASE " + alias + ";";
	Logger::getLogger()->debug("detachDb - db alias :%s: cmd :%s:" ,  alias.c_str() , sqlCmd.c_str() );

	idleLock.lock();
	inUseLock.lock();

	// attach the DB to all idle connections
	for (auto conn : idle)
	{
		dbHandle = conn->getDbHandle();
		rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
		if (rc != SQLITE_OK)
		{
			Logger::getLogger()->error("detachNewDb - It was not possible to detach the db :%s: from an idle connection, error :%s:", alias.c_str(), zErrMsg);
			sqlite3_free(zErrMsg);
			result = false;
			break;
		}
		Logger::getLogger()->debug("detachNewDb - idle dbHandle :%X: sqlCmd :%s: ", dbHandle, sqlCmd.c_str());
	}

	if (result)
	{
		// attach the DB to all inUse connections
		for (auto conn : inUse)
		{
			dbHandle = conn->getDbHandle();
			rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
			if (rc != SQLITE_OK)
			{
				Logger::getLogger()->error("detachNewDb - It was not possible to detach the db :%s: from an inUse connection, error :%s:", alias.c_str() ,zErrMsg);
				sqlite3_free(zErrMsg);
				result = false;
				break;
			}
			Logger::getLogger()->debug("detachNewDb - inUse dbHandle :%X: sqlCmd :%s: ", dbHandle, sqlCmd.c_str());
		}
	}
	m_attachedDatabases--;

	inUseLock.unlock();
	idleLock.unlock();

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

	int poolSize = idle.size() + inUse.size();
	if (poolSize * m_attachedDatabases * NO_DESCRIPTORS_PER_DB 
			> (DESCRIPTOR_THRESHOLD * m_descriptorLimit) / 100)
	{
		Logger::getLogger()->warn("Request to attach nwe database rejected"
			       " due to excessive file descriptor usage");
		return false;
	}
	result = true;

	idleLock.lock();
	inUseLock.lock();

	// attach the DB to all idle connections
	for (auto conn : idle)
	{
		if (dbHandle == conn->getDbHandle())
		{
			Logger::getLogger()->debug("attachRequestNewDb - idle skipped dbHandle :%X: sqlCmd :%s: ", conn->getDbHandle(), sqlCmd.c_str());

		} else
		{
			conn->setUsedDbId(newDbId);

			Logger::getLogger()->debug("attachRequestNewDb - idle, dbHandle :%X: sqlCmd :%s: ", conn->getDbHandle(), sqlCmd.c_str());
		}

	}

	if (result)
	{
		// attach the DB to all inUse connections
		{

			for (auto conn : inUse) {

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
	m_attachedDatabases++;

	inUseLock.unlock();
	idleLock.unlock();

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
#if TRACK_CONNECTION_USER
	conn->clearUsage();
#endif
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
			if (*errMsg)
			{
				sqlite3_free(*errMsg);
				*errMsg = NULL;
			}
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

/**
 * Background thread used to execute periodic tasks and oversee the database activity.
 *
 * We will run the SQLite vacuum command periodically to allow space to be reclaimed
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

/**
 * Determine if we can allow another database to be created and attached to all the
 * connections.
 *
 * @return True if we can create anotehr database.
 */
bool ConnectionManager::allowMoreDatabases()
{
	// Allow for a couple of user defined schemas as well as the fledge database
	if (m_attachedDatabases + 4 > ReadingsCatalogue::getInstance()->getMaxAttached())
	{
		return false;
	}
	int poolSize = idle.size() + inUse.size();
	if (poolSize * (m_attachedDatabases + 1) * NO_DESCRIPTORS_PER_DB 
			> (DESCRIPTOR_THRESHOLD * m_descriptorLimit) / 100)
	{
		return false;
	}
	return true;
}

void ConnectionManager::noConnectionsDiagnostic()
{
#if TRACK_CONNECTION_USER
	Logger *logger = Logger::getLogger();

	inUseLock.lock();
	logger->warn("There are %d connections in use currently", inUse.size());
	for (auto conn : inUse)
	{
		logger->warn("  Connection is use by %s", conn->getUsage().c_str());
	}
	inUseLock.unlock();
#endif
}
