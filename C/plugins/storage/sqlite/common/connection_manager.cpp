/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
// FIXME_I:
#include <sqlite3.h>
#include <unistd.h>

#include <connection_manager.h>
#include <connection.h>
#include <logger.h>



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
			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("xxx5 shrinkPool :%X:", conn->getDbHandle());
			Logger::getLogger()->setMinLevel("warning");


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
		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("xxx5 ConnectionManager::allocate");
		Logger::getLogger()->setMinLevel("warning");


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

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx attachNewDb Start");
	Logger::getLogger()->setMinLevel("warning");


	idleLock.lock();
	inUseLock.lock();

	// attach the DB to all idle connections
	{

		for ( auto conn : idle) {

			dbHandle = conn->getDbHandle();
			// FIXME_I:
			//rc = sqlite3_exec(dbHandle, sqlCmd.c_str(), NULL, NULL, &zErrMsg);
			rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
			if (rc != SQLITE_OK)
			{
				Logger::getLogger()->error("attachNewDb - It was not possible to attach the db :%s: to an idle connection, error :%s:", path.c_str(), zErrMsg);
				result = false;
				break;
			}

			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("xxx attachNewDb idle :%s: :%X: ", sqlCmd.c_str(), dbHandle);
			Logger::getLogger()->setMinLevel("warning");

		}
	}

	if (result)
	{
		// attach the DB to all inUse connections
		{

			for ( auto conn : inUse) {

				dbHandle = conn->getDbHandle();
				// FIXME_I:
				//rc = sqlite3_exec(dbHandle, sqlCmd.c_str(), NULL, NULL, &zErrMsg);
				rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
				if (rc != SQLITE_OK)
				{
					Logger::getLogger()->error("attachNewDb - It was not possible to attach the db :%s: to an inUse connection, error :%s:", path.c_str() ,zErrMsg);
					result = false;
					break;
				}

				//# FIXME_I
				Logger::getLogger()->setMinLevel("debug");
				Logger::getLogger()->debug("xxx attachNewDb inUse :%s: :%X:  ", sqlCmd.c_str(), dbHandle);
				Logger::getLogger()->setMinLevel("warning");

			}
		}
	}
	idleLock.unlock();
	inUseLock.unlock();

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx attachNewDb Exit");
	Logger::getLogger()->setMinLevel("warning");

	return (result);
}

// FIXME_I:
bool ConnectionManager::attachRequestNewDb(int newDbId)
{
	int rc;
	std::string sqlCmd;
	sqlite3 *dbHandle;
	bool result;
	char *zErrMsg = NULL;

	result = true;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx attachRequestNewDb Start");
	Logger::getLogger()->setMinLevel("warning");


	idleLock.lock();
	inUseLock.lock();

	// attach the DB to all idle connections
	{

		for ( auto conn : idle) {

			conn->setUsedDbId(newDbId);

			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("xxx attachRequestNewDb idle :%s: :%X: ", sqlCmd.c_str(), dbHandle);
			Logger::getLogger()->setMinLevel("warning");

		}
	}

	if (result)
	{
		// attach the DB to all inUse connections
		{

			for ( auto conn : inUse) {

				conn->setUsedDbId(newDbId);
				//# FIXME_I
				Logger::getLogger()->setMinLevel("debug");
				Logger::getLogger()->debug("xxx attachRequestNewDb inUse :%s: :%X:  ", sqlCmd.c_str(), dbHandle);
				Logger::getLogger()->setMinLevel("warning");

			}
		}
	}
	idleLock.unlock();
	inUseLock.unlock();

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx attachRequestNewDb Exit");
	Logger::getLogger()->setMinLevel("warning");

	return (result);
}


//// FIXME_I:xxx
/**
 * Attach a database to all the connections, idle and  inuse
 *
 * @param path  - path of the database to attach
 * @param alias - alias to be assigned to the attached database
 */
