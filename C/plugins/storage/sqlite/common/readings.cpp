/*
 * Fledge storage service.
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <math.h>
#include <connection.h>
#include <connection_manager.h>
#include <common.h>
#include <reading_stream.h>
#include <random>
#include <utils.h>

#include <sys/stat.h>
#include <libgen.h>

#include <string_utils.h>
#include <algorithm>
#include <vector>

// 1 enable performance tracking
#define INSTRUMENT	0

#if INSTRUMENT
#include <sys/time.h>
#endif

// Decode stream data
#define	RDS_USER_TIMESTAMP(stream, x) 	stream[x]->userTs
#define	RDS_ASSET_CODE(stream, x)		stream[x]->assetCode
#define	RDS_PAYLOAD(stream, x)			&(stream[x]->assetCode[0]) + stream[x]->assetCodeLength

// Retry mechanism
#define PREP_CMD_MAX_RETRIES		20	    // Maximum no. of retries when a lock is encountered
#define PREP_CMD_RETRY_BASE 		5000    // Base time to wait for
#define PREP_CMD_RETRY_BACKOFF		5000 	// Variable time to wait for

//#ifndef PLUGIN_LOG_NAME
//#define PLUGIN_LOG_NAME "SQLite 3"
//#endif

/**
 * SQLite3 storage plugin for Fledge
 */

using namespace std;
using namespace rapidjson;

#define CONNECT_ERROR_THRESHOLD		5*60	// 5 minutes

#define MAX_RETRIES			40	// Maximum no. of retries when a lock is encountered
#define RETRY_BACKOFF			100	// Multipler to backoff DB retry on lock

/*
 * The following allows for conditional inclusion of code that tracks the top queries
 * run by the storage plugin and the number of times a particular statement has to
 * be retried because of the database being busy./
 */
#define DO_PROFILE		0
#define DO_PROFILE_RETRIES	0
#if DO_PROFILE
#include <profile.h>

#define	TOP_N_STATEMENTS		10	// Number of statements to report in top n
#define RETRY_REPORT_THRESHOLD		1000	// Report retry statistics every X calls

QueryProfile profiler(TOP_N_STATEMENTS);
unsigned long retryStats[MAX_RETRIES] = { 0,0,0,0,0,0,0,0,0,0 };
unsigned long numStatements = 0;
int	      maxQueue = 0;
#endif

static std::atomic<int> m_waiting(0);
static std::atomic<int> m_writeAccessOngoing(0);
static std::mutex	db_mutex;
static std::condition_variable	db_cv;
static int purgeBlockSize = PURGE_DELETE_BLOCK_SIZE;

static time_t connectErrorTime = 0;



#ifndef SQLITE_SPLIT_READINGS
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
#endif

#ifndef SQLITE_SPLIT_READINGS
/**
 * Build, exucute and return data of a timebucket query with min,max,avg for all datapoints
 *
 * @param    payload	JSON object for timebucket query
 * @param    resultSet	JSON Output buffer
 * @return		True of success, false on any error
 */
bool Connection::aggregateQuery(const Value& payload, string& resultSet)
{
	vector<string>  asset_codes;


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
	sql.append("json_each.key AS x, json_each.value AS theval FROM ");

	{
		string sql_cmd;
		ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();

		// SQL - start
		sql_cmd = R"(
			(
			)";

		// SQL - union of all the readings tables
		string sql_cmd_base;
		string sql_cmd_tmp;
		sql_cmd_base = " SELECT  ROWID, id, \"_assetcode_\" asset_code, reading, user_ts, ts  FROM _dbname_._tablename_ ";
		sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, asset_codes);
		sql_cmd += sql_cmd_tmp;

		// SQL - end
		sql_cmd += R"(
				) as reading_table
			)";
		sql.append(sql_cmd.c_str());

		sql.append(", json_each(reading_table.reading) ");

	}


	// Add where condition
	sql.append("WHERE ");
	if (!jsonWhereClause(payload["where"], sql, asset_codes))
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
#endif

/**
 * Append a stream of readings to SQLite db
 *
 * @param readings  readings to store into the SQLite db
 * @param commit    if true a database commit is executed and a new transaction will be opened at the next execution
 *
 * TODO: the current code should be adapted to use the multi databases/tables implementation
 *
 */
int Connection::readingStream(ReadingStream **readings, bool commit)
{
	// Row defintion related
	int i;
	bool add_row = false;
	const char *user_ts;
	string now;
	char ts[60], micro_s[10];
	char formatted_date[LEN_BUFFER_DATE] = {0};
	struct tm timeinfo;
	const char *asset_code;
	const char *payload;
	string reading;

	// Retry mechanism
	int retries = 0;
	int sleep_time_ms = 0;

	// SQLite related
	sqlite3_stmt *stmt;
	int sqlite3_resut;
	int rowNumber = -1;


	//# FIXME_I
	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			// FIXME_I:
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("readingStream - attach new DB thread :%s: dbHandle :%X:", threadId.str().c_str(), this->getDbHandle());

			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}

#if INSTRUMENT
	struct timeval start, t1, t2, t3, t4, t5;
#endif

	// * TODO: the current code should be adapted to use the multi databases/tables implementation
	const char *sql_cmd = "INSERT INTO  " READINGS_DB ".readings_1 ( asset_code, reading, user_ts ) VALUES  (?,?,?)";

	if (sqlite3_prepare_v2(dbHandle, sql_cmd, strlen(sql_cmd), &stmt, NULL) != SQLITE_OK)
	{
		raiseError("readingStream", sqlite3_errmsg(dbHandle));
		return -1;
	}

	// The handling of the commit parameter is overridden as using a pool of connections every execution receives
	// a differen one, so a commit at every run is executed.
	m_streamOpenTransaction = true;
	commit = true;

	if (m_streamOpenTransaction)
	{
		if (sqlite3_exec(dbHandle, "BEGIN TRANSACTION", NULL, NULL, NULL) != SQLITE_OK)
		{
			raiseError("readingStream", sqlite3_errmsg(dbHandle));
			return -1;
		}
		m_streamOpenTransaction = false;
	}

#if INSTRUMENT
	gettimeofday(&start, NULL);
#endif

	try
	{
		for (i = 0; readings[i]; i++)
		{
			add_row = true;

			// Handles - asset_code
			asset_code = RDS_ASSET_CODE(readings, i);

			// Handles - reading
			payload = RDS_PAYLOAD(readings, i);
			reading = escape(payload);

			// Handles - user_ts
			memset(&timeinfo, 0, sizeof(struct tm));
			gmtime_r(&RDS_USER_TIMESTAMP(readings, i).tv_sec, &timeinfo);
			std::strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", &timeinfo);
			snprintf(micro_s, sizeof(micro_s), ".%06lu", RDS_USER_TIMESTAMP(readings, i).tv_usec);

			formatted_date[0] = {0};
			strncat(ts, micro_s, 10);
			user_ts = ts;
			if (strcmp(user_ts, "now()") == 0)
			{
				getNow(now);
				user_ts = now.c_str();
			}
			else
			{
				if (!formatDate(formatted_date, sizeof(formatted_date), user_ts))
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
				if (stmt != NULL)
				{
					sqlite3_bind_text(stmt, 1, asset_code,      -1, SQLITE_STATIC);
					sqlite3_bind_text(stmt, 2, reading.c_str(), -1, SQLITE_STATIC);
					sqlite3_bind_text(stmt, 3, user_ts,         -1, SQLITE_STATIC);

					retries =0;
					sleep_time_ms = 0;

					// Retry mechanism in case SQLlite DB is locked
					do {
						// Insert the row using a lock to ensure one insert at time
						{
							m_writeAccessOngoing.fetch_add(1);
							//unique_lock<mutex> lck(db_mutex);

							sqlite3_resut = sqlite3_step(stmt);

							m_writeAccessOngoing.fetch_sub(1);
							//db_cv.notify_all();
						}

						if (sqlite3_resut == SQLITE_LOCKED  )
						{
							sleep_time_ms = PREP_CMD_RETRY_BASE + (random() %  PREP_CMD_RETRY_BACKOFF);
							retries++;

							Logger::getLogger()->info("SQLITE_LOCKED - record :%d: - retry number :%d: sleep time ms :%d:",i, retries, sleep_time_ms);

							std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
						}
						if (sqlite3_resut == SQLITE_BUSY)
						{
							ostringstream threadId;
							threadId << std::this_thread::get_id();

							sleep_time_ms = PREP_CMD_RETRY_BASE + (random() %  PREP_CMD_RETRY_BACKOFF);
							retries++;

							Logger::getLogger()->info("SQLITE_BUSY - thread :%s: - record :%d: - retry number :%d: sleep time ms :%d:", threadId.str().c_str() ,i , retries, sleep_time_ms);

							std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
						}
					} while (retries < PREP_CMD_MAX_RETRIES && (sqlite3_resut == SQLITE_LOCKED || sqlite3_resut == SQLITE_BUSY));

					if (sqlite3_resut == SQLITE_DONE)
					{
						rowNumber++;

						sqlite3_clear_bindings(stmt);
						sqlite3_reset(stmt);
					}
					else
					{
						raiseError("appendReadings",
								   "Inserting a row into SQLIte using a prepared command - asset_code :%s: error :%s: reading :%s: ",
								   asset_code,
								   sqlite3_errmsg(dbHandle),
								   reading.c_str());

						sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION", NULL, NULL, NULL);
						m_streamOpenTransaction = true;
						return -1;
					}
				}
			}
		}
		rowNumber = i;

	} catch (exception e) {

		raiseError("appendReadings", "Inserting a row into SQLIte using a prepared command - error :%s:", e.what());

		sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION", NULL, NULL, NULL);
		m_streamOpenTransaction = true;
		return -1;
	}

#if INSTRUMENT
	gettimeofday(&t1, NULL);
#endif

	if (commit)
	{
		sqlite3_resut = sqlite3_exec(dbHandle, "END TRANSACTION", NULL, NULL, NULL);
		if (sqlite3_resut != SQLITE_OK)
		{
			raiseError("appendReadings", "Executing the commit of the transaction - error :%s:", sqlite3_errmsg(dbHandle));
			rowNumber = -1;
		}
		m_streamOpenTransaction = true;
	}

	if(stmt != NULL)
	{
		if (sqlite3_finalize(stmt) != SQLITE_OK)
		{
			raiseError("appendReadings","freeing SQLite in memory structure - error :%s:", sqlite3_errmsg(dbHandle));
		}
	}

