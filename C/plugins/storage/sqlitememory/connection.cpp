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


	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx in memory appendReadings");
	Logger::getLogger()->setMinLevel("warning");

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
 * Fetch a block of readings from the reading table
 * It might not work with SQLite 3
 *
 * Fetch, used by the north side, returns timestamp in UTC.
 *
 * NOTE : it expects to handle a date having a fixed format
 * with milliseconds, microseconds and timezone expressed,
 * like for example :
 *
 *    2019-01-11 15:45:01.123456+01:00
 */
bool Connection::fetchReadings(unsigned long id,
							   unsigned int blksize,
							   std::string& resultSet)
{
	char sqlbuffer[512];
	char *zErrMsg = NULL;
	int rc;
	int retrieve;


	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx in memory fetchReadings");
	Logger::getLogger()->setMinLevel("warning");

	// SQL command to extract the data from the readings.readings
	const char *sql_cmd = R"(
	SELECT
		id,
		asset_code,
		reading,
		strftime('%%Y-%%m-%%d %%H:%%M:%%S', user_ts, 'utc')  ||
		substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
		strftime('%%Y-%%m-%%d %%H:%%M:%%f', ts, 'utc') AS ts
	FROM fledge.readings
	WHERE id >= %lu
	ORDER BY id ASC
	LIMIT %u;
	)";

	/*
	 * This query assumes datetime values are in 'localtime'
	 */
	snprintf(sqlbuffer,
			 sizeof(sqlbuffer),
			 sql_cmd,
			 id,
			 blksize);
	logSQL("ReadingsFetch", sqlbuffer);
	sqlite3_stmt *stmt;
	// Prepare the SQL statement and get the result set
	if (sqlite3_prepare_v2(dbHandle,
						   sqlbuffer,
						   -1,
						   &stmt,
						   NULL) != SQLITE_OK)
	{
		raiseError("retrieve", sqlite3_errmsg(dbHandle));

		// Failure
		return false;
	}
	else
	{
		// Call result set mapping
		rc = mapResultSet(stmt, resultSet);

		// Delete result set
		sqlite3_finalize(stmt);

		// Check result set errors
		if (rc != SQLITE_DONE)
		{
			raiseError("retrieve", sqlite3_errmsg(dbHandle));

			// Failure
			return false;
		}
		else
		{
			// Success
			return true;
		}
	}
}


/**
 * Check whether to compute timebucket query with min,max,avg for all datapoints
 *
 * @param    payload	JSON payload
 * @return		True if aggregation is 'all'
 */
bool aggregateAll(const Value& payload)
{
	if (payload.HasMember("aggregate") &&
		payload["aggregate"].IsObject())
	{
		const Value& agg = payload["aggregate"];
		if (agg.HasMember("operation") &&
			(strcmp(agg["operation"].GetString(), "all") == 0))
		{
			return true;
		}
	}
	return false;
}


/**
 * Perform a query against the readings table
 *
 * retrieveReadings, used by the API, returns timestamp in localtime.
 *
 */
