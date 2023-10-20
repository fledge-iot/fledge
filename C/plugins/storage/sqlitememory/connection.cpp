/*
 * Fledge storage service.
 *
 * Copyright (c) 2019 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <connection.h>
#include <connection_manager.h>
#include <sqlite_common.h>
#include <utils.h>
#include <unistd.h>

/**
 * SQLite3 storage plugin for Fledge
 */

using namespace std;
using namespace rapidjson;

static time_t connectErrorTime = 0;

/**
 * Create a SQLite3 database connection
 */
Connection::Connection()
{
	if (getenv("FLEDGE_TRACE_SQL"))
	{
		m_logSQL = true;
	}
	else
	{
		m_logSQL = false;
	}

	/**
	 * Create IN MEMORY database for "readings" table: set empty file
	 */
	const char *dbHandleConn = "file:?cache=shared";

	// UTC time as default
	const char * createReadings = "CREATE TABLE " READINGS_DB_NAME_BASE " ." READINGS_TABLE_MEM " (" \
					"id		INTEGER			PRIMARY KEY AUTOINCREMENT," \
					"asset_code	character varying(50)	NOT NULL," \
					"reading	JSON			NOT NULL DEFAULT '{}'," \
					"user_ts	DATETIME 		DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW' ))," \
					"ts		DATETIME 		DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW' ))" \
					");";

	const char * createReadingsFk = "CREATE INDEX fki_" READINGS_TABLE_MEM "_fk1 ON " READINGS_TABLE_MEM " (asset_code);";
	const char * createReadingsIdx1 = "CREATE INDEX ix1_" READINGS_TABLE_MEM " ON " READINGS_TABLE_MEM " (asset_code, user_ts desc);";
	const char * createReadingsIdx2 = "CREATE INDEX ix2_" READINGS_TABLE_MEM " ON " READINGS_TABLE_MEM " (user_ts);";

	// Allow usage of URI for filename
        sqlite3_config(SQLITE_CONFIG_URI, 1);

	if (sqlite3_open(dbHandleConn, &dbHandle) != SQLITE_OK)
        {
		const char* dbErrMsg = sqlite3_errmsg(dbHandle);
		const char* errMsg = "Failed to open the IN_MEMORY SQLite3 database";

		Logger::getLogger()->error("%s '%s'",
					   dbErrMsg,
					   dbHandleConn);
		connectErrorTime = time(0);

		raiseError("InMemory Connection", "%s '%s'",
			   dbErrMsg,
			   dbHandleConn);

		sqlite3_close_v2(dbHandle);
	}
        else
	{
		Logger::getLogger()->info("Connected to IN_MEMORY SQLite3 database: %s",
					  dbHandleConn);

		int rc;
                // Exec the statements without getting error messages, for now

		// ATTACH 'fledge' as in memory shared DB
		rc = sqlite3_exec(dbHandle,
				  "ATTACH DATABASE 'file::memory:?cache=shared' AS '" READINGS_TABLE_MEM "'",
				  NULL,
				  NULL,
				  NULL);

		// CREATE TABLE readings
		rc = sqlite3_exec(dbHandle,
				  createReadings,
				  NULL,
				  NULL,
				  NULL);

                // FK
		rc = sqlite3_exec(dbHandle,
				  createReadingsFk,
				  NULL,
				  NULL,
				  NULL);

                // Idx1
		rc = sqlite3_exec(dbHandle,
				  createReadingsIdx1,
				  NULL,
				  NULL,
				  NULL);
                // Idx2
		rc = sqlite3_exec(dbHandle,
				  createReadingsIdx2,
				  NULL,
				  NULL,
				  NULL);
	}

}

/** 
 * Add a vacuum funtion, this is not needed for SQLite In Memory, but is here 
 * to satisfy the interface requirement.
 */
bool Connection::vacuum()
{
	return true;
}

/**
 * Load the in memory database from a file backup
 *
 * @param filename	The name of the file to restore from
 * @return bool		Success or failure of the backup
 */
bool Connection::loadDatabase(const string& filename)
{
int rc;
sqlite3 *file;
sqlite3_backup *backup;

	string pathname = getDataDir() + "/";
	pathname.append(filename);
	pathname.append(".db");
	if (access(pathname.c_str(), R_OK) != 0)
	{
		Logger::getLogger()->warn("Persisted database %s does not exist",
				pathname.c_str());
		return false;
	}
	if ((rc = sqlite3_open(pathname.c_str(), &file)) == SQLITE_OK)
	{
		if (backup = sqlite3_backup_init(dbHandle, READINGS_TABLE_MEM, file, "main"))
		{
			(void)sqlite3_backup_step(backup, -1);
			(void)sqlite3_backup_finish(backup);
			Logger::getLogger()->info("Reloaded persisted data to in-memory database");
		}
		rc = sqlite3_errcode(dbHandle);

		(void)sqlite3_close(file);
	}
	return rc == SQLITE_OK;
}

/**
 * Backup the in memory database to a file
 *
 * @param filename	The name of the file to backup to
 * @return bool		Success or failure of the backup
 */
bool Connection::saveDatabase(const string& filename)
{
int rc;
sqlite3 *file;
sqlite3_backup *backup;

	string pathname = getDataDir() + "/";
	pathname.append(filename);
	pathname.append(".db");
	unlink(pathname.c_str());
	if ((rc = sqlite3_open(pathname.c_str(), &file)) == SQLITE_OK)
	{
		if (backup = sqlite3_backup_init(file, "main", dbHandle, READINGS_TABLE_MEM))
		{
			rc = sqlite3_backup_step(backup, -1);
			(void)sqlite3_backup_finish(backup);
			Logger::getLogger()->info("Persisted data from in-memory database to %s", pathname.c_str());
		}
		rc = sqlite3_errcode(file);
		if (rc != SQLITE_OK)
		{
			Logger::getLogger()->warn("Persisting in-memory database failed: %s", sqlite3_errmsg(file));
		}

		(void)sqlite3_close(file);
	}
	else
	{
		Logger::getLogger()->warn("Failed to open database %s to persist in-memory data", pathname.c_str());
	}
	return rc == SQLITE_OK;
}
