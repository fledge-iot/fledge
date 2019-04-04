/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2019 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */
#include <connection.h>
#include <connection_manager.h>
#include <common.h>

/**
 * SQLite3 storage plugin for FogLAMP
 */

using namespace std;
using namespace rapidjson;


// Maximum no. of retries for a DB lock
#define RETRY_BACKOFF 100
#define MAX_RETRIES 10

static time_t connectErrorTime = 0;

/**
 * Create a SQLite3 database connection
 */
Connection::Connection()
{
	if (getenv("FOGLAMP_TRACE_SQL"))
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
	const char * createReadings = "CREATE TABLE foglamp.readings (" \
					"id		INTEGER			PRIMARY KEY AUTOINCREMENT," \
					"asset_code	character varying(50)	NOT NULL," \
					"read_key	uuid			UNIQUE," \
					"reading	JSON			NOT NULL DEFAULT '{}'," \
					"user_ts	DATETIME 		DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW' ))," \
					"ts		DATETIME 		DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW' ))" \
					");";

	const char * createReadingsFk = "CREATE INDEX fki_readings_fk1 ON readings (asset_code);";

	const char * createReadingsIdx = "CREATE INDEX readings_ix1 ON readings (read_key);";

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

		// ATTACH 'foglamp' as in memory shared DB
		rc = sqlite3_exec(dbHandle,
				  "ATTACH DATABASE 'file::memory:?cache=shared' AS 'foglamp'",
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

		// INDEX
		rc = sqlite3_exec(dbHandle,
				  createReadingsIdx,
				  NULL,
				  NULL,
				  NULL);
	}

}

/**
 * Append a set of readings to the readings table
 */
int Connection::appendReadings(const char *readings)
{
// Default template parameter uses UTF8 and MemoryPoolAllocator.
Document 	doc;
SQLBuffer	sql;
int		row = 0;
bool 		add_row = false;

	ParseResult ok = doc.Parse(readings);
	if (!ok)
	{
 		raiseError("appendReadings", GetParseError_En(doc.GetParseError()));
		return -1;
	}

	sql.append("INSERT INTO foglamp.readings ( user_ts, asset_code, read_key, reading ) VALUES ");

	if (!doc.HasMember("readings"))
	{
 		raiseError("appendReadings", "Payload is missing a readings array");
	        return -1;
	}
	Value &rdings = doc["readings"];
	if (!rdings.IsArray())
	{
		raiseError("appendReadings", "Payload is missing the readings array");
		return -1;
	}
	for (Value::ConstValueIterator itr = rdings.Begin(); itr != rdings.End(); ++itr)
	{
		if (!itr->IsObject())
		{
			raiseError("appendReadings",
				   "Each reading in the readings array must be an object");
			return -1;
		}

		add_row = true;

		// Handles - user_ts
		const char *str = (*itr)["user_ts"].GetString();
		if (strcmp(str, "now()") == 0)
		{
			if (row)
			{
				sql.append(", (");
			}
			else
			{
				sql.append('(');
			}

			sql.append(SQLITE3_NOW_READING);
		}
		else
		{
			char formatted_date[LEN_BUFFER_DATE] = {0};
			if (! formatDate(formatted_date, sizeof(formatted_date), str) )
			{
				raiseError("appendReadings", "Invalid date |%s|", str);
				add_row = false;
			}
			else
			{
				if (row)
				{
					sql.append(", (");
				}
				else
				{
					sql.append('(');
				}

				sql.append('\'');
				sql.append(formatted_date);
				sql.append('\'');
			}
		}

		if (add_row)
		{
			row++;

			// Handles - asset_code
			sql.append(",\'");
			sql.append((*itr)["asset_code"].GetString());

			// Handles - read_key
			// Python code is passing the string None when here is no read_key in the payload
			if (itr->HasMember("read_key") && strcmp((*itr)["read_key"].GetString(), "None") != 0)
			{
				sql.append("', \'");
				sql.append((*itr)["read_key"].GetString());
				sql.append("', \'");
			}
			else
			{
				// No "read_key" in this reading, insert NULL
				sql.append("', NULL, '");
			}

			// Handles - reading
			StringBuffer buffer;
			Writer<StringBuffer> writer(buffer);
			(*itr)["reading"].Accept(writer);
			sql.append(buffer.GetString());
			sql.append('\'');

			sql.append(')');
		}

	}
	sql.append(';');

	const char *query = sql.coalesce();
	logSQL("ReadingsAppend", query);
	char *zErrMsg = NULL;
	int rc;

	// Exec the INSERT statement: no callback, no result set
	rc = SQLexec(dbHandle,
		     query,
		     NULL,
		     NULL,
		     &zErrMsg);

	// Release memory for 'query' var
	delete[] query;

	// Check result code
	if (rc == SQLITE_OK)
	{
		// Success
		return sqlite3_changes(dbHandle);
	}
	else
	{
	 	raiseError("appendReadings", zErrMsg);
		sqlite3_free(zErrMsg);

		// Failure
		return -1;
	}
}

/**
 * Purge readings from the reading table
 */