#if INSTRUMENT
	gettimeofday(&t2, NULL);
#endif

#if INSTRUMENT
	struct timeval tm;
	double timeT1, timeT2, timeT3;

	timersub(&t1, &start, &tm);
	timeT1 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

	timersub(&t2, &t1, &tm);
	timeT2 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

	Logger::getLogger()->debug("readingStream row count :%d:", rowNumber);

	Logger::getLogger()->debug("readingStream Timing - stream handling %.3f seconds - commit/finalize %.3f seconds",
							   timeT1,
							   timeT2
	);
#endif

	return rowNumber;
}




// FIXME_I:
void Connection::setUsedDbId(int dbId) {

	m_NewDbIdList.push_back(dbId);
}


#ifndef SQLITE_SPLIT_READINGS
/**
 * Append a set of readings to the readings table
 */
int Connection::appendReadings(const char *readings)
{
// Default template parameter uses UTF8 and MemoryPoolAllocator.
Document doc;
int      row = 0, readingId;
bool     add_row = false;

int lastReadingsId;

// Variables related to the SQLite insert using prepared command
const char   *user_ts;
const char   *asset_code;
string        reading,
              msg;
sqlite3_stmt *stmt;
int rc;
int           sqlite3_resut;
int           readingsId;
string        now;

std::pair<int, sqlite3_stmt *> pairValue;
string lastAsset;

// Retry mechanism
int retries = 0;
int sleep_time_ms = 0;

int localNReadingsTotal;

	//# FIXME_I
	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	// FIXME_I:
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("appendReadings thread start :%s: conn :%X: dbHandle :%X:", threadId.str().c_str(), this, this->getDbHandle());

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			// FIXME_I:
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("XXX appendReadings - attach new DB thread :%s: dbHandle :%X:", threadId.str().c_str(), this->getDbHandle());

			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}

	localNReadingsTotal = readCatalogue->getMaxReadingsId();
	vector<sqlite3_stmt *> readingsStmt(localNReadingsTotal +1, nullptr);

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

	int tableIdx;
	string sql_cmd;

	{
	m_writeAccessOngoing.fetch_add(1);
	//unique_lock<mutex> lck(db_mutex);
	sqlite3_exec(dbHandle, "BEGIN TRANSACTION", NULL, NULL, NULL);

#if INSTRUMENT
		gettimeofday(&t1, NULL);
#endif

	lastAsset = "";
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

			//# A different asset is managed respect the previous one
			if (lastAsset.compare(asset_code)!= 0)
			{
				readingsId = readCatalogue->getReadingReference(this, asset_code);

				// FIXME_I:
				Logger::getLogger()->setMinLevel("debug");
				Logger::getLogger()->debug("getReadingReference after :%X: threadId :%s:", dbHandle, threadId.str().c_str() );
				Logger::getLogger()->setMinLevel("debug");

				if (readingsId == -1)
				{
					Logger::getLogger()->warn("appendReadings - It was not possible to insert the row for the asset_code :%s: into the readings, row ignored.", asset_code);
					stmt = NULL;
				}
				else
				{
					if (readingsId >= localNReadingsTotal)
					{
						localNReadingsTotal = readingsId + 1;
						readingsStmt.resize(localNReadingsTotal, nullptr);

						Logger::getLogger()->debug("appendReadings: thread :%s: resize size :%d: idx :%d: ", threadId.str().c_str(), localNReadingsTotal, readingsId);
					}

					if (readingsStmt[readingsId] == nullptr)
					{
						string dbName = readCatalogue->generateDbNameFromTableId(readingsId);
						string dbReadingsName = readCatalogue->generateReadingsName(readingsId);

						sql_cmd = "INSERT INTO  " + dbName + "." + dbReadingsName + " ( id, user_ts, reading ) VALUES  (?,?,?)";
						rc = SQLPrepare(dbHandle, sql_cmd.c_str(), &readingsStmt[readingsId]);

						if (rc != SQLITE_OK)
						{
							raiseError("appendReadings", sqlite3_errmsg(dbHandle));
						}

					}
					stmt = readingsStmt[readingsId];

					lastAsset = asset_code;
				}
			}

			// Handles - reading
			StringBuffer buffer;
			Writer<StringBuffer> writer(buffer);
			(*itr)["reading"].Accept(writer);
			reading = escape(buffer.GetString());

			if(stmt != NULL) {

				sqlite3_bind_int (stmt, 1, readCatalogue->getGlobalId());
				sqlite3_bind_text(stmt, 2, user_ts         ,-1, SQLITE_STATIC);
				sqlite3_bind_text(stmt, 3, reading.c_str(), -1, SQLITE_STATIC);

				retries =0;
				sleep_time_ms = 0;

				string msgError;

				// Retry mechanism in case SQLlite DB is locked
				do {
					// Insert the row using a lock to ensure one insert at time
					{
						sqlite3_resut = sqlite3_step(stmt);
					}

					msgError = "";

					if (sqlite3_resut == SQLITE_LOCKED  )
					{
						msgError = "SQLITE_LOCKED";

					} else if (sqlite3_resut == SQLITE_BUSY)
					{
						msgError = "SQLITE_BUSY";

					} else if (sqlite3_resut  != SQLITE_DONE)
					{
						msgError = "SQLITE_ERROR";
					}


					if(sqlite3_resut != SQLITE_DONE)
					{
						ostringstream threadId;
						threadId << std::this_thread::get_id();

						sleep_time_ms = PREP_CMD_RETRY_BASE + (random() %  PREP_CMD_RETRY_BACKOFF);
						retries++;

						// FIXME_I:
						//Logger::getLogger()->info("appendReadings - %s - thread :%s: - con :%X: - dbHandle :%X: - record :%d: - retry number :%d: sleep time ms :%d:error :%s:",
						Logger::getLogger()->warn("appendReadings - %s - thread :%s: - con :%X: - dbHandle :%X: - record :%d: - retry number :%d: sleep time ms :%d:error :%s:",
								msgError.c_str(),
								threadId.str().c_str() ,
								this,
								dbHandle,
								row,
								retries,
								sleep_time_ms,
								sqlite3_errmsg(dbHandle));

						// FIXME_I:
						Logger::getLogger()->warn("appendReadings - asset_code :%s: readingsId :%d:",
												  asset_code,
												  readingsId);

						std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
					}
				// FIXME_I:
				} while (retries < PREP_CMD_MAX_RETRIES && (sqlite3_resut != SQLITE_DONE));

				if (sqlite3_resut == SQLITE_DONE)
				{
					row++;

					sqlite3_clear_bindings(stmt);
					sqlite3_reset(stmt);
				}
				else
				{
					raiseError("appendReadings","Inserting a row into SQLIte using a prepared command - asset_code :%s: error :%s: reading :%s: dbHandle :%X:",
						asset_code,
						sqlite3_errmsg(dbHandle),
						reading.c_str(),
						dbHandle);

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

	// Finalize sqlite structures
	for (auto &item : readingsStmt)
	{
		if(item != nullptr)
		{

			if (sqlite3_finalize(item) != SQLITE_OK)
			{
				raiseError("appendReadings","freeing SQLite in memory structure - error :%s:", sqlite3_errmsg(dbHandle));
			}
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
#endif

#ifndef SQLITE_SPLIT_READINGS
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
char sqlbuffer[5120];
char *zErrMsg = NULL;
int rc;
int retrieve;
vector<string>  asset_codes;
string sql_cmd;

	//# FIXME_I
	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			// FIXME_I:
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("fetchReadings - attach new DB thread :%s: dbHandle :%X:", threadId.str().c_str(), this->getDbHandle());

			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}

	// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
	{
		// SQL - start
		sql_cmd = R"(
			SELECT
				id,
				asset_code,
				reading,
				strftime('%Y-%m-%d %H:%M:%S', user_ts, 'utc')  ||
				substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
				strftime('%Y-%m-%d %H:%M:%f', ts, 'utc') AS ts
			FROM
			(
		)";

		// SQL - union of all the readings tables
		string sql_cmd_base;
		string sql_cmd_tmp;
		sql_cmd_base = " SELECT  id, \"_assetcode_\" asset_code, reading, user_ts, ts  FROM _dbname_._tablename_ WHERE id >= " + to_string(id) + " and id <=  " + to_string(id) + " + " + to_string(blksize) + " ";
		ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
		sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, asset_codes);
		sql_cmd += sql_cmd_tmp;

		// SQL - end
		sql_cmd += R"(
			) as tb
			ORDER BY id ASC
			LIMIT
		)" + to_string(blksize);

	}

	logSQL("ReadingsFetch", sql_cmd.c_str());
	sqlite3_stmt *stmt;
	// Prepare the SQL statement and get the result set
	if (sqlite3_prepare_v2(dbHandle,
						   sql_cmd.c_str(),
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
#endif

#ifndef SQLITE_SPLIT_READINGS
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

SQLBuffer	sqlExtDummy;
SQLBuffer	sqlExt;
SQLBuffer	jsonConstraintsExt;
// Extra constraints to add to where clause
SQLBuffer	jsonConstraints;
bool		isAggregate = false;
bool		isOptAggregate = false;

string modifierExt;
string modifierInt;

vector<string>  asset_codes;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("retrieveReadings");
	Logger::getLogger()->setMinLevel("warning");


	//# FIXME_I
	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			// FIXME_I:
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("XX1 retrieveReadings - attach new DB thread :%s: dbHandle :%X:", threadId.str().c_str(), this->getDbHandle());

			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}

	try {
		if (dbHandle == NULL)
		{
			raiseError("retrieve", "No SQLite 3 db connection available");
			return false;
		}

		if (condition.empty())
		{
			string sql_cmd;
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();

			// SQL - start
			sql_cmd = R"(
				SELECT
					id,
					asset_code,
					reading,
					strftime(')" F_DATEH24_SEC R"(', user_ts, 'localtime')  ||
					substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
					strftime(')" F_DATEH24_MS R"(', ts, 'localtime') AS ts
				FROM (
			)";

			// SQL - union of all the readings tables
			string sql_cmd_base;
			string sql_cmd_tmp;
			sql_cmd_base = " SELECT  id, \"_assetcode_\" asset_code, reading, user_ts, ts  FROM _dbname_._tablename_ ";
			sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, asset_codes);
			sql_cmd += sql_cmd_tmp;

			// SQL - end
			sql_cmd += R"(
				) as tb;
			)";
			sql.append(sql_cmd.c_str());
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
				// Generates the SQL for the external query
				if (!jsonAggregates(document, document["aggregate"], sql, jsonConstraints, isOptAggregate, true, true))
				{
					return false;
				}
				// Generates the SQL for the internal query
				if (isOptAggregate)
				{
					if (!jsonAggregates(document, document["aggregate"], sqlExt, jsonConstraintsExt, isOptAggregate, true, false))
					{
						return false;
					}
				}

				sql.append(" FROM  ");
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
				sql.append(" FROM ");
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
                    FROM  )";

				sql.append(sql_cmd);
			}
			{

				// Identifies the asset_codes used in the query
				if (document.HasMember("where"))
				{
					jsonWhereClause(document["where"], sqlExtDummy, asset_codes);
				}

				string sql_cmd;
				ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();

				// SQL - start
				sql_cmd = R"(
					(
				)";

				// SQL - union of all the readings tables
				string sql_cmd_base;
				string sql_cmd_tmp;

				// Specific optimization for the count operation
				if (isOptAggregate)
				{
					const char *queryTmp = sqlExt.coalesce();

					sql_cmd_base = " SELECT ";
					sql_cmd_base += queryTmp;

					if (! strstr(queryTmp, "ROWID"))
						sql_cmd_base += ",  ROWID";

					if (! strstr(queryTmp, "asset_code"))
						sql_cmd_base += ",  asset_code";

					sql_cmd_base += ", id, reading, user_ts, ts ";
					StringReplaceAll (sql_cmd_base, "asset_code", " \"_assetcode_\" .assetcode. ");
					sql_cmd_base += " FROM _dbname_._tablename_ ";

					delete[] queryTmp;
				}
				else
				{
					sql_cmd_base = " SELECT ROWID, id, \"_assetcode_\" asset_code, reading, user_ts, ts  FROM _dbname_._tablename_ ";
				}
				sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, asset_codes);
				sql_cmd += sql_cmd_tmp;

				// SQL - end
				sql_cmd += R"(
					) as readings_1
				)";
				sql.append(sql_cmd.c_str());

			}



			if (document.HasMember("where"))
			{
				sql.append(" WHERE ");
			 
				if (document.HasMember("where"))
				{
					if (!jsonWhereClause(document["where"], sql, asset_codes))
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
				sql.append(" WHERE id = id");
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

			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("retrieve error :%s: ", sqlite3_errmsg(dbHandle));
			Logger::getLogger()->setMinLevel("warning");


			raiseError("retrieve", sqlite3_errmsg(dbHandle));

			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("retrieve error :%s: ", sqlite3_errmsg(dbHandle));
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
			return false;
		}
		// Success
		return true;
	} catch (exception e) {
		raiseError("retrieve", "Internal error: %s", e.what());
	}

}
#endif

