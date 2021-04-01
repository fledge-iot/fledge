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
#include <math.h>

/**
 * SQLite3 storage plugin for Fledge
 */

using namespace std;
using namespace rapidjson;


// Retry mechanism
#define PREP_CMD_MAX_RETRIES		20	    // Maximum no. of retries when a lock is encountered
#define PREP_CMD_RETRY_BASE 		5000    // Base time to wait for
#define PREP_CMD_RETRY_BACKOFF		5000 	// Variable time to wait for

#define MAX_RETRIES_SQLEXEC			80	// Maximum no. of retries when a lock is encountered

// 1 enable performance tracking
#define INSTRUMENT	0

static std::atomic<int> m_writeAccessOngoing(0);

static time_t connectErrorTime = 0;
static int purgeBlockSize = PURGE_DELETE_BLOCK_SIZE;

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
	const char * createReadings = "CREATE TABLE " READINGS_DB " ." READINGS_TABLE_MEM " (" \
					"id		INTEGER			PRIMARY KEY AUTOINCREMENT," \
					"asset_code	character varying(50)	NOT NULL," \
					"reading	JSON			NOT NULL DEFAULT '{}'," \
					"user_ts	DATETIME 		DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW' ))," \
					"ts		DATETIME 		DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW' ))" \
					");";

	const char * createReadingsFk = "CREATE INDEX fki_" READINGS_TABLE_MEM "_fk1 ON " READINGS_TABLE_MEM " (asset_code);";

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
						  "ATTACH DATABASE 'file::memory:?cache=shared' AS '" READINGS_DB "'",
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

	ostringstream threadId;
	threadId << std::this_thread::get_id();

	do {
		rc = sqlite3_exec(db, sql, callback, cbArg, errmsg);
		retries++;

		if (rc != SQLITE_OK)
		{
			this_thread::sleep_for(chrono::milliseconds(1000));

			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("%s - Retry :%d: :%X: :%X: :%s: :%s:", __FUNCTION__, retries, this->getDbHandle() ,this, threadId.str().c_str(), sql );
			Logger::getLogger()->setMinLevel("warning");

		}
	} while (retries < MAX_RETRIES_SQLEXEC && (rc != SQLITE_OK));

	if (retries >1) {
		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");

		Logger::getLogger()->debug("%s - Complete :%d: :%X: :%X: :%s: :%s:", __FUNCTION__, retries, this->getDbHandle() ,this, threadId.str().c_str(), sql );
		Logger::getLogger()->setMinLevel("warning");
	}

	if (rc == SQLITE_LOCKED)
	{
		Logger::getLogger()->error("Database still locked after maximum retries - %s retries :%d: :%X: :%X: :%s: :%s:", __FUNCTION__, retries, this->getDbHandle() ,this, threadId.str().c_str(), sql );
	}
	if (rc == SQLITE_BUSY)
	{
		Logger::getLogger()->error("Database still busy after maximum retries");
	}

	return rc;
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

	// SQL command to extract the data from the readings.readings
	const char *sql_cmd = R"(
	SELECT
		id,
		asset_code,
		reading,
		strftime('%%Y-%%m-%%d %%H:%%M:%%S', user_ts, 'utc')  ||
		substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
		strftime('%%Y-%%m-%%d %%H:%%M:%%f', ts, 'utc') AS ts
	FROM  )" READINGS_DB "." READINGS_TABLE_MEM R"(
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
 * Append a set of readings to the readings table
 */
int Connection::appendReadings(const char *readings)
{


// Default template parameter uses UTF8 and MemoryPoolAllocator.
	Document doc;
	int      row = 0;
	bool     add_row = false;

// Variables related to the SQLite insert using prepared command
	const char   *user_ts;
	const char   *asset_code;
	string        reading;
	sqlite3_stmt *stmt;
	int           sqlite3_resut;
	string        now;

// Retry mechanism
	int retries = 0;
	int sleep_time_ms = 0;

#if INSTRUMENT
	Logger::getLogger()->debug("appendReadings start thread :%s:", threadId.str().c_str());

	struct timeval	start, t1, t2, t3, t4, t5;
#endif

#if INSTRUMENT
	gettimeofday(&start, NULL);
#endif

	ParseResult ok = doc.Parse(readings);
	if (!ok)
	{
		raiseError("appendReadings", GetParseError_En(doc.GetParseError()));
		return -1;
	}

	if (!doc.HasMember("readings"))
	{
		raiseError("appendReadings", "Payload is missing a readings array");
		return -1;
	}
	Value &readingsValue = doc["readings"];
	if (!readingsValue.IsArray())
	{
		raiseError("appendReadings", "Payload is missing the readings array");
		return -1;
	}

	const char *sql_cmd="INSERT INTO  " READINGS_DB "." READINGS_TABLE_MEM " ( user_ts, asset_code, reading ) VALUES  (?,?,?)";

	sqlite3_prepare_v2(dbHandle, sql_cmd, strlen(sql_cmd), &stmt, NULL);
	{
		m_writeAccessOngoing.fetch_add(1);
		//unique_lock<mutex> lck(db_mutex);
		sqlite3_exec(dbHandle, "BEGIN TRANSACTION", NULL, NULL, NULL);

#if INSTRUMENT
		gettimeofday(&t1, NULL);
#endif

		for (Value::ConstValueIterator itr = readingsValue.Begin(); itr != readingsValue.End(); ++itr)
		{
			if (!itr->IsObject())
			{
				raiseError("appendReadings","Each reading in the readings array must be an object");
				sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION;", NULL, NULL, NULL);
				return -1;
			}

			add_row = true;

			// Handles - user_ts
			char formatted_date[LEN_BUFFER_DATE] = {0};
			user_ts = (*itr)["user_ts"].GetString();
			if (strcmp(user_ts, "now()") == 0)
			{
				getNow(now);
				user_ts = now.c_str();
			}
			else
			{
				if (! formatDate(formatted_date, sizeof(formatted_date), user_ts) )
				{
					raiseError("appendReadings", "Invalid date |%s|", user_ts);
					add_row = false;
				}
				else
				{
					user_ts = formatted_date;
				}
			}

			if (add_row)
			{
				// Handles - asset_code
				asset_code = (*itr)["asset_code"].GetString();

				// Handles - reading
				StringBuffer buffer;
				Writer<StringBuffer> writer(buffer);
				(*itr)["reading"].Accept(writer);
				reading = escape(buffer.GetString());

				if(stmt != NULL) {

					sqlite3_bind_text(stmt, 1, user_ts         ,-1, SQLITE_STATIC);
					sqlite3_bind_text(stmt, 2, asset_code      ,-1, SQLITE_STATIC);
					sqlite3_bind_text(stmt, 3, reading.c_str(), -1, SQLITE_STATIC);

					retries =0;
					sleep_time_ms = 0;

					// Retry mechanism in case SQLlite DB is locked
					do {
						// Insert the row using a lock to ensure one insert at time
						{

							sqlite3_resut = sqlite3_step(stmt);

						}
						if (sqlite3_resut == SQLITE_LOCKED  )
						{
							sleep_time_ms = PREP_CMD_RETRY_BASE + (random() %  PREP_CMD_RETRY_BACKOFF);
							retries++;

							Logger::getLogger()->info("SQLITE_LOCKED - record :%d: - retry number :%d: sleep time ms :%d:" ,row ,retries ,sleep_time_ms);

							std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
						}
						if (sqlite3_resut == SQLITE_BUSY)
						{
							ostringstream threadId;
							threadId << std::this_thread::get_id();

							sleep_time_ms = PREP_CMD_RETRY_BASE + (random() %  PREP_CMD_RETRY_BACKOFF);
							retries++;

							Logger::getLogger()->info("SQLITE_BUSY - thread :%s: - record :%d: - retry number :%d: sleep time ms :%d:", threadId.str().c_str() ,row, retries, sleep_time_ms);

							std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
						}
					} while (retries < PREP_CMD_MAX_RETRIES && (sqlite3_resut == SQLITE_LOCKED || sqlite3_resut == SQLITE_BUSY));

					if (sqlite3_resut == SQLITE_DONE)
					{
						row++;

						sqlite3_clear_bindings(stmt);
						sqlite3_reset(stmt);
					}
					else
					{
						raiseError("appendReadings","Inserting a row into SQLIte using a prepared command - asset_code :%s: error :%s: reading :%s: ",
								   asset_code,
								   sqlite3_errmsg(dbHandle),
								   reading.c_str());

						sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION", NULL, NULL, NULL);
						return -1;
					}
				}
			}
		}

		sqlite3_resut = sqlite3_exec(dbHandle, "END TRANSACTION", NULL, NULL, NULL);
		if (sqlite3_resut != SQLITE_OK)
		{
			raiseError("appendReadings", "Executing the commit of the transaction :%s:", sqlite3_errmsg(dbHandle));
			row = -1;
		}
		m_writeAccessOngoing.fetch_sub(1);
		//db_cv.notify_all();
	}

#if INSTRUMENT
	gettimeofday(&t2, NULL);
#endif

	if(stmt != NULL)
	{
		if (sqlite3_finalize(stmt) != SQLITE_OK)
		{
			raiseError("appendReadings","freeing SQLite in memory structure - error :%s:", sqlite3_errmsg(dbHandle));
		}
	}

#if INSTRUMENT
	gettimeofday(&t3, NULL);
#endif

#if INSTRUMENT
	struct timeval tm;
		double timeT1, timeT2, timeT3;

		timersub(&t1, &start, &tm);
		timeT1 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

		timersub(&t2, &t1, &tm);
		timeT2 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

		timersub(&t3, &t2, &tm);
		timeT3 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

		Logger::getLogger()->debug("appendReadings end   thread :%s: buffer :%10lu: count :%5d: JSON :%6.3f: inserts :%6.3f: finalize :%6.3f:",
								   threadId.str().c_str(),
								   strlen(readings),
								   row,
								   timeT1,
								   timeT2,
								   timeT3
		);

#endif

	return row;
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
bool Connection::retrieveReadings(const string& condition, string& resultSet)
{
// Default template parameter uses UTF8 and MemoryPoolAllocator.
	Document	document;
	SQLBuffer	sql;
// Extra constraints to add to where clause
	SQLBuffer	jsonConstraints;
	bool		isAggregate = false;

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
					FROM )" READINGS_DB "." READINGS_TABLE_MEM ")";

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
				sql.append(" FROM  " READINGS_DB ".");
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
				sql.append(" FROM  " READINGS_DB ".");
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
                    FROM  )" READINGS_DB R"(.)";

				sql.append(sql_cmd);
			}
			sql.append(READINGS_TABLE_MEM);
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

		logSQL("ReadingsRetrieve", query);

		// Prepare the SQL statement and get the result set
		rc = sqlite3_prepare_v2(dbHandle, query, -1, &stmt, NULL);

		// Release memory for 'query' var
		delete[] query;

		if (rc != SQLITE_OK)
		{
			raiseError("retrieve", sqlite3_errmsg(dbHandle));
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
			return false;
		}
		// Success
		return true;
	} catch (exception e) {
		raiseError("retrieve", "Internal error: %s", e.what());
		return false;
	}
}