void ConnectionManager::listConnections()
{
	int rc;
	std::string sqlCmd;
	sqlite3 *dbHandle;
	bool result;
	char *zErrMsg = NULL;

	result = true;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx listConnections");


	idleLock.lock();
	inUseLock.lock();

	// attach the DB to all idle connections
	for ( auto conn : idle) {

		dbHandle = conn->getDbHandle();
		Logger::getLogger()->debug("listConnections - idle :%X:", dbHandle);
		listReadingAvailable(dbHandle);
	}


	for ( auto conn : inUse) {

		dbHandle = conn->getDbHandle();
		Logger::getLogger()->debug("listConnections - inUse :%X:", dbHandle);
		listReadingAvailable(dbHandle);
	}

	idleLock.unlock();
	inUseLock.unlock();

	//# FIXME_I
	Logger::getLogger()->debug("xxx listConnections end");

}

// FIXME_I:
void ConnectionManager::listReadingAvailable(sqlite3 *dbHandle)
{
	using namespace std;

	string dbName;
	int nCols;
	int id;
	char *asset_name;
	sqlite3_stmt *stmt;
	int rc;
	string tableName;
	int dbId;
	vector<int> dbIdList;

	//# FIXME_I
	Logger::getLogger()->debug("xxx listReadingAvailable start");


	ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
	readCat->getAllDbs(dbIdList);

	for(int dbId : dbIdList)
	{

		dbName = READINGS_DB_NAME_BASE "_" + to_string(dbId);

		string sql_cmd = R"(
			SELECT name
			FROM  )" + dbName + R"(.sqlite_master
			WHERE type='table' and name like 'readings_%';
		)";

		Logger::getLogger()->debug("xxx listReadingAvailable sql_cmd :%s:" ,sql_cmd.c_str());

		if (sqlite3_prepare_v2(dbHandle, sql_cmd.c_str(), -1, &stmt, NULL) != SQLITE_OK)
		{
			Logger::getLogger()->error("xxx listReadingAvailable s1");
		}
		else
		{
			while ((rc = sqlite3_step(stmt)) == SQLITE_ROW)
			{
				nCols = sqlite3_column_count(stmt);

				tableName = (char *) sqlite3_column_text(stmt, 0);
				id = stoi(tableName.substr(tableName.find('_') + 1));

				Logger::getLogger()->error("xxx listReadingAvailable :%X: db :%s: table :%s:", dbHandle, dbName.c_str(), tableName.c_str());
			}
			sqlite3_finalize(stmt);
		}
	}

	Logger::getLogger()->debug("xxx listReadingAvailable end");




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
 * @param	db	     The open SQLite database
 * @param	sql	     The SQL to execute
 * @param	errmsg	 Error message
 */
int ConnectionManager::SQLExec(sqlite3 *dbHandle, const char *sqlCmd, char **errMsg)
{
	int retries = 0, rc;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");

	Logger::getLogger()->debug("xxx SQLExec start: cmd :%s: ", sqlCmd);

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

		retries++;
		if (rc != SQLITE_OK)
		{
			int interval = (retries * RETRY_BACKOFF);
			usleep(interval);	// sleep retries milliseconds
			if (retries > 5)
					Logger::getLogger()->info("xxx SQLExec - error :%s: retry %d of %d, rc=%s, DB connection @ %p, slept for %d msecs",
											  sqlite3_errmsg(dbHandle), retries, MAX_RETRIES, (rc==SQLITE_LOCKED)?"SQLITE_LOCKED":"SQLITE_BUSY", this, interval);
		}
	} while (retries < MAX_RETRIES && (rc  != SQLITE_OK));

	if (rc == SQLITE_LOCKED)
	{
		Logger::getLogger()->error("xxx SQLExec - Database still locked after maximum retries");
	}
	if (rc == SQLITE_BUSY)
	{
		Logger::getLogger()->error("xxx SQLExec - Database still busy after maximum retries");
	}

	// FIXME_I:
	Logger::getLogger()->debug("xxx SQLExec start: end :%s: ", sqlCmd);
	Logger::getLogger()->setMinLevel("warning");

	return rc;
}