#ifndef SQLITE_SPLIT_READINGS
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

vector<string>  assetCodes;

	Logger *logger = Logger::getLogger();


	//# FIXME_I
	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			// FIXME_I:
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("purgeReadings - attach new DB thread :%s: dbHandle :%X:", threadId.str().c_str(), this->getDbHandle());

			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}


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

		string sql_cmd;
		// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
		{
			// SQL - start
			sql_cmd = R"(
				SELECT MAX(rowid)
				FROM
				(
			)";

			// SQL - union of all the readings tables
			string sql_cmd_base;
			string sql_cmd_tmp;
			sql_cmd_base = " SELECT  MAX(rowid) rowid FROM _dbname_._tablename_ ";
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
			sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, assetCodes);
			sql_cmd += sql_cmd_tmp;

			// SQL - end
			sql_cmd += R"(
				) as readings_1
			)";
		}

		rc = SQLexec(dbHandle,
					 sql_cmd.c_str(),
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

	Logger::getLogger()->debug("purgeReadings rowidLimit %lu", rowidLimit);

	{
		char *zErrMsg = NULL;
		int rc;

		string sql_cmd;
		// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
		{
			// SQL - start
			sql_cmd = R"(
				SELECT MIN(rowid)
				FROM
				(
			)";

			// SQL - union of all the readings tables
			string sql_cmd_base;
			string sql_cmd_tmp;
			sql_cmd_base = " SELECT  MIN(rowid) rowid FROM _dbname_._tablename_ ";
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
			sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, assetCodes);
			sql_cmd += sql_cmd_tmp;

			// SQL - end
			sql_cmd += R"(
				) as readings_1
			)";
		}

		rc = SQLexec(dbHandle,
					 sql_cmd.c_str(),
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

	Logger::getLogger()->debug("purgeReadings minrowidLimit %lu", minrowidLimit);

	if (age == 0)
	{
		/*
		 * An age of 0 means remove the oldest hours data.
		 * So set age based on the data we have and continue.
		 */
		string sql_cmd;
		// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
		{
			// SQL - start
			sql_cmd = R"(
				SELECT (strftime('%s','now', 'utc') - strftime('%s', MIN(user_ts)))/360
				FROM
				(
			)";

			// SQL - union of all the readings tables
			string sql_cmd_base;
			string sql_cmd_tmp;
			sql_cmd_base = " SELECT MIN(user_ts) user_ts FROM _dbname_._tablename_  WHERE rowid <= " + to_string(rowidLimit);
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
			sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, assetCodes);
			sql_cmd += sql_cmd_tmp;

			// SQL - end
			sql_cmd += R"(
				) as readings_1
			)";

		}

		SQLBuffer oldest;
		oldest.append(sql_cmd);
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

		Logger::getLogger()->debug("purgeReadings purge_readings :%d: age :%d:", purge_readings, age);
	}
	Logger::getLogger()->debug("purgeReadings: purge_readings %d", age);


	{
		/*
		 * Refine rowid limit to just those rows older than age hours.
		 */
		char *zErrMsg = NULL;
		int rc;
		unsigned long l = minrowidLimit;
		unsigned long r = ((flags & 0x01) && sent) ? min(sent, rowidLimit) : rowidLimit;
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

			string sql_cmd;
			// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
			{
				// SQL - start
				// MIN is used to ensure just 1 row is returned
				sql_cmd = R"(
					select id
					FROM
					(
				)";

				// SQL - union of all the readings tables
				string sql_cmd_base;
				string sql_cmd_tmp;
				sql_cmd_base = " SELECT id FROM _dbname_._tablename_  WHERE rowid = " + to_string(m) + " AND user_ts < datetime('now' , '-" +to_string(age) + " hours')";
				ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
				sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, assetCodes);
				sql_cmd += sql_cmd_tmp;

				// SQL - end
				sql_cmd += R"(
					) as readings_1
				)";

			}

			SQLBuffer sqlBuffer;
			sqlBuffer.append(sql_cmd);
			sqlBuffer.append(';');
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

		Logger::getLogger()->debug("purgeReadings m :%lu: rowidMin :%lu: ",m,  rowidMin);
	}

	//logger->info("Purge collecting unsent row count");
	if ((flags & 0x01) == 0)
	{
		char *zErrMsg = NULL;
		int rc;
		int lastPurgedId;

		string sql_cmd;
		// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
		{
			// SQL - start
			// MIN is used to ensure just 1 row is returned
			sql_cmd = R"(
					select id
					FROM
					(
				)";

			// SQL - union of all the readings tables
			string sql_cmd_base;
			string sql_cmd_tmp;
			sql_cmd_base = " SELECT id FROM _dbname_._tablename_  WHERE rowid = " + to_string(rowidLimit) + " ";
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
			sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, assetCodes);
			sql_cmd += sql_cmd_tmp;

			// SQL - end
			sql_cmd += R"(
					) as readings_1
				)";

		}

		SQLBuffer idBuffer;
		idBuffer.append(sql_cmd);
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

		Logger::getLogger()->debug("purgeReadings lastPurgedId :%d: unsentPurged :%ld:"  ,lastPurgedId, unsentPurged);
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

	ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();

	while (rowidMin < rowidLimit)
	{
		blocks++;
		rowidMin += purgeBlockSize;
		if (rowidMin > rowidLimit)
		{
			rowidMin = rowidLimit;
		}
		SQLBuffer sql;
		sql.append("DELETE FROM  _dbname_._tablename_ WHERE rowid <= ");
		sql.append(rowidMin);
		sql.append(';');
		const char *query = sql.coalesce();

		logSQL("ReadingsPurge", query);

		int rc;
		{
		//unique_lock<mutex> lck(db_mutex);
//		if (m_writeAccessOngoing) db_cv.wait(lck);

		START_TIME;
		rc = readCat->purgeAllReadings(dbHandle, query ,&zErrMsg, &rowsAffected);
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

#endif

#ifndef SQLITE_SPLIT_READINGS
/**
 * Purge readings from the reading table
 */
unsigned int  Connection::purgeReadingsByRows(unsigned long rows,
					unsigned int flags,
					unsigned long sent,
					std::string& result)
{
unsigned long  deletedRows = 0, unsentPurged = 0, unsentRetained = 0, numReadings = 0;
unsigned long limit = 0;
string sql_cmd;
vector<string>  assetCodes;

	Logger *logger = Logger::getLogger();

	//# FIXME_I
	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			// FIXME_I:
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("purgeReadingsByRows - attach new DB thread :%s: dbHandle :%X:", threadId.str().c_str(), this->getDbHandle());

			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}

	logger->info("Purge by Rows called");
	if ((flags & 0x01) == 0x01)
	{
		limit = sent;
		logger->info("Sent is %d", sent);
	}
	logger->info("Purge by Rows called with flags %x, rows %d, limit %d", flags, rows, limit);
	// Don't save unsent rows
	int rowcount;
	do {
		char *zErrMsg = NULL;
		int rc;

		// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
		{
			// SQL - start
			// MIN is used to ensure just 1 row is returned
			sql_cmd = R"(
				SELECT  SUM(rowid)
					FROM
					(
				)";

			// SQL - union of all the readings tables
			string sql_cmd_base;
			string sql_cmd_tmp;
			sql_cmd_base = " select count(rowid) rowid FROM _dbname_._tablename_ ";
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
			sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base, assetCodes);
			sql_cmd += sql_cmd_tmp;

			// SQL - end
			sql_cmd += R"(
					) as readings_1
				)";
		}

		rc = SQLexec(dbHandle,
			sql_cmd.c_str(),
			rowidCallback,
			&rowcount,
			&zErrMsg);

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phaase 0, fetching row count", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
		if (rowcount <= rows)
		{
			logger->info("Row count %d is less than required rows %d", rowcount, rows);
			break;
		}
		int minId;

		// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
		{
			// SQL - start
			// MIN is used to ensure just 1 row is returned
			sql_cmd = R"(
				SELECT  MIN(rowid)
					FROM
					(
				)";

			// SQL - union of all the readings tables
			string sql_cmd_base;
			string sql_cmd_tmp;
			sql_cmd_base = " SELECT MIN(rowid) rowid FROM _dbname_._tablename_ ";
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
			sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base ,assetCodes);
			sql_cmd += sql_cmd_tmp;

			// SQL - end
			sql_cmd += R"(
					) as readings_1
				)";
		}

		rc = SQLexec(dbHandle,
					 sql_cmd.c_str(),
		     rowidCallback,
		     &minId,
		     &zErrMsg);

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phaase 0, fetching minimum id", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
		int maxId;
		// Generate a single SQL statement that using a set of UNION considers all the readings table in handling
		{
			// SQL - start
			// MIN is used to ensure just 1 row is returned
			sql_cmd = R"(
				SELECT  MAX(id)
					FROM
					(
				)";

			// SQL - union of all the readings tables
			string sql_cmd_base;
			string sql_cmd_tmp;
			sql_cmd_base = " SELECT MAX(id) id FROM _dbname_._tablename_ ";
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();
			sql_cmd_tmp = readCat->sqlConstructMultiDb(sql_cmd_base ,assetCodes);
			sql_cmd += sql_cmd_tmp;

			// SQL - end
			sql_cmd += R"(
					) as readings_1
				)";

		}

		rc = SQLexec(dbHandle,
					 sql_cmd.c_str(),
		     rowidCallback,
		     &maxId,
		     &zErrMsg);

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phaase 0, fetching maximum id", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
		int deletePoint = minId + 10000;
		if (maxId - deletePoint < rows || deletePoint > maxId)
			deletePoint = maxId - rows;
		if (limit && limit > deletePoint)
		{
			deletePoint = limit;
		}
		SQLBuffer sql;

		logger->info("RowCount %d, Max Id %d, min Id %d, delete point %d", rowcount, maxId, minId, deletePoint);

		sql.append("DELETE FROM  _dbname_._tablename_ WHERE id <= ");
		sql.append(deletePoint);
		const char *query = sql.coalesce();

		{
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();


			//unique_lock<mutex> lck(db_mutex);
//			if (m_writeAccessOngoing) db_cv.wait(lck);

			// Exec DELETE query: no callback, no resultset
			rc = readCat->purgeAllReadings(dbHandle, query ,&zErrMsg);

			int rowsAffected = sqlite3_changes(dbHandle);
			deletedRows += rowsAffected;
			numReadings = rowcount - rowsAffected;
			// Release memory for 'query' var
			delete[] query;
			logger->debug("Deleted %d rows", rowsAffected);
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
	logger->info("Purge by Rows complete: %s", result.c_str());
	return deletedRows;
}
#endif