/**
 * Process the aggregate options and return the columns to be selected
 */
bool Connection::jsonAggregates(const Value& payload,
								const Value& aggregates,
								SQLBuffer& sql,
								SQLBuffer& jsonConstraint,
								bool isTableReading)
{
	if (aggregates.IsObject())
	{
		if (! aggregates.HasMember("operation"))
		{
			raiseError("Select aggregation",
					   "Missing property \"operation\"");
			return false;
		}
		if ((! aggregates.HasMember("column")) && (! aggregates.HasMember("json")))
		{
			raiseError("Select aggregation",
					   "Missing property \"column\" or \"json\"");
			return false;
		}
		sql.append(aggregates["operation"].GetString());
		sql.append('(');
		if (aggregates.HasMember("column"))
		{
			string col = aggregates["column"].GetString();
			if (col.compare("*") == 0)	// Faster to count ROWID rather than *
			{
				sql.append("ROWID");
			}
			else
			{
				// an operation different from the 'count' is requested
				if (isTableReading && (col.compare("user_ts") == 0) )
				{
					sql.append("strftime('" F_DATEH24_SEC "', user_ts, 'localtime') ");
					sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
				}
				else
				{
					sql.append("\"");
					sql.append(col);
					sql.append("\"");
				}
			}
		}
		else if (aggregates.HasMember("json"))
		{
			const Value& json = aggregates["json"];
			if (! json.IsObject())
			{
				raiseError("Select aggregation",
						   "The json property must be an object");
				return false;
			}

			if (!json.HasMember("column"))
			{
				raiseError("retrieve",
						   "The json property is missing a column property");
				return false;
			}
			// Use json_extract(field, '$.key1.key2') AS value
			sql.append("json_extract(");
			sql.append(json["column"].GetString());
			sql.append(", '$.");

			if (!json.HasMember("properties"))
			{
				raiseError("retrieve",
						   "The json property is missing a properties property");
				return false;
			}
			const Value& jsonFields = json["properties"];

			if (jsonFields.IsArray())
			{
				if (! jsonConstraint.isEmpty())
				{
					jsonConstraint.append(" AND ");
				}
				// JSON1 SQLite3 extension 'json_type' object check:
				// json_type(field, '$.key1.key2') IS NOT NULL
				// Build the Json keys NULL check
				jsonConstraint.append("json_type(");
				jsonConstraint.append(json["column"].GetString());
				jsonConstraint.append(", '$.");

				int field = 0;
				string prev;
				for (Value::ConstValueIterator itr = jsonFields.Begin(); itr != jsonFields.End(); ++itr)
				{
					if (field)
					{
						sql.append(".");
					}
					if (prev.length() > 0)
					{
						// Append Json field for NULL check
						jsonConstraint.append(prev);
						jsonConstraint.append(".");
					}
					prev = itr->GetString();
					field++;
					// Append Json field for query
					sql.append(itr->GetString());
				}
				// Add last Json key
				jsonConstraint.append(prev);

				// Add condition for all json keys not null
				jsonConstraint.append("') IS NOT NULL");
			}
			else
			{
				// Append Json field for query
				sql.append(jsonFields.GetString());

				if (! jsonConstraint.isEmpty())
				{
					jsonConstraint.append(" AND ");
				}
				// JSON1 SQLite3 extension 'json_type' object check:
				// json_type(field, '$.key1.key2') IS NOT NULL
				// Build the Json key NULL check
				jsonConstraint.append("json_type(");
				jsonConstraint.append(json["column"].GetString());
				jsonConstraint.append(", '$.");
				jsonConstraint.append(jsonFields.GetString());

				// Add condition for json key not null
				jsonConstraint.append("') IS NOT NULL");
			}
			sql.append("')");
		}
		sql.append(") AS \"");
		if (aggregates.HasMember("alias"))
		{
			sql.append(aggregates["alias"].GetString());
		}
		else
		{
			sql.append(aggregates["operation"].GetString());
			sql.append('_');
			sql.append(aggregates["column"].GetString());
		}
		sql.append("\"");
	}
	else if (aggregates.IsArray())
	{
		int index = 0;
		for (Value::ConstValueIterator itr = aggregates.Begin(); itr != aggregates.End(); ++itr)
		{
			if (!itr->IsObject())
			{
				raiseError("select aggregation",
						   "Each element in the aggregate array must be an object");
				return false;
			}
			if ((! itr->HasMember("column")) && (! itr->HasMember("json")))
			{
				raiseError("Select aggregation", "Missing property \"column\"");
				return false;
			}
			if (! itr->HasMember("operation"))
			{
				raiseError("Select aggregation", "Missing property \"operation\"");
				return false;
			}
			if (index)
				sql.append(", ");
			index++;
			sql.append((*itr)["operation"].GetString());
			sql.append('(');
			if (itr->HasMember("column"))
			{
				string column_name= (*itr)["column"].GetString();
				if (isTableReading && (column_name.compare("user_ts") == 0) )
				{
					sql.append("strftime('" F_DATEH24_SEC "', user_ts, 'localtime') ");
					sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
				}
				else
				{
					sql.append("\"");
					sql.append(column_name);
					sql.append("\"");
				}

			}
			else if (itr->HasMember("json"))
			{
				const Value& json = (*itr)["json"];
				if (! json.IsObject())
				{
					raiseError("Select aggregation", "The json property must be an object");
					return false;
				}
				if (!json.HasMember("column"))
				{
					raiseError("retrieve", "The json property is missing a column property");
					return false;
				}
				if (!json.HasMember("properties"))
				{
					raiseError("retrieve", "The json property is missing a properties property");
					return false;
				}
				const Value& jsonFields = json["properties"];
				if (! jsonConstraint.isEmpty())
				{
					jsonConstraint.append(" AND ");
				}
				// Use json_extract(field, '$.key1.key2') AS value
				sql.append("json_extract(");
				sql.append(json["column"].GetString());
				sql.append(", '$.");

				// JSON1 SQLite3 extension 'json_type' object check:
				// json_type(field, '$.key1.key2') IS NOT NULL
				// Build the Json keys NULL check
				jsonConstraint.append("json_type(");
				jsonConstraint.append(json["column"].GetString());
				jsonConstraint.append(", '$.");

				if (jsonFields.IsArray())
				{
					string prev;
					for (Value::ConstValueIterator itr = jsonFields.Begin(); itr != jsonFields.End(); ++itr)
					{
						if (prev.length() > 0)
						{
							jsonConstraint.append(prev);
							jsonConstraint.append('.');
							sql.append('.');
						}
						// Append Json field for query
						sql.append(itr->GetString());
						prev = itr->GetString();
					}
					// Add last Json key
					jsonConstraint.append(prev);

					// Add condition for json key not null
					jsonConstraint.append("') IS NOT NULL");
				}
				else
				{
					// Append Json field for query
					sql.append(jsonFields.GetString());

					// JSON1 SQLite3 extension 'json_type' object check:
					// json_type(field, '$.key1.key2') IS NOT NULL
					// Build the Json key NULL check
					jsonConstraint.append(jsonFields.GetString());

					// Add condition for json key not null
					jsonConstraint.append("') IS NOT NULL");
				}
				sql.append("')");
			}
			sql.append(") AS \"");
			if (itr->HasMember("alias"))
			{
				sql.append((*itr)["alias"].GetString());
			}
			else
			{
				sql.append((*itr)["operation"].GetString());
				sql.append('_');
				sql.append((*itr)["column"].GetString());
			}
			sql.append("\"");
		}
	}
	if (payload.HasMember("group"))
	{
		sql.append(", ");
		if (payload["group"].IsObject())
		{
			const Value& grp = payload["group"];

			if (grp.HasMember("format"))
			{
				// SQLite 3 date format.
				string new_format;
				if (isTableReading)
				{
					applyColumnDateFormatLocaltime(grp["format"].GetString(),
												   grp["column"].GetString(),
												   new_format);
				}
				else
				{
					applyColumnDateFormat(grp["format"].GetString(),
										  grp["column"].GetString(),
										  new_format);
				}
				// Add the formatted column or use it as is
				sql.append(new_format);
			}
			else
			{
				sql.append(grp["column"].GetString());
			}

			if (grp.HasMember("alias"))
			{
				sql.append(" AS \"");
				sql.append(grp["alias"].GetString());
				sql.append("\"");
			}
			else
			{
				sql.append(" AS \"");
				sql.append(grp["column"].GetString());
				sql.append("\"");
			}
		}
		else
		{
			sql.append(payload["group"].GetString());
		}
	}
	if (payload.HasMember("timebucket"))
	{
		const Value& tb = payload["timebucket"];
		if (! tb.IsObject())
		{
			raiseError("Select data",
					   "The \"timebucket\" property must be an object");
			return false;
		}
		if (! tb.HasMember("timestamp"))
		{
			raiseError("Select data",
					   "The \"timebucket\" object must have a timestamp property");
			return false;
		}

		if (tb.HasMember("format"))
		{
			// SQLite 3 date format is limited.
			string new_format;
			if (applyDateFormat(tb["format"].GetString(),
								new_format))
			{
				sql.append(", ");
				// Add the formatted column
				sql.append(new_format);

				if (tb.HasMember("size"))
				{
					// Use Unix epoch, without microseconds
					sql.append(tb["size"].GetString());
					sql.append(" * round(");
					sql.append("strftime('%s', ");
					sql.append(tb["timestamp"].GetString());
					sql.append(") / ");
					sql.append(tb["size"].GetString());
					sql.append(", 6)");
				}
				else
				{
					sql.append(tb["timestamp"].GetString());
				}
				sql.append(", 'unixepoch')");
			}
			else
			{
				/**
				 * No date format found: we should return an error.
				 * Note: currently if input Json payload has no 'result' member
				 * raiseError() results in no data being sent to the client
				 * We use Unix epoch without microseconds
				 */
				sql.append(", datetime(");
				if (tb.HasMember("size"))
				{
					sql.append(tb["size"].GetString());
					sql.append(" * round(");
				}
				// Use Unix epoch, without microseconds
				sql.append("strftime('%s', ");
				sql.append(tb["timestamp"].GetString());
				if (tb.HasMember("size"))
				{
					sql.append(") / ");
					sql.append(tb["size"].GetString());
					sql.append(", 6)");
				}
				else
				{
					sql.append(")");
				}
				sql.append(", 'unixepoch')");
			}
		}
		else
		{
			sql.append(", datetime(");
			if (tb.HasMember("size"))
			{
				sql.append(tb["size"].GetString());
				sql.append(" * round(");
			}

			/*
			 * Default format when no format is specified:
			 * - we use Unix time without milliseconds.
			 */
			sql.append("strftime('%s', ");
			sql.append(tb["timestamp"].GetString());
			if (tb.HasMember("size"))
			{
				sql.append(") / ");
				sql.append(tb["size"].GetString());
				sql.append(", 6)");
			}
			else
			{
				sql.append(")");
			}
			sql.append(", 'unixepoch')");
		}

		sql.append(" AS \"");
		if (tb.HasMember("alias"))
		{
			sql.append(tb["alias"].GetString());
		}
		else
		{
			sql.append("timestamp");
		}
		sql.append('"');
	}
	return true;
}

