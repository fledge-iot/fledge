/*
 * Fledge storage service.
 *
 * Copyright (c) 2020 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <connection.h>
#include <connection_manager.h>
#include <common.h>
#include <utils.h>

/**
 * SQLite3 storage plugin for Fledge
 */

using namespace std;
using namespace rapidjson;


// Maximum no. of retries for a DB lock
#define RETRY_BACKOFF 100
#define MAX_RETRIES 10

static time_t connectErrorTime = 0;

#define _DB_NAME              "/readings.db"


/**
 * Create a SQLite3 database connection
 */
Connection::Connection()
{
	string dbPath;
	const char *defaultConnection = getenv("DEFAULT_SQLITE_READINGS_DB_FILE");

	m_logSQL = false;
	m_queuing = 0;
	m_streamOpenTransaction = true;

	if (defaultConnection == NULL)
	{
		// Set DB base path
		dbPath = getDataDir();
		// Add the filename
		dbPath += _DB_NAME;
	}
	else
	{
		dbPath = defaultConnection;
	}

	// Allow usage of URI for filename
	sqlite3_config(SQLITE_CONFIG_URI, 1);

	Logger *logger = Logger::getLogger();

	Logger::getLogger()->warn("Opening readings database %s", dbPath.c_str());

	/**
	 * Make a connection to the database
	 * and check backend connection was successfully made
	 * Note:
	 *   we assume the database already exists, so the flag
	 *   SQLITE_OPEN_CREATE is not added in sqlite3_open_v2 call
	 */
	if (sqlite3_open_v2(dbPath.c_str(),
			    &dbHandle,
			    SQLITE_OPEN_READWRITE | SQLITE_OPEN_NOMUTEX,
			    NULL) != SQLITE_OK)
	{
		const char* dbErrMsg = sqlite3_errmsg(dbHandle);
		const char* errMsg = "Failed to open the SQLite3 database";
	Logger::getLogger()->fatal("Error readings database %s", dbPath.c_str());

		Logger::getLogger()->error("%s '%s': %s",
					   dbErrMsg,
					   dbPath.c_str(),
					   dbErrMsg);
		connectErrorTime = time(0);

		raiseError("Connection", "%s '%s': '%s'",
			   dbErrMsg,
			   dbPath.c_str(),
			   dbErrMsg);

		sqlite3_close_v2(dbHandle);
		dbHandle = NULL;
	}
	else
	{
	Logger::getLogger()->warn("Opened readings database %s", dbPath.c_str());
		int rc;
		char *zErrMsg = NULL;

		rc = sqlite3_exec(dbHandle, "PRAGMA busy_timeout = 5000; PRAGMA cache_size = -4000; PRAGMA journal_mode = WAL; PRAGMA secure_delete = off; PRAGMA journal_size_limit = 4096000;", NULL, NULL, &zErrMsg);
		if (rc != SQLITE_OK)
		{
			const char* errMsg = "Failed to set 'PRAGMA busy_timeout = 5000; PRAGMA cache_size = -4000; PRAGMA journal_mode = WAL; PRAGMA secure_delete = off; PRAGMA journal_size_limit = 4096000;'";
			Logger::getLogger()->error("%s : error %s",
						   errMsg,
						   zErrMsg);
			connectErrorTime = time(0);

			sqlite3_free(zErrMsg);
	Logger::getLogger()->warn("PRAGMA failed  readings database %s", dbPath.c_str());
		}

#if 0
	Logger::getLogger()->warn("Attaching readings database %s", dbPath.c_str());
		/*
		 * Build the ATTACH DATABASE command in order to get
		 * 'fledge.' prefix in all SQL queries
		 */
		SQLBuffer attachDb;
		attachDb.append("ATTACH DATABASE '");
		attachDb.append(dbPath + "' AS readings;");

		const char *sqlStmt = attachDb.coalesce();
	Logger::getLogger()->warn("Rnning comamnd %s", sqlStmt);

		// Exec the statement
		rc = SQLexec(dbHandle,
			     sqlStmt,
			     NULL,
			     NULL,
			     &zErrMsg);

		// Check result
		if (rc != SQLITE_OK)
		{
			const char* errMsg = "Failed to attach 'fledge' database in";
			Logger::getLogger()->error("%s '%s': error %s",
						   errMsg,
						   sqlStmt,
						   zErrMsg);
			connectErrorTime = time(0);

			sqlite3_free(zErrMsg);
			sqlite3_close_v2(dbHandle);
		}
		else
		{
			Logger::getLogger()->warn("Connected to SQLite3 readings database: %s",
						  dbPath.c_str());
		}
		//Release sqlStmt buffer
		delete[] sqlStmt;
#else
			Logger::getLogger()->warn("Connected to SQLite3 readings database: %s",
						  dbPath.c_str());
#endif
	}
}