/**
 * Logs an error
 *
 */
void ReadingsCatalogue::raiseError(const char *operation, const char *reason, ...)
{
	char	tmpbuf[512];

	va_list ap;
	va_start(ap, reason);
	vsnprintf(tmpbuf, sizeof(tmpbuf), reason, ap);
	va_end(ap);
	Logger::getLogger()->error("ReadingsCatalogues error: %s", tmpbuf);
}

// FIXME_I:
bool ReadingsCatalogue::configurationRetrieve()
{
	string sql_cmd;
	int rc;
	int id;
	int nCols;
	sqlite3_stmt *stmt;
	sqlite3 *dbHandle;

	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection *connection = manager->allocate();
	dbHandle = connection->getDbHandle();

	// Retrieves the global_id from thd DB
	{
		sql_cmd = " SELECT global_id, db_id_Last FROM " READINGS_DB ".configuration_readings ";

		if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
		{
			raiseError("configurationRetrieve", sqlite3_errmsg(dbHandle));
			return false;
		}

		if (SQLStep(stmt) != SQLITE_ROW)
		{
			m_ReadingsGlobalId = 1;
			m_dbIdLast = 0;

			sql_cmd = " INSERT INTO " READINGS_DB ".configuration_readings VALUES (" + to_string(m_ReadingsGlobalId) + "," + to_string(m_dbIdLast) + ")";

			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("configurationRetrieve insert :%s: ", sql_cmd.c_str());
			Logger::getLogger()->setMinLevel("warning");

			if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
			{
				raiseError("configurationRetrieve", sqlite3_errmsg(dbHandle));
				return false;
			}
		}
		else
		{
			nCols = sqlite3_column_count(stmt);
			m_ReadingsGlobalId = sqlite3_column_int(stmt, 0);
			m_dbIdLast = sqlite3_column_int(stmt, 1);
		}
	}

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("configurationRetrieve m_ReadingsGlobalId :%d: m_dbIdLast :%d: ", (int) m_ReadingsGlobalId, m_dbIdLast);
	Logger::getLogger()->setMinLevel("warning");

	sqlite3_finalize(stmt);
	manager->release(connection);

	return true;
}



/**
 * Retrieves the global id stored in SQLite and if it is not possible
 * it calculates the value from the readings tables executing a max(id) on each table.
 *
 * Once retrieved or calculated,
 * It updates the value into SQlite to -1 to force a calculation at the next plugin init (Fledge starts)
 * in the case the proper value was not stored as the plugin shutdown (when Fledge is stopped) was not called.
 *
 */
bool ReadingsCatalogue::evaluateGlobalId ()
{
	string sql_cmd;
	int rc;
	int id;
	int nCols;
	sqlite3_stmt *stmt;
	sqlite3 *dbHandle;

	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection *connection = manager->allocate();
	dbHandle = connection->getDbHandle();

	// Retrieves the global_id from thd DB
	{
		sql_cmd = " SELECT global_id FROM " READINGS_DB ".configuration_readings ";

		if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
		{
			raiseError("evaluateGlobalId", sqlite3_errmsg(dbHandle));
			return false;
		}

		if (SQLStep(stmt) != SQLITE_ROW)
		{
			m_ReadingsGlobalId = 1;

			sql_cmd = " INSERT INTO " READINGS_DB ".configuration_readings VALUES (" + to_string(m_ReadingsGlobalId) + ", 0)";

			//# FIXME_I
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->debug("evaluateGlobalId insert :%s: ", sql_cmd.c_str());
			Logger::getLogger()->setMinLevel("warning");

			if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
			{
				raiseError("evaluateGlobalId", sqlite3_errmsg(dbHandle));
				return false;
			}
		}
		else
		{
			nCols = sqlite3_column_count(stmt);
			m_ReadingsGlobalId = sqlite3_column_int(stmt, 0);
		}
	}

	id = m_ReadingsGlobalId;
	Logger::getLogger()->debug("evaluateGlobalId - global id from the DB :%d:", id);

	if (m_ReadingsGlobalId == -1)
	{
		m_ReadingsGlobalId = calculateGlobalId (dbHandle);
	}

	id = m_ReadingsGlobalId;
	Logger::getLogger()->debug("evaluateGlobalId - global id from the DB :%d:", id);

	// Set the global_id in the DB to -1 to force a calculation at the restart
	// in case the shutdown is not executed and the proper value stored
	{
		sql_cmd = " UPDATE " READINGS_DB ".configuration_readings SET global_id=-1;";

		if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
		{
			raiseError("evaluateGlobalId", sqlite3_errmsg(dbHandle));
			return false;
		}
	}

	sqlite3_finalize(stmt);
	manager->release(connection);

	return true;
}

/**
 * Stores the global id into SQlite
 *
 */
bool ReadingsCatalogue::storeGlobalId ()
{
	string sql_cmd;
	int rc;
	int id;
	int nCols;
	sqlite3_stmt *stmt;
	sqlite3 *dbHandle;

	int i;
	i = m_ReadingsGlobalId;
	Logger::getLogger()->debug("storeGlobalId m_globalId :%d: ", i);


	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection *connection = manager->allocate();
	dbHandle = connection->getDbHandle();

	sql_cmd = " UPDATE " READINGS_DB ".configuration_readings SET global_id=" + to_string(m_ReadingsGlobalId);

	if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
	{
		raiseError("storeGlobalId", sqlite3_errmsg(dbHandle));
		return false;
	}

	manager->release(connection);

	return true;
}

/**
 * Calculates the value from the readings tables executing a max(id) on each table.
 *
 */
int ReadingsCatalogue::calculateGlobalId (sqlite3 *dbHandle)
{
	string sql_cmd;
	string dbReadingsName;
	string dbName;

	int rc;
	int id;
	int nCols;

	sqlite3_stmt *stmt;
	id = 1;

	// Prepare the sql command to calculate the global id from the rows in the DB
	{
		sql_cmd = R"(
			SELECT
				max(id) id
			FROM
			(
		)";

		bool firstRow = true;
		if (m_AssetReadingCatalogue.empty())
		{
			sql_cmd += " SELECT max(id) id FROM " READINGS_DB ".readings_1 ";
		}
		else
		{
			for (auto &item : m_AssetReadingCatalogue)
			{
				if (!firstRow)
				{
					sql_cmd += " UNION ";
				}

				dbReadingsName = generateReadingsName(item.second.first);
				dbName = generateDbName(item.second.second);

				sql_cmd += " SELECT max(id) id FROM " + dbName + "." + dbReadingsName + " ";
				firstRow = false;
			}
		}
		sql_cmd += ") AS tb";
	}


	if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
	{
		raiseError("calculateGlobalId", sqlite3_errmsg(dbHandle));
		return false;
	}

	if (SQLStep(stmt) != SQLITE_ROW)
	{
		id = 1;
	}
	else
	{
		nCols = sqlite3_column_count(stmt);
		id = sqlite3_column_int(stmt, 0);
		// m_globalId stores then next value to be used
		id++;
	}

	Logger::getLogger()->debug("calculateGlobalId - global id evaluated :%d:", id);
	sqlite3_finalize(stmt);

	return (id);
}