/**
 * Convert a JSON where clause into a SQLite3 where clause
 *
 */
bool Connection::jsonWhereClause(const Value& whereClause,
								 SQLBuffer& sql, bool convertLocaltime)
{
	if (!whereClause.IsObject())
	{
		raiseError("where clause", "The \"where\" property must be a JSON object");
		return false;
	}
	if (!whereClause.HasMember("column"))
	{
		raiseError("where clause", "The \"where\" object is missing a \"column\" property");
		return false;
	}
	if (!whereClause.HasMember("condition"))
	{
		raiseError("where clause", "The \"where\" object is missing a \"condition\" property");
		return false;
	}
	if (!whereClause.HasMember("value"))
	{
		raiseError("where clause",
				   "The \"where\" object is missing a \"value\" property");
		return false;
	}

	sql.append(whereClause["column"].GetString());
	sql.append(' ');
	string cond = whereClause["condition"].GetString();
	if (!cond.compare("older"))
	{
		if (!whereClause["value"].IsInt())
		{
			raiseError("where clause",
					   "The \"value\" of an \"older\" condition must be an integer");
			return false;
		}
		sql.append("< datetime('now', '-");
		sql.append(whereClause["value"].GetInt());
		if (convertLocaltime)
			sql.append(" seconds', 'localtime')"); // Get value in localtime
		else
			sql.append(" seconds')"); // Get value in UTC by asking for no timezone
	}
	else if (!cond.compare("newer"))
	{
		if (!whereClause["value"].IsInt())
		{
			raiseError("where clause",
					   "The \"value\" of an \"newer\" condition must be an integer");
			return false;
		}
		sql.append("> datetime('now', '-");
		sql.append(whereClause["value"].GetInt());
		if (convertLocaltime)
			sql.append(" seconds', 'localtime')"); // Get value in localtime
		else
			sql.append(" seconds')"); // Get value in UTC by asking for no timezone
	}
	else if (!cond.compare("in") || !cond.compare("not in"))
	{
		// Check we have a non empty array
		if (whereClause["value"].IsArray() &&
			whereClause["value"].Size())
		{
			sql.append(cond);
			sql.append(" ( ");
			int field = 0;
			for (Value::ConstValueIterator itr = whereClause["value"].Begin();
				 itr != whereClause["value"].End();
				 ++itr)
			{
				if (field)
				{
					sql.append(", ");
				}
				field++;
				if (itr->IsNumber())
				{
					if (itr->IsInt())
					{
						sql.append(itr->GetInt());
					}
					else if (itr->IsInt64())
					{
						sql.append((long)itr->GetInt64());
					}
					else
					{
						sql.append(itr->GetDouble());
					}
				}
				else if (itr->IsString())
				{
					sql.append('\'');
					sql.append(escape(itr->GetString()));
					sql.append('\'');
				}
				else
				{
					string message("The \"value\" of a \"" + \
							cond + \
							"\" condition array element must be " \
							"a string, integer or double.");
					raiseError("where clause", message.c_str());
					return false;
				}
			}
			sql.append(" )");
		}
		else
		{
			string message("The \"value\" of a \"" + \
					cond + "\" condition must be an array " \
					"and must not be empty.");
			raiseError("where clause", message.c_str());
			return false;
		}
	}
	else
	{
		sql.append(cond);
		sql.append(' ');
		if (whereClause["value"].IsInt())
		{
			sql.append(whereClause["value"].GetInt());
		} else if (whereClause["value"].IsString())
		{
			sql.append('\'');
			sql.append(escape(whereClause["value"].GetString()));
			sql.append('\'');
		}
	}

	if (whereClause.HasMember("and"))
	{
		sql.append(" AND ");
		if (!jsonWhereClause(whereClause["and"], sql, convertLocaltime))
		{
			return false;
		}
	}
	if (whereClause.HasMember("or"))
	{
		sql.append(" OR ");
		if (!jsonWhereClause(whereClause["or"], sql, convertLocaltime))
		{
			return false;
		}
	}

	return true;
}