unsigned int  Connection::purgeReadings(unsigned long age,
					unsigned int flags,
					unsigned long sent,
					std::string& result)
{
SQLBuffer sql;
long unsentPurged = 0;
long unsentRetained = 0;
long numReadings = 0;

	if (age == 0)
	{
		/*
		 * An age of 0 means remove the oldest hours data.
		 * So set age based on the data we have and continue.
		 */
		SQLBuffer oldest;
		oldest.append("SELECT (strftime('%s','now', 'localtime') - strftime('%s', MIN(user_ts)))/360 FROM foglamp.readings;");
		const char *query = oldest.coalesce();
		char *zErrMsg = NULL;
		int rc;
		int purge_readings = 0;

		// Exec query and get result in 'purge_readings' via 'selectCallback'
		rc = SQLexec(dbHandle,
			     query,
			     selectCallback,
			     &purge_readings,
			     &zErrMsg);
		// Release memory for 'query' var
		delete[] query;

		if (rc == SQLITE_OK)
		{
			age = purge_readings;
		}
		else
		{
 			raiseError("purge", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
	}
	if ((flags & 0x01) == 0)
	{
		// Get number of unsent rows we are about to remove
		SQLBuffer unsentBuffer;
		unsentBuffer.append("SELECT count(*) FROM foglamp.readings WHERE  user_ts < datetime('now', '-");
		unsentBuffer.append(age);
		unsentBuffer.append(" hours', 'localtime') AND id > ");
		unsentBuffer.append(sent);
		unsentBuffer.append(';');
		const char *query = unsentBuffer.coalesce();
		logSQL("ReadingsPurge", query);
		char *zErrMsg = NULL;
		int rc;
		int unsent = 0;

		// Exec query and get result in 'unsent' via 'countCallback'
		rc = SQLexec(dbHandle,
			     query,
			     countCallback,
			     &unsent,
			     &zErrMsg);

		// Release memory for 'query' var
		delete[] query;

		if (rc == SQLITE_OK)
		{
			unsentPurged = unsent;
		}
		else
		{
 			raiseError("retrieve", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
	}
	
	sql.append("DELETE FROM foglamp.readings WHERE user_ts < datetime('now', '-");
	sql.append(age);
	sql.append(" hours', 'localtime')");
	if ((flags & 0x01) == 0x01)	// Don't delete unsent rows
	{
		sql.append(" AND id < ");
		sql.append(sent);
	}
	sql.append(';');
	const char *query = sql.coalesce();
	logSQL("ReadingsPurge", query);
	char *zErrMsg = NULL;
	int rc;
	int rows_deleted;

	// Exec DELETE query: no callback, no resultset
	rc = SQLexec(dbHandle,
		     query,
		     NULL,
		     NULL,
		     &zErrMsg);

	// Release memory for 'query' var
	delete[] query;

	if (rc != SQLITE_OK)
	{
 		raiseError("retrieve", zErrMsg);
		sqlite3_free(zErrMsg);
		return 0;
	}

	// Get db changes
	unsigned int deletedRows = sqlite3_changes(dbHandle);

	SQLBuffer retainedBuffer;
	retainedBuffer.append("SELECT count(*) FROM foglamp.readings WHERE id > ");
	retainedBuffer.append(sent);
	retainedBuffer.append(';');
	const char *query_r = retainedBuffer.coalesce();
	logSQL("ReadingsPurge", query_r);
	int retained_unsent = 0;

	// Exec query and get result in 'retained_unsent' via 'countCallback'
	rc = SQLexec(dbHandle,
		     query_r,
		     countCallback,
		     &retained_unsent,
		     &zErrMsg);

	// Release memory for 'query_r' var
	delete[] query_r;

	if (rc == SQLITE_OK)
	{
		unsentRetained = retained_unsent;
	}
	else
	{
 		raiseError("retrieve", zErrMsg);
		sqlite3_free(zErrMsg);
	}

	int readings_num = 0;
	// Exec query and get result in 'readings_num' via 'countCallback'
	rc = SQLexec(dbHandle,
		    "SELECT count(*) FROM foglamp.readings",
		     countCallback,
		     &readings_num,
		     &zErrMsg);

	if (rc == SQLITE_OK)
	{
		numReadings = readings_num;
	}
	else
	{
 		raiseError("retrieve", zErrMsg);
		sqlite3_free(zErrMsg);
	}

	ostringstream convert;

	convert << "{ \"removed\" : " << deletedRows << ", ";
	convert << " \"unsentPurged\" : " << unsentPurged << ", ";
	convert << " \"unsentRetained\" : " << unsentRetained << ", ";
    	convert << " \"readings\" : " << numReadings << " }";

	result = convert.str();

	return deletedRows;
}

/**
 * SQLITE wrapper to rety statements when the database is locked
 *
 * @param	db	The open SQLite database
 * @param	sql	The SQL to execute
 * @param	callback	Callback function
 * @param	cbArg		Callback 1st argument
 * @param	errmsg		Locaiton to write error message
 */
int Connection::SQLexec(sqlite3 *db,
			const char *sql,
			int (*callback)(void*,int,char**,char**),
  			void *cbArg,
			char **errmsg)
{
int retries = 0, rc;

	do {
		rc = sqlite3_exec(db, sql, callback, cbArg, errmsg);
		retries++;
		if (rc == SQLITE_LOCKED || rc == SQLITE_BUSY)
		{
			usleep(retries * 1000);	// sleep retries milliseconds
		}
	} while (retries < MAX_RETRIES && (rc == SQLITE_LOCKED || rc == SQLITE_BUSY));

	if (rc == SQLITE_LOCKED)
	{
		Logger::getLogger()->error("Database still locked after maximum retries");
	}
	if (rc == SQLITE_BUSY)
	{
		Logger::getLogger()->error("Database still busy after maximum retries");
	}

	return rc;
}