/**
 * Loads the reading catalogue stored in SQLite into an in memory structure
 *
 */
bool  ReadingsCatalogue::loadAssetReadingCatalogue()
{
	int nCols;
	int tableId, dbId, maxDbID;
	char *asset_name;
	sqlite3_stmt *stmt;
	int rc;
	sqlite3		*dbHandle;

	ostringstream threadId;
	threadId << std::this_thread::get_id();

	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection        *connection = manager->allocate();
	dbHandle = connection->getDbHandle();

	// loads readings catalog from the db
	const char *sql_cmd = R"(
		SELECT
			table_id,
			db_id,
			asset_code
		FROM  )" READINGS_DB R"(.asset_reading_catalogue
		ORDER BY table_id;
	)";


	maxDbID = 1;
	if (sqlite3_prepare_v2(dbHandle,sql_cmd,-1, &stmt,NULL) != SQLITE_OK)
	{
		raiseError("retrieve asset_reading_catalogue", sqlite3_errmsg(dbHandle));
		return false;
	}
	else
	{
		// Iterate over all the rows in the resultSet
		while ((rc = SQLStep(stmt)) == SQLITE_ROW)
		{
			nCols = sqlite3_column_count(stmt);

			tableId = sqlite3_column_int(stmt, 0);
			dbId = sqlite3_column_int(stmt, 1);
			asset_name = (char *)sqlite3_column_text(stmt, 2);

			if (dbId > maxDbID)
				maxDbID = dbId;

			Logger::getLogger()->debug("loadAssetReadingCatalogue - thread :%s: reading Id :%d: dbId :%d: asset name :%s: max db Id :%d:", threadId.str().c_str(), tableId, dbId,  asset_name, maxDbID);

			auto newItem = make_pair(tableId,dbId);
			auto newMapValue = make_pair(asset_name,newItem);
			m_AssetReadingCatalogue.insert(newMapValue);

		}

		sqlite3_finalize(stmt);
	}
	manager->release(connection);
	m_dbIdCurrent = maxDbID;

	Logger::getLogger()->debug("loadAssetReadingCatalogue maxdb :%d:", m_dbIdCurrent);

	return true;
}

// FIXME_I:
void ReadingsCatalogue::setUsedDbId(int dbId) {

	m_dbIdList.push_back(dbId);
}

// FIXME_I:
void ReadingsCatalogue::prepareAllDbs() {

	int dbId, dbIdStart, dbIdEnd;


	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("prepareAllDbs dbIdCurrent :%d: dbIdLast :%d:", m_dbIdCurrent, m_dbIdLast);

	if (m_dbIdLast == 0)
	{
		//# FIXME_I
		Logger::getLogger()->debug("prepareAllDbs initial stage XXX");

		// Initial stage - creates the databases requested by the preallocation
		dbIdStart = 2;
		dbIdEnd = dbIdStart + nDbPreallocate - 2;

		preallocateNewDbsRange(dbIdStart, dbIdEnd);

		m_dbIdLast = dbIdEnd;
	} else
	{
		//# FIXME_I
		Logger::getLogger()->debug("prepareAllDbs next stage XXX");

		// Following runs - attaches all the databases
		for (dbId = 2; dbId <= m_dbIdLast ; dbId++ )
		{
			m_dbIdList.push_back(dbId);
		}
		attachDbsToAllConnections();
	}

	m_dbNAvailable = (m_dbIdLast - m_dbIdCurrent) - nDbLeftFreeBeforeAllocate;

	Logger::getLogger()->debug("prepareAllDbs m_dbNAvailable :%d:", m_dbNAvailable);

	//# FIXME_I
	Logger::getLogger()->setMinLevel("warning");


}

// FIXME_I:
void ReadingsCatalogue::preallocateNewDbsRange(int dbIdStart, int dbIdEnd) {

	int dbId;
	int startReadingsId;
	tyReadingsAvailable readingsAvailable;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("preallocateNewDbsRange: START - start :%d: end :%d: ", dbIdStart, dbIdEnd);

	for (dbId = dbIdStart; dbId <= dbIdEnd; dbId++)
	{
		readingsAvailable = evaluateLastReadingAvailable(NULL, dbId - 1);
		startReadingsId = readingsAvailable.lastReadings +1;
		createNewDB(NULL,  dbId, startReadingsId, true);

		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("preallocateNewDbsRange - create new dbs - dbId :%d: startReadingsIdOnDB :%d:", dbId, startReadingsId);

	}

	// FIXME_I:
	//attachDbsToAllConnections();
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("preallocateNewDbsRange: END - start :%d: end :%d:", dbIdStart, dbIdEnd);


	//# FIXME_I
	Logger::getLogger()->setMinLevel("warning");
}



/**
 * Generates a list of all the used databases
 *
 */
void ReadingsCatalogue::getAllDbs(vector<int> &dbIdList) {

	int dbId;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");

	Logger::getLogger()->debug("getAllDbs - Used");

	for (auto &item : m_AssetReadingCatalogue) {

		dbId = item.second.second;
		if (dbId > 1)
		{
			if (std::find(dbIdList.begin(), dbIdList.end(), dbId) ==  dbIdList.end() )
			{
				dbIdList.push_back(dbId);
				Logger::getLogger()->debug("getAllDbs  DB :%d:", dbId);
			}

		}
	}

	Logger::getLogger()->debug("getAllDbs - created");

	for (auto &dbId : m_dbIdList) {

		if (std::find(dbIdList.begin(), dbIdList.end(), dbId) ==  dbIdList.end() )
		{
			dbIdList.push_back(dbId);
			Logger::getLogger()->debug("getAllDbs DB created :%d:", dbId);
		}
	}

	sort(dbIdList.begin(), dbIdList.end());

	// FIXME_I:
	Logger::getLogger()->setMinLevel("warning");

}




// FIXME_I:
void ReadingsCatalogue::getNewDbs(vector<int> &dbIdList) {

	int dbId;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");

	Logger::getLogger()->debug("getAllDbs - Newly created");

	for (auto &dbId : m_dbIdList) {

		if (std::find(dbIdList.begin(), dbIdList.end(), dbId) ==  dbIdList.end() )
		{
			dbIdList.push_back(dbId);
			Logger::getLogger()->debug("getAllDbs DB created :%d:", dbId);
		}
	}

	sort(dbIdList.begin(), dbIdList.end());

	// FIXME_I:
	Logger::getLogger()->setMinLevel("warning");

}



/**
 * Enable WAL on the provided database file
 *
 */
bool ReadingsCatalogue::enableWAL(string &dbPathReadings) {

	int rc;
	sqlite3 *dbHandle;

	Logger::getLogger()->debug("enableWAL on :%s:", dbPathReadings.c_str());

	rc = sqlite3_open(dbPathReadings.c_str(), &dbHandle);
	if(rc != SQLITE_OK)
	{
		raiseError("enableWAL", sqlite3_errmsg(dbHandle));
		return false;
	}
	else
	{
		// Enables the WAL feature
		rc = sqlite3_exec(dbHandle, DB_CONFIGURATION, NULL, NULL, NULL);
		if (rc != SQLITE_OK)
		{
			raiseError("enableWAL", sqlite3_errmsg(dbHandle));
			return false;
		}
	}
	sqlite3_close(dbHandle);
	return true;
}

// FIXME_I:
/**
 * Attach a database to all the connections, idle and  inuse
 *
 * @param path  - path of the database to attach
 * @param alias - alias to be assigned to the attached database
 */
bool ReadingsCatalogue::attachDb(sqlite3 *dbHandle, std::string &path, std::string &alias)
{
	int rc;
	std::string sqlCmd;
	bool result;
	char *zErrMsg = NULL;

	result = true;


	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("- attachDb start");

	sqlCmd = "ATTACH DATABASE '" + path + "' AS " + alias + ";";


	Logger::getLogger()->debug("-  attachDb end - path :%s: alais :%s: cmd :%s:" , path.c_str(), alias.c_str() , sqlCmd.c_str() );
	// FIXME_I:
	//rc = SQLITE_OK;
	rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
	if (rc != SQLITE_OK)
	{
		Logger::getLogger()->error("- attachDb - It was not possible to attach the db :%s: to the connection :%X:, error :%s:", path.c_str(), dbHandle, zErrMsg);
		result = false;
	}

	//# FIXME_I
	Logger::getLogger()->debug("-  attachDb end - path :%s: alais :%s:" , path.c_str(), alias.c_str() );
	Logger::getLogger()->setMinLevel("warning");

	return (result);
}


/**
 * Attaches all the defined SQlite database to all the connections and enable the WAL
 *
 */
bool ReadingsCatalogue::connectionAttachDbList(sqlite3 *dbHandle, vector<int> &dbIdList)
{
	int dbId;
	string dbPathReadings;
	string dbAlias;
	int item;

	bool result;

	result = true;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("connectionAttachDbList  start dbHandle :%X:" ,dbHandle);
	Logger::getLogger()->setMinLevel("warning");

	while (!dbIdList.empty())
	{
		item = dbIdList.back();

		dbPathReadings = generateDbFilePah(item);
		dbAlias = generateDbAlias(item);

		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("XXX connectionAttachDbList:  dbHandle :%X: dbId :%d: path :%s: alias :%s:",dbHandle, item, dbPathReadings.c_str(), dbAlias.c_str());

		result = attachDb(dbHandle, dbPathReadings, dbAlias);
		dbIdList.pop_back();

		// FIXME_I:
		Logger::getLogger()->setMinLevel("warning");
	}

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("connectionAttachDbList  end Connection :%X:" ,dbHandle);
	Logger::getLogger()->setMinLevel("warning");


	return (result);
}