/**
 * Build, exucute and return data of a timebucket query with min,max,avg for all datapoints
 *
 * @param    payload	JSON object for timebucket query
 * @param    resultSet	JSON Output buffer
 * @return		True of success, false on any error
 */
bool Connection::aggregateQuery(const Value& payload, string& resultSet)
{
	if (!payload.HasMember("where") ||
		!payload.HasMember("timebucket"))
	{
		raiseError("retrieve", "aggregateQuery is missing "
							   "'where' and/or 'timebucket' properties");
		return false;
	}

	SQLBuffer sql;

	sql.append("SELECT asset_code, ");

	double size = 1;
	string timeColumn;

	// Check timebucket object
	if (payload.HasMember("timebucket"))
	{
		const Value& bucket = payload["timebucket"];
		if (!bucket.HasMember("timestamp"))
		{
			raiseError("retrieve", "aggregateQuery is missing "
								   "'timestamp' property for 'timebucket'");
			return false;
		}

		// Time column
		timeColumn = bucket["timestamp"].GetString();

		// Bucket size
		if (bucket.HasMember("size"))
		{
			size = atof(bucket["size"].GetString());
			if (!size)
			{
				size = 1;
			}
		}

		// Time format for output
		string newFormat;
		if (bucket.HasMember("format") && size >= 1)
		{
			applyColumnDateFormatLocaltime(bucket["format"].GetString(),
										   "timestamp",
										   newFormat,
										   true);
			sql.append(newFormat);
		}
		else
		{
			if (size < 1)
			{
				// sub-second granularity to time bucket size:
				// force output formatting with microseconds
				newFormat = "strftime('%Y-%m-%d %H:%M:%S', " + timeColumn +
							", 'localtime') || substr(" + timeColumn	  +
							", instr(" + timeColumn + ", '.'), 7)";
				sql.append(newFormat);
			}
			else
			{
				sql.append("timestamp");
			}
		}

		// Time output alias
		if (bucket.HasMember("alias"))
		{
			sql.append(" AS ");
			sql.append(bucket["alias"].GetString());
		}
	}

	// JSON format aggregated data
	sql.append(", '{' || group_concat('\"' || x || '\" : ' || resd, ', ') || '}' AS reading ");

	// subquery
	sql.append("FROM ( SELECT  x, asset_code, max(timestamp) AS timestamp, ");
	// Add min
	sql.append("'{\"min\" : ' || min(theval) || ', ");
	// Add max
	sql.append("\"max\" : ' || max(theval) || ', ");
	// Add avg
	sql.append("\"average\" : ' || avg(theval) || ', ");
	// Add count
	sql.append("\"count\" : ' || count(theval) || ', ");
	// Add sum
	sql.append("\"sum\" : ' || sum(theval) || '}' AS resd ");

	if (size < 1)
	{
		// Add max(user_ts)
		sql.append(", max(" + timeColumn + ") AS " + timeColumn + " ");
	}

	// subquery
	sql.append("FROM ( SELECT asset_code, ");
	sql.append(timeColumn);

	if (size >= 1)
	{
		sql.append(", datetime(");
	}
	else
	{
		sql.append(", (");
	}

	// Size formatted string
	string size_format;
	if (fmod(size, 1.0) == 0.0)
	{
		size_format = to_string(int(size));
	}
	else
	{
		size_format = to_string(size);
	}

	// Add timebucket size
	// Unix Time is (Julian Day - JulianDay(1/1/1970 0:00 UTC) * Seconds_per_day
	if (size != 1)
	{
		sql.append(size_format);
		sql.append(" * round((julianday(");
		sql.append(timeColumn);
		sql.append(") - " + string(JULIAN_DAY_START_UNIXTIME) + ") * " + string(SECONDS_PER_DAY) + " / ");
		sql.append(size_format);
		sql.append(")");
	}
	else
	{
		sql.append("round((julianday(");
		sql.append(timeColumn);
		sql.append(") - " + string(JULIAN_DAY_START_UNIXTIME) + ") * " + string(SECONDS_PER_DAY) + " / 1)");
	}
	if (size >= 1)
	{
		sql.append(", 'unixepoch') AS \"timestamp\", reading, ");
	}
	else
	{
		sql.append(") AS \"timestamp\", reading, ");
	}

	// Get all datapoints in 'reading' field
	sql.append("json_each.key AS x, json_each.value AS theval FROM " READINGS_DB "." READINGS_TABLE_MEM ", json_each(" READINGS_TABLE_MEM ".reading) ");

	// Add where condition
	sql.append("WHERE ");
	if (!jsonWhereClause(payload["where"], sql))
	{
		raiseError("retrieve", "aggregateQuery: failure while building WHERE clause");
		return false;
	}

	// close subquery
	sql.append(") tmp ");

	// Add group by
	// Unix Time is (Julian Day - JulianDay(1/1/1970 0:00 UTC) * Seconds_per_day
	sql.append(" GROUP BY x, asset_code, ");
	sql.append("round((julianday(");
	sql.append(timeColumn);
	sql.append(") - " + string(JULIAN_DAY_START_UNIXTIME) + ") * " + string(SECONDS_PER_DAY) + " / ");

	if (size != 1)
	{
		sql.append(size_format);
	}
	else
	{
		sql.append('1');
	}
	sql.append(") ");

	// close subquery
	sql.append(") tbl ");

	// Add final group and sort
	sql.append("GROUP BY timestamp, asset_code ORDER BY timestamp DESC");

	// Add limit
	if (payload.HasMember("limit"))
	{
		if (!payload["limit"].IsInt())
		{
			raiseError("retrieve", "aggregateQuery: limit must be specfied as an integer");
			return false;
		}
		sql.append(" LIMIT ");
		try {
			sql.append(payload["limit"].GetInt());
		} catch (exception e) {
			raiseError("retrieve", "aggregateQuery: bad value for limit parameter: %s", e.what());
			return false;
		}
	}
	sql.append(';');

	// Execute query
	const char *query = sql.coalesce();
	int rc;
	sqlite3_stmt *stmt;

	logSQL("CommonRetrieve", query);

	// Prepare the SQL statement and get the result set
	rc = sqlite3_prepare_v2(dbHandle, query, -1, &stmt, NULL);

	// Release memory for 'query' var
	delete[] query;

	if (rc != SQLITE_OK)
	{
		raiseError("retrieve", sqlite3_errmsg(dbHandle));
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
		return false;
	}

	return true;
}


