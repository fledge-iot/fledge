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
#include <common.h>

/**
 * SQLite3 storage plugin for Fledge
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
	const char * createReadings = "CREATE TABLE fledge.readings (" \
					"id		INTEGER			PRIMARY KEY AUTOINCREMENT," \
					"asset_code	character varying(50)	NOT NULL," \
					"reading	JSON			NOT NULL DEFAULT '{}'," \
					"user_ts	DATETIME 		DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW' ))," \
					"ts		DATETIME 		DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW' ))" \
					");";

	const char * createReadingsFk = "CREATE INDEX fki_readings_fk1 ON readings (asset_code);";

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
				  "ATTACH DATABASE 'file::memory:?cache=shared' AS 'fledge'",
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

	sql.append("INSERT INTO fledge.readings ( user_ts, asset_code, reading ) VALUES ");

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
			sql.append("\',\'");

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