/**
 * Attaches all the defined SQlite database to all the connections and enable the WAL
 *
 */
bool ReadingsCatalogue::connectionAttachAllDbs(sqlite3 *dbHandle)
{
	int dbId;
	string dbPathReadings;
	string dbAlias;
	vector<int> dbIdList;
	bool result;

	result = true;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("connectionAttachAllDbs  start Connection :%X:" ,dbHandle);
	Logger::getLogger()->setMinLevel("warning");


	getAllDbs(dbIdList);

	for(int item : dbIdList)
	{
		dbPathReadings = generateDbFilePah(item);
		dbAlias = generateDbAlias(item);

		result = attachDb(dbHandle, dbPathReadings, dbAlias);
		if (! result)
			break;

		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");

		Logger::getLogger()->debug("connectionAttachAllDbs: dbId :%d: path :%s: alias :%s:", item, dbPathReadings.c_str(), dbAlias.c_str());

		// FIXME_I:
		Logger::getLogger()->setMinLevel("warning");
	}

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("connectionAttachAllDbs  end Connection :%X:" ,dbHandle);
	Logger::getLogger()->setMinLevel("warning");


	return (result);
}


/**
 * Attaches all the defined SQlite database to all the connections and enable the WAL
 *
 */
bool ReadingsCatalogue::attachDbsToAllConnections()
{
	int dbId;
	string dbPathReadings;
	string dbAlias;
	vector<int> dbIdList;
	bool result;

	result = true;

	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection        *connection = manager->allocate();

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("attachDbsToAllConnections DBG");
	Logger::getLogger()->setMinLevel("warning");


	getAllDbs(dbIdList);

	for(int item : dbIdList)
	{
		dbPathReadings = generateDbFilePah(item);
		dbAlias = generateDbAlias(item);

		enableWAL(dbPathReadings);
		// Attached the new db to the connections
		result = manager->attachNewDb(dbPathReadings, dbAlias);
		if (! result)
			break;

		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");

		Logger::getLogger()->debug("attachDbsToAllConnections: dbId :%d: path :%s: alias :%s:", item, dbPathReadings.c_str(), dbAlias.c_str());

		// FIXME_I:
		Logger::getLogger()->setMinLevel("warning");
	}

	manager->release(connection);

	return (result);
}

// FIXME_I:
void ReadingsCatalogue::multipleReadingsInit()
{

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("multipleReadingsInit XX2");
	Logger::getLogger()->setMinLevel("warning");

	loadAssetReadingCatalogue();

	preallocateReadingsTables(1);   // on the first database
	configurationRetrieve();
	prepareAllDbs();
	preallocateReadingsTables(0);   // on the last database

	evaluateGlobalId();
}

/**
 * Creates all the needed readings tables considering the tables already defined in the database
 * and the number of tables to have on each database.
 *
 */
void ReadingsCatalogue::preallocateReadingsTables(int dbId)
{
	int readingsToAllocate;
	int readingsToCreate;
	int startId;

	if (dbId == 0 )
		dbId = m_dbIdCurrent;

	tyReadingsAvailable readingsAvailable;

	string dbName;

	readingsAvailable.lastReadings = 0;
	readingsAvailable.tableCount = 0;

	// Identifies last readings available
	readingsAvailable = evaluateLastReadingAvailable(NULL, dbId);
	readingsToAllocate = getNReadingsAllocate();

	if (readingsAvailable.tableCount < readingsToAllocate)
	{
		readingsToCreate = readingsToAllocate - readingsAvailable.tableCount;
		startId = readingsAvailable.lastReadings + 1;
		createReadingsTables(NULL, dbId, startId, readingsToCreate);
	}

	m_nReadingsAvailable = readingsToAllocate - getUsedTablesDbId(dbId);


	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("preallocateReadingsTables: dbId :%d: nReadingsAvailable :%d: lastReadingsCreated :%d: tableCount :%d:", m_dbIdCurrent, m_nReadingsAvailable, readingsAvailable.lastReadings, readingsAvailable.tableCount);
	Logger::getLogger()->setMinLevel("warning");

}

/**
 * Generates the full path of the SQLite database from the given the id
 *
 */
string ReadingsCatalogue::generateDbFilePah(int dbId)
{
	string dbPathReadings;

	char *defaultReadingsConnection;
	char defaultReadingsConnectionTmp[1000];

	defaultReadingsConnection = getenv("DEFAULT_SQLITE_DB_READINGS_FILE");

	if (defaultReadingsConnection == NULL)
	{
		dbPathReadings = getDataDir();
	}
	else
	{
		// dirname modify the content of the parameter
		strncpy ( defaultReadingsConnectionTmp, defaultReadingsConnection, sizeof(defaultReadingsConnectionTmp) );
		dbPathReadings  = dirname(defaultReadingsConnectionTmp);
	}

	if (dbPathReadings.back() != '/')
		dbPathReadings += "/";

	dbPathReadings += generateDbFileName(dbId);

	return  (dbPathReadings);
}

// FIXME_I:
bool ReadingsCatalogue::latestDbUpdate(sqlite3 *dbHandle, int newDbId)
{
	string sql_cmd;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");

	Logger::getLogger()->debug("latestDbUpdate - dbHandle :%X: newDbId :%d:", dbHandle, newDbId);

	{
		sql_cmd = " UPDATE " READINGS_DB ".configuration_readings SET db_id_Last=" + to_string(newDbId) + ";";

		if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
		{
			raiseError("latestDbUpdate", sqlite3_errmsg(dbHandle));
			return false;
		}
	}

	//# FIXME_I
	Logger::getLogger()->setMinLevel("warning");

	return true;
}


/**
 * Creates a new database using m_dbId as datbase id
 *
 */
bool  ReadingsCatalogue::createNewDB(sqlite3 *dbHandle, int newDbId, int startId, bool attachAllDb)
{
	int rc;
	int nTables;

	int readingsToAllocate;
	int readingsToCreate;

	string sqlCmd;
	string dbPathReadings;
	string dbAlias;

	struct stat st;
	bool dbAlreadyPresent=false;
	bool result;
	bool connAllocated;
	Connection *connection;

	connAllocated = false;
	result = true;

	ConnectionManager *manager = ConnectionManager::getInstance();
	ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();

	if (dbHandle == NULL)
	{
		connection = manager->allocate();
		dbHandle = connection->getDbHandle();
		connAllocated = true;
	}

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->info("createNewDB V3: connection :%X: dbHandle :%X:" ,connection, dbHandle);

	// Creates the DB data file
	{
		dbPathReadings = generateDbFilePah(newDbId);

		dbAlreadyPresent = false;
		if(stat(dbPathReadings.c_str(),&st) == 0)
		{
			Logger::getLogger()->info("createNewDB: database file :%s: already present, creation skipped " , dbPathReadings.c_str() );
			dbAlreadyPresent = true;
		}
		else
		{
			Logger::getLogger()->debug("createNewDB: new database created :%s:", dbPathReadings.c_str());
		}
		enableWAL(dbPathReadings);

		// FIXME_I:
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("createNewDB latestDbUpdate");
		Logger::getLogger()->setMinLevel("warning");
		latestDbUpdate(dbHandle, newDbId);

	}
	readingsToAllocate = getNReadingsAllocate();
	readingsToCreate = readingsToAllocate;

	// FIXME_I:
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("- -createNewDB: generateDbAlias");

	// Attached the new db to the connections
	dbAlias = generateDbAlias(newDbId);

	if (attachAllDb)
	{

		// FIXME_I:
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("- -createNewDB: attachNewDb ALL");

		result = manager->attachNewDb(dbPathReadings, dbAlias);
	} else {

		// FIXME_I:
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("- -createNewDB: attachDb SINGLE");

		// FIXME_I:
		result = readCat->attachDb(dbHandle, dbPathReadings, dbAlias);

		// FIXME_I:
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("- -createNewDB: attachRequestNewDb");

		// FIXME_I:
		result = manager->attachRequestNewDb(newDbId, dbHandle);

	}



	if (result)
	{
		// FIXME_I:
		setUsedDbId(newDbId);

		if (dbAlreadyPresent)
		{
			tyReadingsAvailable readingsAvailable = evaluateLastReadingAvailable(dbHandle, newDbId);

			if (readingsAvailable.lastReadings == -1)
			{
				Logger::getLogger()->error("createNewDB: database file :%s: is already present but it is not possible to evaluate the readings table already present" , dbPathReadings.c_str() );
				result = false;
			}
			else
			{
				readingsToCreate = readingsToAllocate - readingsAvailable.tableCount;
				startId = readingsAvailable.lastReadings +1;
				Logger::getLogger()->info("createNewDB: database file :%s: is already present, creating readings tables - from id :%d: n :%d: " , dbPathReadings.c_str(), startId, readingsToCreate);
			}
		}

		if (readingsToCreate > 0)
		{
			// FIXME_I:
			createReadingsTables(dbHandle, newDbId ,startId, readingsToCreate);

			Logger::getLogger()->info("createNewDB: database file :%s: created readings table - from id :%d: n :%d: " , dbPathReadings.c_str(), startId, readingsToCreate);
		}
		m_nReadingsAvailable = readingsToAllocate;
	}

	if (connAllocated)
	{
		manager->release(connection);
	}

	return (result);
}

/**
 * Creates a set of reading tables in the given database id
 *
 * @param dbId        - Database id on which the tables should be created
 * @param idStartFrom - Id from with to start to create the tables
 * @param nTables     - Number of table to create
 */