/**
 * Purge readings from the reading table
 */
unsigned int  Connection::purgeReadings(unsigned long age,
										unsigned int flags,
										unsigned long sent,
										std::string& result)
{
	long unsentPurged = 0;
	long unsentRetained = 0;
	long numReadings = 0;
	unsigned long rowidLimit = 0, minrowidLimit = 0, maxrowidLimit = 0, rowidMin;
	struct timeval startTv, endTv;
	int blocks = 0;

	Logger *logger = Logger::getLogger();

	result = "{ \"removed\" : 0, ";
	result += " \"unsentPurged\" : 0, ";
	result += " \"unsentRetained\" : 0, ";
	result += " \"readings\" : 0 }";

	logger->info("Purge starting...");
	gettimeofday(&startTv, NULL);
	/*
	 * We fetch the current rowid and limit the purge process to work on just
	 * those rows present in the database when the purge process started.
	 * This provents us looping in the purge process if new readings become
	 * eligible for purging at a rate that is faster than we can purge them.
	 */
	{
		char *zErrMsg = NULL;
		int rc;
		rc = SQLexec(dbHandle,
					 "select max(rowid) from " READINGS_DB "."  READINGS_TABLE_MEM ";",
			rowidCallback,
			&rowidLimit,
			&zErrMsg);

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phase 0, fetching rowid limit ", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
		maxrowidLimit = rowidLimit;
	}

	{
		char *zErrMsg = NULL;
		int rc;
		rc = SQLexec(dbHandle,
					 "select min(rowid) from " READINGS_DB "." READINGS_TABLE_MEM ";",
			rowidCallback,
			&minrowidLimit,
			&zErrMsg);

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phaase 0, fetching minrowid limit ", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
	}

	if (age == 0)
	{
		/*
		 * An age of 0 means remove the oldest hours data.
		 * So set age based on the data we have and continue.
		 */
		SQLBuffer oldest;
		oldest.append("SELECT (strftime('%s','now', 'utc') - strftime('%s', MIN(user_ts)))/360 FROM " READINGS_DB "." READINGS_TABLE_MEM " where rowid <= ");
		oldest.append(rowidLimit);
		oldest.append(';');
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
			raiseError("purge - phase 1", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
	}

	{
		/*
		 * Refine rowid limit to just those rows older than age hours.
		 */
		char *zErrMsg = NULL;
		int rc;
		unsigned long l = minrowidLimit;
		unsigned long r;
		if (flags & 0x01) {

			r = min(sent, rowidLimit);
		} else {
			r = rowidLimit;
		}

		r = max(r, l);
		//logger->info("%s:%d: l=%u, r=%u, sent=%u, rowidLimit=%u, minrowidLimit=%u, flags=%u", __FUNCTION__, __LINE__, l, r, sent, rowidLimit, minrowidLimit, flags);
		if (l == r)
		{
			logger->info("No data to purge: min_id == max_id == %u", minrowidLimit);
			return 0;
		}

		unsigned long m=l;

		while (l <= r)
		{
			unsigned long midRowId = 0;
			unsigned long prev_m = m;
			m = l + (r - l) / 2;
			if (prev_m == m) break;

			// e.g. select id from readings where rowid = 219867307 AND user_ts < datetime('now' , '-24 hours', 'utc');
			SQLBuffer sqlBuffer;
			sqlBuffer.append("select id from " READINGS_DB "." READINGS_TABLE_MEM " where rowid = ");
			sqlBuffer.append(m);
			sqlBuffer.append(" AND user_ts < datetime('now' , '-");
			sqlBuffer.append(age);
			sqlBuffer.append(" hours');");
			const char *query = sqlBuffer.coalesce();


			rc = SQLexec(dbHandle,
						 query,
						 rowidCallback,
						 &midRowId,
						 &zErrMsg);

			if (rc != SQLITE_OK)
			{
				raiseError("purge - phase 1, fetching midRowId ", zErrMsg);
				sqlite3_free(zErrMsg);
				return 0;
			}

			if (midRowId == 0) // mid row doesn't satisfy given condition for user_ts, so discard right/later half and look in left/earlier half
			{
				// search in earlier/left half
				r = m - 1;

				// The m position should be skipped as midRowId is 0
				m = r;
			}
			else //if (l != m)
			{
				// search in later/right half
				l = m + 1;
			}
		}

		rowidLimit = m;

		if (minrowidLimit == rowidLimit)
		{
			logger->info("No data to purge");
			return 0;
		}

		rowidMin = minrowidLimit;
	}
	//logger->info("Purge collecting unsent row count");
	if ((flags & 0x01) == 0)
	{
		char *zErrMsg = NULL;
		int rc;
		int lastPurgedId;
		SQLBuffer idBuffer;
		idBuffer.append("select id from " READINGS_DB "." READINGS_TABLE_MEM " where rowid = ");
		idBuffer.append(rowidLimit);
		idBuffer.append(';');
		const char *idQuery = idBuffer.coalesce();
		rc = SQLexec(dbHandle,
					 idQuery,
					 rowidCallback,
					 &lastPurgedId,
					 &zErrMsg);

		// Release memory for 'idQuery' var
		delete[] idQuery;

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phase 0, fetching rowid limit ", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}

		if (sent != 0 && lastPurgedId > sent)	// Unsent readings will be purged
		{
			// Get number of unsent rows we are about to remove
			int unsent = rowidLimit - sent;
			unsentPurged = unsent;
		}
	}
	if (m_writeAccessOngoing)
	{
		while (m_writeAccessOngoing)
		{
			std::this_thread::sleep_for(std::chrono::milliseconds(100));
		}
	}

	unsigned int deletedRows = 0;
	char *zErrMsg = NULL;
	unsigned int rowsAffected, totTime=0, prevBlocks=0, prevTotTime=0;
	logger->info("Purge about to delete readings # %ld to %ld", rowidMin, rowidLimit);
	while (rowidMin < rowidLimit)
	{
		blocks++;
		rowidMin += purgeBlockSize;
		if (rowidMin > rowidLimit)
		{
			rowidMin = rowidLimit;
		}
		SQLBuffer sql;
		sql.append("DELETE FROM " READINGS_DB "." READINGS_TABLE_MEM " WHERE rowid <= ");
		sql.append(rowidMin);
		sql.append(';');
		const char *query = sql.coalesce();
		logSQL("ReadingsPurge", query);

		int rc;
		{
			//unique_lock<mutex> lck(db_mutex);
//		if (m_writeAccessOngoing) db_cv.wait(lck);

			START_TIME;
			// Exec DELETE query: no callback, no resultset
			rc = SQLexec(dbHandle,
						 query,
						 NULL,
						 NULL,
						 &zErrMsg);
			END_TIME;

			// Release memory for 'query' var
			delete[] query;

			totTime += usecs;

			if(usecs>150000)
			{
				std::this_thread::sleep_for(std::chrono::milliseconds(100+usecs/10000));
			}
		}

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phase 3", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}

		// Get db changes
		rowsAffected = sqlite3_changes(dbHandle);
		deletedRows += rowsAffected;
		logger->debug("Purge delete block #%d with %d readings", blocks, rowsAffected);

		if(blocks % RECALC_PURGE_BLOCK_SIZE_NUM_BLOCKS == 0)
		{
			int prevAvg = prevTotTime/(prevBlocks?prevBlocks:1);
			int currAvg = (totTime-prevTotTime)/(blocks-prevBlocks);
			int avg = ((prevAvg?prevAvg:currAvg)*5 + currAvg*5) / 10; // 50% weightage for long term avg and 50% weightage for current avg
			prevBlocks = blocks;
			prevTotTime = totTime;
			int deviation = abs(avg - TARGET_PURGE_BLOCK_DEL_TIME);
			logger->debug("blocks=%d, totTime=%d usecs, prevAvg=%d usecs, currAvg=%d usecs, avg=%d usecs, TARGET_PURGE_BLOCK_DEL_TIME=%d usecs, deviation=%d usecs",
						  blocks, totTime, prevAvg, currAvg, avg, TARGET_PURGE_BLOCK_DEL_TIME, deviation);
			if (deviation > TARGET_PURGE_BLOCK_DEL_TIME/10)
			{
				float ratio = (float)TARGET_PURGE_BLOCK_DEL_TIME / (float)avg;
				if (ratio > 2.0) ratio = 2.0;
				if (ratio < 0.5) ratio = 0.5;
				purgeBlockSize = (float)purgeBlockSize * ratio;
				purgeBlockSize = purgeBlockSize / PURGE_BLOCK_SZ_GRANULARITY * PURGE_BLOCK_SZ_GRANULARITY;
				if (purgeBlockSize < MIN_PURGE_DELETE_BLOCK_SIZE)
					purgeBlockSize = MIN_PURGE_DELETE_BLOCK_SIZE;
				if (purgeBlockSize > MAX_PURGE_DELETE_BLOCK_SIZE)
					purgeBlockSize = MAX_PURGE_DELETE_BLOCK_SIZE;
				logger->debug("Changed purgeBlockSize to %d", purgeBlockSize);
			}
			std::this_thread::sleep_for(std::chrono::milliseconds(100));
		}
		//Logger::getLogger()->debug("Purge delete block #%d with %d readings", blocks, rowsAffected);
	} while (rowidMin  < rowidLimit);

	unsentRetained = maxrowidLimit - rowidLimit;

	numReadings = maxrowidLimit +1 - minrowidLimit - deletedRows;

	if (sent == 0)	// Special case when not north process is used
	{
		unsentPurged = deletedRows;
	}

	ostringstream convert;

	convert << "{ \"removed\" : " << deletedRows << ", ";
	convert << " \"unsentPurged\" : " << unsentPurged << ", ";
	convert << " \"unsentRetained\" : " << unsentRetained << ", ";
	convert << " \"readings\" : " << numReadings << " }";

	result = convert.str();

	//logger->debug("Purge result=%s", result.c_str());

	gettimeofday(&endTv, NULL);
	unsigned long duration = (1000000 * (endTv.tv_sec - startTv.tv_sec)) + endTv.tv_usec - startTv.tv_usec;
	logger->info("Purge process complete in %d blocks in %lduS", blocks, duration);

	return deletedRows;
}


/**
 * Purge readings from the reading table
 */
unsigned int  Connection::purgeReadingsByRows(unsigned long rows,
											  unsigned int flags,
											  unsigned long sent,
											  std::string& result)
{
	unsigned long deletedRows = 0, unsentPurged = 0, unsentRetained = 0, numReadings = 0;
	unsigned long limit = 0;

	unsigned long rowcount, minId, maxId;
	unsigned long rowsAffected;
	unsigned long deletePoint;

	Logger *logger = Logger::getLogger();

	logger->info("Purge by Rows called");
	if ((flags & 0x01) == 0x01)
	{
		limit = sent;
		logger->info("Sent is %lu", sent);
	}
	logger->info("Purge by Rows called with flags %x, rows %lu, limit %lu", flags, rows, limit);
	// Don't save unsent rows

	char *zErrMsg = NULL;
	int rc;
	rc = SQLexec(dbHandle,
				 "select count(rowid) from " READINGS_DB "." READINGS_TABLE_MEM ";",
				 rowidCallback,
				 &rowcount,
				 &zErrMsg);

	if (rc != SQLITE_OK)
	{
		raiseError("purge - phaase 0, fetching row count", zErrMsg);
		sqlite3_free(zErrMsg);
		return 0;
	}

	rc = SQLexec(dbHandle,
				 "select max(id) from " READINGS_DB "." READINGS_TABLE_MEM ";",
				 rowidCallback,
				 &maxId,
				 &zErrMsg);

	if (rc != SQLITE_OK)
	{
		raiseError("purge - phaase 0, fetching maximum id", zErrMsg);
		sqlite3_free(zErrMsg);
		return 0;
	}

	numReadings = rowcount;
	rowsAffected = 0;
	deletedRows = 0;

	do
	{
		if (rowcount <= rows)
		{
			logger->info("Row count %d is less than required rows %d", rowcount, rows);
			break;
		}

		rc = SQLexec(dbHandle,
					 "select min(id) from " READINGS_DB "." READINGS_TABLE_MEM ";",
					 rowidCallback,
					 &minId,
					 &zErrMsg);

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phaase 0, fetching minimum id", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}

		deletePoint = minId + 10000;
		if (maxId - deletePoint < rows || deletePoint > maxId)
			deletePoint = maxId - rows;

		// Do not delete
		if ((flags & 0x01) == 0x01) {

			if (limit < deletePoint)
			{
				deletePoint = limit;
			}
		}
		SQLBuffer sql;

		logger->info("RowCount %lu, Max Id %lu, min Id %lu, delete point %lu", rowcount, maxId, minId, deletePoint);

		sql.append("delete from " READINGS_DB "." READINGS_TABLE_MEM "  where id <= ");
		sql.append(deletePoint);
		const char *query = sql.coalesce();
		{
			//unique_lock<mutex> lck(db_mutex);
//			if (m_writeAccessOngoing) db_cv.wait(lck);

			// Exec DELETE query: no callback, no resultset
			rc = SQLexec(dbHandle, query, NULL, NULL, &zErrMsg);
			rowsAffected = sqlite3_changes(dbHandle);

			deletedRows += rowsAffected;
			numReadings -= rowsAffected;
			rowcount    -= rowsAffected;

			// Release memory for 'query' var
			delete[] query;
			logger->debug("Deleted %lu rows", rowsAffected);
			if (rowsAffected == 0)
			{
				break;
			}
			if (limit != 0 && sent != 0)
			{
				unsentPurged = deletePoint - sent;
			}
			else if (!limit)
			{
				unsentPurged += rowsAffected;
			}
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(1));
	} while (rowcount > rows);



	if (limit)
	{
		unsentRetained = numReadings - rows;
	}

	ostringstream convert;

	convert << "{ \"removed\" : " << deletedRows << ", ";
	convert << " \"unsentPurged\" : " << unsentPurged << ", ";
	convert << " \"unsentRetained\" : " << unsentRetained << ", ";
	convert << " \"readings\" : " << numReadings << " }";

	result = convert.str();

	Logger::getLogger()->debug("%s - rows :%lu: flag :%x: sent :%lu: numReadings :%lu:  rowsAffected :%u:  result :%s:", __FUNCTION__, rows, flags, sent, numReadings, rowsAffected, result.c_str() );

	logger->info("Purge by Rows complete: %s", result.c_str());
	return deletedRows;
}