// FIXME_I:
bool Connection::retrieveReadings(const string& condition, string& resultSet)
{
// Default template parameter uses UTF8 and MemoryPoolAllocator.
	Document	document;
	SQLBuffer	sql;
// Extra constraints to add to where clause
	SQLBuffer	jsonConstraints;
	bool		isAggregate = false;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx in memory retrieveReadings");
	Logger::getLogger()->setMinLevel("warning");


	try {
		if (dbHandle == NULL)
		{
			raiseError("retrieve", "No SQLite 3 db connection available");
			return false;
		}

		if (condition.empty())
		{
			const char *sql_cmd = R"(
					SELECT
						id,
						asset_code,
						reading,
						strftime(')" F_DATEH24_SEC R"(', user_ts, 'localtime')  ||
						substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
						strftime(')" F_DATEH24_MS R"(', ts, 'localtime') AS ts
					FROM fledge.readings)";

			sql.append(sql_cmd);
		}
		else
		{
			if (document.Parse(condition.c_str()).HasParseError())
			{
				raiseError("retrieve", "Failed to parse JSON payload");
				return false;
			}

			// timebucket aggregate all datapoints
			if (aggregateAll(document))
			{
				return aggregateQuery(document, resultSet);
			}

			if (document.HasMember("aggregate"))
			{
				isAggregate = true;
				sql.append("SELECT ");
				if (document.HasMember("modifier"))
				{
					sql.append(document["modifier"].GetString());
					sql.append(' ');
				}
				if (!jsonAggregates(document, document["aggregate"], sql, jsonConstraints, true))
				{
					return false;
				}
				sql.append(" FROM fledge.");
			}
			else if (document.HasMember("return"))
			{
				int col = 0;
				Value& columns = document["return"];
				if (! columns.IsArray())
				{
					raiseError("retrieve", "The property return must be an array");
					return false;
				}
				sql.append("SELECT ");
				if (document.HasMember("modifier"))
				{
					sql.append(document["modifier"].GetString());
					sql.append(' ');
				}
				for (Value::ConstValueIterator itr = columns.Begin(); itr != columns.End(); ++itr)
				{
					if (col)
						sql.append(", ");
					if (!itr->IsObject())	// Simple column name
					{
						if (strcmp(itr->GetString() ,"user_ts") == 0)
						{
							// Display without TZ expression and microseconds also
							sql.append(" strftime('" F_DATEH24_SEC "', user_ts, 'localtime') ");
							sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
							sql.append(" as  user_ts ");
						}
						else if (strcmp(itr->GetString() ,"ts") == 0)
						{
							// Display without TZ expression and microseconds also
							sql.append(" strftime('" F_DATEH24_MS "', ts, 'localtime') ");
							sql.append(" as ts ");
						}
						else
						{
							sql.append(itr->GetString());
						}
					}
					else
					{
						if (itr->HasMember("column"))
						{
							if (! (*itr)["column"].IsString())
							{
								raiseError("retrieve",
										   "column must be a string");
								return false;
							}
							if (itr->HasMember("format"))
							{
								if (! (*itr)["format"].IsString())
								{
									raiseError("retrieve",
											   "format must be a string");
									return false;
								}

								// SQLite 3 date format.
								string new_format;
								applyColumnDateFormatLocaltime((*itr)["format"].GetString(),
															   (*itr)["column"].GetString(),
															   new_format, true);
								// Add the formatted column or use it as is
								sql.append(new_format);
							}
							else if (itr->HasMember("timezone"))
							{
								if (! (*itr)["timezone"].IsString())
								{
									raiseError("retrieve",
											   "timezone must be a string");
									return false;
								}
								// SQLite3 doesnt support time zone formatting
								const char *tz = (*itr)["timezone"].GetString();

								if (strncasecmp(tz, "utc", 3) == 0)
								{
									if (strcmp((*itr)["column"].GetString() ,"user_ts") == 0)
									{
										// Extract milliseconds and microseconds for the user_ts fields

										sql.append("strftime('" F_DATEH24_SEC "', user_ts, 'utc') ");
										sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
										if (! itr->HasMember("alias"))
										{
											sql.append(" AS ");
											sql.append((*itr)["column"].GetString());
										}
									}
									else
									{
										sql.append("strftime('" F_DATEH24_MS "', ");
										sql.append((*itr)["column"].GetString());
										sql.append(", 'utc')");
										if (! itr->HasMember("alias"))
										{
											sql.append(" AS ");
											sql.append((*itr)["column"].GetString());
										}
									}
								}
								else if (strncasecmp(tz, "localtime", 9) == 0)
								{
									if (strcmp((*itr)["column"].GetString() ,"user_ts") == 0)
									{
										// Extract milliseconds and microseconds for the user_ts fields

										sql.append("strftime('" F_DATEH24_SEC "', user_ts, 'localtime') ");
										sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
										if (! itr->HasMember("alias"))
										{
											sql.append(" AS ");
											sql.append((*itr)["column"].GetString());
										}
									}
									else
									{
										sql.append("strftime('" F_DATEH24_MS "', ");
										sql.append((*itr)["column"].GetString());
										sql.append(", 'localtime')");
										if (! itr->HasMember("alias"))
										{
											sql.append(" AS ");
											sql.append((*itr)["column"].GetString());
										}
									}
								}
								else
								{
									raiseError("retrieve",
											   "SQLite3 plugin does not support timezones in queries");
									return false;
								}
							}
							else
							{

								if (strcmp((*itr)["column"].GetString() ,"user_ts") == 0)
								{
									// Extract milliseconds and microseconds for the user_ts fields

									sql.append("strftime('" F_DATEH24_SEC "', user_ts, 'localtime') ");
									sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
									if (! itr->HasMember("alias"))
									{
										sql.append(" AS ");
										sql.append((*itr)["column"].GetString());
									}
								}
								else
								{
									sql.append("strftime('" F_DATEH24_MS "', ");
									sql.append((*itr)["column"].GetString());
									sql.append(", 'localtime')");
									if (! itr->HasMember("alias"))
									{
										sql.append(" AS ");
										sql.append((*itr)["column"].GetString());
									}
								}
							}
							sql.append(' ');
						}
						else if (itr->HasMember("json"))
						{
							const Value& json = (*itr)["json"];
							if (! returnJson(json, sql, jsonConstraints))
								return false;
						}
						else
						{
							raiseError("retrieve",
									   "return object must have either a column or json property");
							return false;
						}

						if (itr->HasMember("alias"))
						{
							sql.append(" AS \"");
							sql.append((*itr)["alias"].GetString());
							sql.append('"');
						}
					}
					col++;
				}
				sql.append(" FROM fledge.");
			}
			else
			{
				sql.append("SELECT ");
				if (document.HasMember("modifier"))
				{
					sql.append(document["modifier"].GetString());
					sql.append(' ');
				}

				const char *sql_cmd = R"(
						id,
						asset_code,
						reading,
						strftime(')" F_DATEH24_SEC R"(', user_ts, 'localtime')  ||
						substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
						strftime(')" F_DATEH24_MS R"(', ts, 'localtime') AS ts
					FROM fledge.)";

				sql.append(sql_cmd);
			}
			sql.append("readings");
			if (document.HasMember("where"))
			{
				sql.append(" WHERE ");

				if (document.HasMember("where"))
				{
					if (!jsonWhereClause(document["where"], sql))
					{
						return false;
					}
				}
				else
				{
					raiseError("retrieve",
							   "JSON does not contain where clause");
					return false;
				}
				if (! jsonConstraints.isEmpty())
				{
					sql.append(" AND ");
					const char *jsonBuf =  jsonConstraints.coalesce();
					sql.append(jsonBuf);
					delete[] jsonBuf;
				}
			}
			else if (isAggregate)
			{
				/*
				 * Performance improvement: force sqlite to use an index
				 * if we are doing an aggregate and have no where clause.
				 */
				sql.append(" WHERE asset_code = asset_code");
			}
			if (!jsonModifiers(document, sql, true))
			{
				return false;
			}
		}
		sql.append(';');

		const char *query = sql.coalesce();
		char *zErrMsg = NULL;
		int rc;
		sqlite3_stmt *stmt;

		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		m_logSQL = true;
		logSQL("ReadingsRetrieve", query);
		Logger::getLogger()->setMinLevel("warning");


		// Prepare the SQL statement and get the result set
		rc = sqlite3_prepare_v2(dbHandle, query, -1, &stmt, NULL);

		// Release memory for 'query' var
		delete[] query;

		if (rc != SQLITE_OK)
		{
			raiseError("retrieve", sqlite3_errmsg(dbHandle));
			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("xxx Error 1");
			Logger::getLogger()->setMinLevel("warning");

			return false;
		}

		// Call result set mapping
		rc = mapResultSet(stmt, resultSet);

		// Delete result set
		sqlite3_finalize(stmt);

		// Check result set mapping errors
		if (rc != SQLITE_DONE)
		{
			raiseError("retrieve", sqlite3_errmsg(dbHandle));
			// Failure
			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("xxx Error 2");
			Logger::getLogger()->setMinLevel("warning");

			return false;
		}
		// Success
		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("xxx Ok");
		Logger::getLogger()->setMinLevel("warning");

		return true;
	} catch (exception e) {
		raiseError("retrieve", "Internal error: %s", e.what());
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