bool  ReadingsCatalogue::createReadingsTables(sqlite3 *dbHandle, int dbId, int idStartFrom, int nTables)
{
	string createReadings, createReadingsIdx;
	string dbName;
	string dbReadingsName;
	int tableId;
	int rc;
	int readingsIdx;
	bool newConnection;
	Connection        *connection;

	Logger *logger = Logger::getLogger();
	newConnection = false;

	ConnectionManager *manager = ConnectionManager::getInstance();

	if (dbHandle == NULL)
	{
		connection = manager->allocate();
		dbHandle = connection->getDbHandle();
		newConnection = true;
	}

	// FIXME_I:
	Logger::getLogger()->setMinLevel("debug");
	logger->info("Creating :%d: readings table in advance starting id :%d:", nTables, idStartFrom);
	logger->debug("createReadingsTables start dbHandle :%X: ", dbHandle);

	dbName = generateDbName(dbId);

	for (readingsIdx = 0 ;  readingsIdx < nTables; ++readingsIdx)
	{
		tableId = idStartFrom + readingsIdx;
		dbReadingsName = generateReadingsName(tableId);

		createReadings = R"(
			CREATE TABLE )" + dbName + "." + dbReadingsName + R"( (
				id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
				reading    JSON                        NOT NULL DEFAULT '{}',
				user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),
				ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))
			);
		)";

		createReadingsIdx = R"(
			CREATE INDEX )" + dbName + "." + dbReadingsName + R"(_ix3 ON readings_)" + to_string(tableId) + R"( (user_ts);
		)";

		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("createReadingsTables table :%s: ", createReadings.c_str());

		rc = SQLExec(dbHandle, createReadings.c_str());
		if (rc != SQLITE_OK)
		{
			raiseError("createReadingsTables", sqlite3_errmsg(dbHandle));
			return false;
		}

		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("createReadingsTables idx :%s: ", createReadingsIdx.c_str());


		rc = SQLExec(dbHandle, createReadingsIdx.c_str());
		if (rc != SQLITE_OK)
		{
			raiseError("createReadingsTables", sqlite3_errmsg(dbHandle));
			return false;
		}
	}

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("createReadingsTables end dbHandle :%X: ", dbHandle);

	if (newConnection)
	{
		manager->release(connection);
	}

	return true;
}

/**
 * Evaluates the latest reading table defined in the provided database id looking at sqlite_master, the SQLite repository
 *
 * @return - a struct containing
 *             lastReadings = the id of the latest reading table defined in the  given database id
 *             tableCount   = Number of tables  given database id in the given database id
 */
ReadingsCatalogue::tyReadingsAvailable  ReadingsCatalogue::evaluateLastReadingAvailable(sqlite3 *dbHandle, int dbId)
{
	string dbName;
	int nCols;
	int id;
	char *asset_name;
	sqlite3_stmt *stmt;
	int rc;
	string tableName;
	tyReadingsAvailable readingsAvailable;

	Connection        *connection;
	bool connAllocated;

	connAllocated = false;

	vector<int> readingsId(getNReadingsAvailable(), 0);

	ConnectionManager *manager = ConnectionManager::getInstance();


	if (dbHandle == NULL)
	{
		connection = manager->allocate();
		dbHandle = connection->getDbHandle();
		connAllocated = true;
	}

	dbName = generateDbName(dbId);

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("Ingest evaluateLastReadingAvailable S1");


	string sql_cmd = R"(
		SELECT name
		FROM  )" + dbName +  R"(.sqlite_master
		WHERE type='table' and name like 'readings_%';
	)";

	if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
	{
		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->error("evaluateLastReadingAvailable :cmd: error :%s:", sql_cmd.c_str(), sqlite3_errmsg(dbHandle));

		raiseError("evaluateLastReadingAvailable", sqlite3_errmsg(dbHandle));
		readingsAvailable.lastReadings = -1;
		readingsAvailable.tableCount = 0;
	}
	else
	{
		//# FIXME_I
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("Ingest evaluateLastReadingAvailable S2");

		// Iterate over all the rows in the resultSet
		readingsAvailable.lastReadings = 0;
		readingsAvailable.tableCount = 0;
		while ((rc = SQLStep(stmt)) == SQLITE_ROW)
		{
			nCols = sqlite3_column_count(stmt);

			tableName = (char *)sqlite3_column_text(stmt, 0);
			id = stoi(tableName.substr (tableName.find('_') + 1));

			if (id > readingsAvailable.lastReadings)
				readingsAvailable.lastReadings = id;

			readingsAvailable.tableCount++;
		}
		//# FIXME_I

		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("Ingest evaluateLastReadingAvailable S3  - tableName :%s: lastReadings :%d:", tableName.c_str(), readingsAvailable.lastReadings);

		sqlite3_finalize(stmt);
	}

	if (connAllocated)
	{
		manager->release(connection);
	}

	//# FIXME_I
	Logger::getLogger()->setMinLevel("warning");


	return (readingsAvailable);
}

/**
 * Checks if there is a reading table still available to be used
 */
bool  ReadingsCatalogue::isReadingAvailable() const
{
	if (m_nReadingsAvailable <= 0)
		return false;
	else
		return true;

}

/**
 * Tracks the allocation of a reading table
 *
 */
void  ReadingsCatalogue::allocateReadingAvailable()
{
	m_nReadingsAvailable--;
}

/**
 * Allocates a reading table to the given asset_code
 *
 * @return - the reading id associated to the provided asset_code
 */
int ReadingsCatalogue::getReadingReference(Connection *connection, const char *asset_code)
{
	sqlite3_stmt *stmt;
	string sql_cmd;
	int rc;
	sqlite3		*dbHandle;

	int readingsId;
	string msg;
	bool success;

	int startReadingsId;
	tyReadingsAvailable readingsAvailable;

	//# FIXME_I
	ostringstream threadId;
	threadId << std::this_thread::get_id();


	success = true;

	dbHandle = connection->getDbHandle();

	Logger *logger = Logger::getLogger();

	auto item = m_AssetReadingCatalogue.find(asset_code);
	if (item != m_AssetReadingCatalogue.end())
	{
		//# An asset already  managed
		readingsId = item->second.first;
	}
	else
	{
		// FIXME_I:
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		//m_mutexAssetReadingCatalogue.lock();

		// FIXME_I:
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("getReadingReference lock after m_mutexAssetReadingCatalogue dbHandle :%X: threadId :%s:", dbHandle, threadId.str().c_str() );

		auto item = m_AssetReadingCatalogue.find(asset_code);
		if (item != m_AssetReadingCatalogue.end())
		{
			readingsId = item->second.first;
		}
		else
		{
			//# Allocate a new block of readings table
			if (! isReadingAvailable () )
			{


				// FIXME_I:
				Logger::getLogger()->setMinLevel("debug");
				Logger::getLogger()->debug("XXX  Allocate a new db dbNAvailable :%d:", m_dbNAvailable);

				if (m_dbNAvailable > 0)
				{
					// DBs already created are available
					m_dbIdCurrent++;
					m_dbNAvailable--;
					m_nReadingsAvailable = getNReadingsAllocate();

					Logger::getLogger()->debug("Allocate a new db - db already available - dbIdCurrent :%d: m_dbIdLast :%d: dbNAvailable  :%d: nReadingsAvailable :%d:  ", m_dbIdCurrent, m_dbIdLast, m_dbNAvailable, m_nReadingsAvailable);
				}
				else
				{
					// Allocates new DBs
					int dbId, dbIdStart, dbIdEnd;

					dbIdStart = m_dbIdLast +1;
					dbIdEnd = m_dbIdLast + nDbToAllocate;

					Logger::getLogger()->debug("Allocate a new db - create new dbs - dbIdCurrent :%d:  dbIdStart :%d: dbIdEnd :%d:", m_dbIdCurrent, dbIdStart, dbIdEnd);

					for (dbId = dbIdStart; dbId <= dbIdEnd; dbId++)
					{
						readingsAvailable = evaluateLastReadingAvailable(dbHandle, dbId - 1);
						startReadingsId = readingsAvailable.lastReadings +1;
						//
						Logger::getLogger()->setMinLevel("debug");
						Logger::getLogger()->debug("Allocate a new db - create new dbs - dbId :%d: startReadingsIdOnDB :%d:", dbId, startReadingsId);

						success = createNewDB(dbHandle,  dbId, startReadingsId, false);
						if (success)
						{
							Logger::getLogger()->debug("Allocate a new db - create new dbs - created :%d:", dbId);
						}
					}
					m_dbIdLast = dbIdEnd;
					m_dbIdCurrent++;
					m_dbNAvailable = (m_dbIdLast - m_dbIdCurrent) - nDbLeftFreeBeforeAllocate;
				}

				readingsId = -1;

				if (success)
				{
					Logger::getLogger()->debug("Allocate a new db - dbIdCurrent :%d:  dbIdLast :%d: dbNAvailable :%d:", m_dbIdCurrent, m_dbIdLast, m_dbNAvailable);
				}


				// FIXME_I:
				Logger::getLogger()->setMinLevel("warning");
			}

			if (success)
			{
				// Associate a reading table to the asset
				{
					// Associate the asset to the reading_id
					{
						readingsId = getMaxReadingsId() + 1;

						auto newItem = make_pair(readingsId, m_dbIdCurrent);
						auto newMapValue = make_pair(asset_code, newItem);
						m_AssetReadingCatalogue.insert(newMapValue);
					}

					// FIXME_I:
					Logger::getLogger()->setMinLevel("debug");
					Logger::getLogger()->debug("getReadingReference: allocate a new reading table for the asset :%s: db Id :%d: readings Id :%d: ", asset_code, m_dbIdCurrent, readingsId);
					Logger::getLogger()->setMinLevel("warning");

					// Allocate the table in the reading catalogue
					{
						sql_cmd =
							"INSERT INTO  " READINGS_DB ".asset_reading_catalogue (table_id, db_id, asset_code) VALUES  ("
							+ to_string(readingsId) + ","
							+ to_string(m_dbIdCurrent) + ","
							+ "\"" + asset_code + "\")";

						rc = SQLExec(dbHandle, sql_cmd.c_str());
						if (rc != SQLITE_OK)
						{
							msg = string(sqlite3_errmsg(dbHandle)) + " asset :" + asset_code + ":";
							raiseError("asset_reading_catalogue update", msg.c_str());
						}
						allocateReadingAvailable();
					}

				}

			}
		}


		// FIXME_I:
		Logger::getLogger()->setMinLevel("debug");
		Logger::getLogger()->debug("getReadingReference end dbHandle :%X: threadId :%s:", dbHandle, threadId.str().c_str() );


		attachSync->unlock();

		//m_mutexAssetReadingCatalogue.unlock();
	}

	return (readingsId);

}

/**
 * Retrieve the maximum database id used
 *
 */
int ReadingsCatalogue::getMaxReadingsId()
{
	int maxId = 0;

	for (auto &item : m_AssetReadingCatalogue) {

		if (item.second.first > maxId)
				maxId = item.second.first;
	}

	return (maxId);
}

/**
 * Calculate the number of reading tables associated to the given database id
 *
 */
int ReadingsCatalogue::getUsedTablesDbId(int dbId)
{
	int count = 0;

	for (auto &item : m_AssetReadingCatalogue) {

		if (item.second.second == dbId)
			count++;
	}

	return (count);
}

/**
 * Delete the content of all the active readings tables using the provided sql command sqlCmdBase
 *
 * @return - returns SQLITE_OK if all the sql commands are properly executed
 */
int  ReadingsCatalogue::purgeAllReadings(sqlite3 *dbHandle, const char *sqlCmdBase, char **zErrMsg, unsigned int *rowsAffected)
{
	string dbReadingsName;
	string dbName;
	string sqlCmdTmp;
	string sqlCmd;
	bool firstRow;
	int rc;

	if (m_AssetReadingCatalogue.empty())
	{
		Logger::getLogger()->debug("purgeAllReadings: no tables defined");
		rc = SQLITE_OK;
	}
	else
	{
		Logger::getLogger()->debug("purgeAllReadings tables defined");

		firstRow = true;
		if  (rowsAffected != nullptr)
			*rowsAffected = 0;

		for (auto &item : m_AssetReadingCatalogue)
		{
			sqlCmdTmp = sqlCmdBase;

			dbReadingsName = generateReadingsName(item.second.first);
			dbName = generateDbName(item.second.second);

			StringReplaceAll (sqlCmdTmp, "_assetcode_", item.first);
			StringReplaceAll (sqlCmdTmp, "_dbname_", dbName);
			StringReplaceAll (sqlCmdTmp, "_tablename_", dbReadingsName);
			sqlCmd += sqlCmdTmp;
			firstRow = false;

			rc = SQLExec(dbHandle, sqlCmdTmp.c_str(), zErrMsg);

			Logger::getLogger()->debug("purgeAllReadings:  rc :%d: cmd :%s:", rc ,sqlCmdTmp.c_str() );

			if (rc != SQLITE_OK)
			{
				break;
			}
			if  (rowsAffected != nullptr)
				*rowsAffected += sqlite3_changes(dbHandle);
		}
	}

	return(rc);

}

/**
 * Constructs a sql command from the given one consisting of a set of UNION ALL commands
 * considering all the readings tables in use
 *
 */
string  ReadingsCatalogue::sqlConstructMultiDb(string &sqlCmdBase, vector<string>  &assetCodes)
{

	//# FIXME_I:
	char tmp_buffer[500000];

	string dbReadingsName;
	string dbName;
	string sqlCmdTmp;
	string sqlCmd;

	string assetCode;
	bool addTable;
	bool addedOne;

	if (m_AssetReadingCatalogue.empty())
	{
		Logger::getLogger()->debug("sqlConstructMultiDb: no tables defined");
		sqlCmd = sqlCmdBase;

		StringReplaceAll (sqlCmd, "_assetcode_", "dummy_asset_code");
		StringReplaceAll (sqlCmd, ".assetcode.", "asset_code");
		StringReplaceAll (sqlCmd, "_dbname_", READINGS_DB);
		StringReplaceAll (sqlCmd, "_tablename_", "readings_1");
	}
	else
	{
		Logger::getLogger()->debug("sqlConstructMultiDb: tables defined");

		bool firstRow = true;
		addedOne = false;

		for (auto &item : m_AssetReadingCatalogue)
		{
			assetCode=item.first;
			addTable = false;

			// Evaluates which tables should be referenced
			if (assetCodes.empty())
				addTable = true;
			else
			{
				if (std::find(assetCodes.begin(), assetCodes.end(), assetCode) != assetCodes.end())
					addTable = true;
			}

			if (addTable)
			{
				addedOne = true;

				sqlCmdTmp = sqlCmdBase;

				if (!firstRow)
				{
					sqlCmd += " UNION ALL ";
				}

				dbReadingsName = generateReadingsName(item.second.first);
				dbName = generateDbName(item.second.second);

				StringReplaceAll(sqlCmdTmp, "_assetcode_", assetCode);
				StringReplaceAll (sqlCmdTmp, ".assetcode.", "asset_code");
				StringReplaceAll(sqlCmdTmp, "_dbname_", dbName);
				StringReplaceAll(sqlCmdTmp, "_tablename_", dbReadingsName);
				sqlCmd += sqlCmdTmp;
				firstRow = false;
			}
		}
		// Add at least one table eventually a dummy one
		if (! addedOne)
		{
			sqlCmd = sqlCmdBase;
			StringReplaceAll (sqlCmd, "_assetcode_", "dummy_asset_code");
			StringReplaceAll (sqlCmd, "_dbname_", READINGS_DB);
			StringReplaceAll (sqlCmd, "_tablename_", "readings_1");
		}
	}

	return(sqlCmd);

}


/**
 * Generates a SQLIte db alis from the database id
 *
 */
string ReadingsCatalogue::generateDbAlias(int dbId)
{

	return (READINGS_DB_NAME_BASE "_" + to_string(dbId));
}

/**
 * Generates a SQLIte database name from the database id
 *
 */
string ReadingsCatalogue::generateDbName(int dbId)
{
	return (READINGS_DB_NAME_BASE "_" + to_string(dbId));
}

/**
 * Generates a SQLITE database file name from the database id
 *
 */
string ReadingsCatalogue::generateDbFileName(int dbId)
{
	return (READINGS_DB_NAME_BASE "_" + to_string (dbId) + ".db");
}

/**
 * Generates the name of the readin table from the given table id
 *
 */
string ReadingsCatalogue::generateReadingsName(int tableId)
{
	return (READINGS_TABLE "_" + to_string(tableId));
}

/**
 * Identifies SQLIte database name from the given table id
 *
 */
string ReadingsCatalogue::generateDbNameFromTableId(int tableId)
{
	string dbName;

	for (auto &item : m_AssetReadingCatalogue)
	{

		if (item.second.first == tableId)
		{
			dbName = READINGS_DB_NAME_BASE "_" + to_string(item.second.second);
			break;
		}
	}
	if (dbName == "")
		dbName = READINGS_DB_NAME_BASE "_1";

	return (dbName);
}

/**
 * SQLIte wrapper to retry statements when the database is locked
 *
 * @param	db	     The open SQLite database
 * @param	sql	     The SQL to execute
 * @param	errmsg	 Error message
 */
int ReadingsCatalogue::SQLExec(sqlite3 *dbHandle, const char *sqlCmd, char **errMsg)
{
	int retries = 0, rc;

	Logger::getLogger()->debug("SQLExec: cmd :%s: ", sqlCmd);

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
		if (rc == SQLITE_LOCKED || rc == SQLITE_BUSY)
		{
			int interval = (retries * RETRY_BACKOFF);
			usleep(interval);	// sleep retries milliseconds
			if (retries > 5) Logger::getLogger()->info("SQLExec - error :%s: retry %d of %d, rc=%s, DB connection @ %p, slept for %d msecs",
													   sqlite3_errmsg(dbHandle), retries, MAX_RETRIES, (rc==SQLITE_LOCKED)?"SQLITE_LOCKED":"SQLITE_BUSY", this, interval);
		}
	} while (retries < MAX_RETRIES && (rc == SQLITE_LOCKED || rc == SQLITE_BUSY));

	if (rc == SQLITE_LOCKED)
	{
		Logger::getLogger()->error("SQLExec - Database still locked after maximum retries");
	}
	if (rc == SQLITE_BUSY)
	{
		Logger::getLogger()->error("SQLExec - Database still busy after maximum retries");
	}

	return rc;
}


int ReadingsCatalogue::SQLStep(sqlite3_stmt *statement)
{
	int retries = 0, rc;

	do {
		rc = sqlite3_step(statement);
		retries++;
		if (rc == SQLITE_LOCKED || rc == SQLITE_BUSY)
		{
			int interval = (retries * RETRY_BACKOFF);
			usleep(interval);	// sleep retries milliseconds
			if (retries > 5) Logger::getLogger()->info("SQLStep: retry %d of %d, rc=%s, DB connection @ %p, slept for %d msecs",
													   retries, MAX_RETRIES, (rc==SQLITE_LOCKED)?"SQLITE_LOCKED":"SQLITE_BUSY", this, interval);
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

int Connection::SQLPrepare(sqlite3 *dbHandle, const char *sqlCmd, sqlite3_stmt **readingsStmt)
{
	int retries = 0, rc;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	//Logger::getLogger()->debug("SQLPrepare start: cmd :%s: ", sqlCmd);

	do {
		rc = sqlite3_prepare_v2(dbHandle, sqlCmd, -1, readingsStmt, NULL);


		if (rc != SQLITE_OK)
		{
			// FIXME_I:
			Logger::getLogger()->setMinLevel("debug");
			Logger::getLogger()->error("SQLPrepare: rc :%d: dbHandle :%X: sqlCmd :%s: error :%s: ", rc, dbHandle, sqlCmd,  sqlite3_errmsg(dbHandle));
			Logger::getLogger()->setMinLevel("warning");

			retries++;

			int interval = (retries * RETRY_BACKOFF);
			if (retries > 5){
				Logger::getLogger()->info("SQLPrepare: error :%s: retry %d of %d, rc=%d, DB connection @ %p, slept for %d msecs",
										  sqlite3_errmsg(dbHandle), retries, MAX_RETRIES, rc, this, interval);

			}
			usleep(interval);	// sleep retries milliseconds
		}
	} while (retries < MAX_RETRIES && (rc != SQLITE_OK));

	if (rc != SQLITE_OK)
	{
		Logger::getLogger()->error("SQLPrepare - Database error after maximum retries");
	}

	//# FIXME_I
	Logger::getLogger()->setMinLevel("warning");
	//Logger::getLogger()->debug("SQLPrepare end: cmd :%s: ", sqlCmd);

	return rc;
}
