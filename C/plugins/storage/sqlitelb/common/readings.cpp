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
#include <sqlite_common.h>
#include <reading_stream.h>
#include <random>

// 1 enable performance tracking
#define INSTRUMENT	0

#if INSTRUMENT
#include <sys/time.h>
#endif

/*
 * The number of readings to insert in a single prepared statement
 */
#define APPEND_BATCH_SIZE	100

/*
 * JSON parsing requires a lot of mempry allocation, which is slow and causes
 * bottlenecks with thread synchronisation. RapidJSON supports in-situ parsing
 * whereby it will reuse the storage of the string it is parsing to store the
 * keys and string values of the parsed JSON. This is destructive on the buffer.
 * However it can be quicker to maek a copy of the raw string and then do in-situ
 * parsing on that copy of the string.
 * See http://rapidjson.org/md_doc_dom.html#InSituParsing
 *
 * Define a threshold length for the append readings to switch to using in-situ
 * parsing of the JSON to save on memory allocation overheads. Define as 0 to
 * disable the in-situ parsing.
 */
#define INSITU_THRESHOLD	10240

// Decode stream data
#define	RDS_USER_TIMESTAMP(stream, x) 		stream[x]->userTs
#define	RDS_ASSET_CODE(stream, x)		stream[x]->assetCode
#define	RDS_PAYLOAD(stream, x)			&(stream[x]->assetCode[0]) + stream[x]->assetCodeLength

// Retry mechanism
#define PREP_CMD_MAX_RETRIES		100	// Maximum no. of retries when a lock is encountered
#define PREP_CMD_RETRY_BASE 		20	// Base time to wait for
#define PREP_CMD_RETRY_BACKOFF		20 	// Variable time to wait for

/*
 * Control the way purge deletes readings. The block size sets a limit as to how many rows
 * get deleted in each call, whilst the sleep interval controls how long the thread sleeps
 * between deletes. The idea is to not keep the database locked too long and allow other threads
 * to have access to the database between blocks.
 */
#define PURGE_SLEEP_MS 500
#define PURGE_DELETE_BLOCK_SIZE	20
#define TARGET_PURGE_BLOCK_DEL_TIME	(70*1000) 	// 70 msec
#define PURGE_BLOCK_SZ_GRANULARITY	5 	// 5 rows
#define MIN_PURGE_DELETE_BLOCK_SIZE	20
#define MAX_PURGE_DELETE_BLOCK_SIZE	1500
#define RECALC_PURGE_BLOCK_SIZE_NUM_BLOCKS	30	// recalculate purge block size after every 30 blocks

#define PURGE_SLOWDOWN_AFTER_BLOCKS 5
#define PURGE_SLOWDOWN_SLEEP_MS 500

#define SECONDS_PER_DAY "86400.0"
// 2440587.5 is the julian day at 1/1/1970 0:00 UTC.
#define JULIAN_DAY_START_UNIXTIME "2440587.5"

//#ifndef PLUGIN_LOG_NAME
//#define PLUGIN_LOG_NAME "SQLite 3"
//#endif

/**
 * SQLite3 storage plugin for Fledge
 */

using namespace std;
using namespace rapidjson;

#define CONNECT_ERROR_THRESHOLD		5*60	// 5 minutes


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

#define START_TIME std::chrono::high_resolution_clock::time_point t1 = std::chrono::high_resolution_clock::now();
#define END_TIME std::chrono::high_resolution_clock::time_point t2 = std::chrono::high_resolution_clock::now(); \
				 auto usecs = std::chrono::duration_cast<std::chrono::microseconds>( t2 - t1 ).count();

static time_t connectErrorTime = 0;


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
	sql.append("json_each.key AS x, json_each.value AS theval FROM " READINGS_DB_NAME_BASE ".readings, json_each(readings.reading) ");

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

/**
 * Append a stream of readings to SQLite db
 *
 * @param readings  readings to store into the SQLite db
 * @param commit    if true a database commit is executed and a new transaction will be opened at the next execution
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
	sqlite3_stmt *stmt, *batch_stmt;
	int sqlite3_resut;
	int rowNumber = -1;
	
#if INSTRUMENT
	struct timeval start, t1, t2, t3, t4, t5;
#endif

	const char *sql_cmd = "INSERT INTO  " READINGS_DB_NAME_BASE ".readings ( user_ts, asset_code, reading ) VALUES  (?,?,?)";
	string cmd = sql_cmd;
	for (int i = 0; i < APPEND_BATCH_SIZE - 1; i++)
	{
		cmd.append(", (?,?,?)");
	}

	sqlite3_prepare_v2(dbHandle, sql_cmd, strlen(sql_cmd), &stmt, NULL);
	sqlite3_prepare_v2(dbHandle, cmd.c_str(), cmd.length(), &batch_stmt, NULL);

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

	int nReadings;
	for (nReadings = 0; readings[nReadings]; nReadings++);

	try
	{
		
		unsigned int nBatches = nReadings / APPEND_BATCH_SIZE;
		int curReading = 0;
	       	for (int batch = 0; batch < nBatches; batch++)
		{
			int varNo = 1;
			for (int readingNo = 0; readingNo < APPEND_BATCH_SIZE; readingNo++)
			{
				add_row = true;

				// Handles - asset_code
				asset_code = RDS_ASSET_CODE(readings, curReading);

				// Handles - reading
				payload = RDS_PAYLOAD(readings, curReading);
				reading = escape(payload);

				// Handles - user_ts
				memset(&timeinfo, 0, sizeof(struct tm));
				gmtime_r(&RDS_USER_TIMESTAMP(readings, curReading).tv_sec, &timeinfo);
				std::strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", &timeinfo);
				snprintf(micro_s, sizeof(micro_s), ".%06lu", RDS_USER_TIMESTAMP(readings, curReading).tv_usec);

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
						raiseError("streamReadings", "Invalid date |%s|", user_ts);
						add_row = false;
					}
					else
					{
						user_ts = formatted_date;
					}
				}

				if (add_row)
				{
					if (batch_stmt != NULL)
					{
						sqlite3_bind_text(batch_stmt, varNo++, user_ts,         -1, SQLITE_STATIC);
						sqlite3_bind_text(batch_stmt, varNo++, asset_code,      -1, SQLITE_STATIC);
						sqlite3_bind_text(batch_stmt, varNo++, reading.c_str(), -1, SQLITE_STATIC);
					}
				}
				curReading++;
			}
			// Write the batch

			retries = 0;
			sleep_time_ms = 0;

			// Retry mechanism in case SQLlite DB is locked
			do {
				// Insert the row using a lock to ensure one insert at time
				{
					m_writeAccessOngoing.fetch_add(1);
					//unique_lock<mutex> lck(db_mutex);

					sqlite3_resut = sqlite3_step(batch_stmt);

					m_writeAccessOngoing.fetch_sub(1);
					//db_cv.notify_all();
				}

				if (sqlite3_resut == SQLITE_LOCKED  )
				{
					sleep_time_ms = PREP_CMD_RETRY_BASE + ((retries / 2 ) * (random() %  PREP_CMD_RETRY_BACKOFF));
					retries++;

					Logger::getLogger()->info("SQLITE_LOCKED - record :%d: - retry number :%d: sleep time ms :%d:",i, retries, sleep_time_ms);

					std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
				}
				if (sqlite3_resut == SQLITE_BUSY)
				{
					ostringstream threadId;
					threadId << std::this_thread::get_id();

					sleep_time_ms = PREP_CMD_RETRY_BASE + ((retries / 2 ) * (random() %  PREP_CMD_RETRY_BACKOFF));
					retries++;

					Logger::getLogger()->info("SQLITE_BUSY - thread :%s: - record :%d: - retry number :%d: sleep time ms :%d:", threadId.str().c_str() ,i , retries, sleep_time_ms);

					std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
				}
			} while (retries < PREP_CMD_MAX_RETRIES && (sqlite3_resut == SQLITE_LOCKED || sqlite3_resut == SQLITE_BUSY));

			if (sqlite3_resut == SQLITE_DONE)
			{
				rowNumber++;

				sqlite3_clear_bindings(batch_stmt);
				sqlite3_reset(batch_stmt);
			}
			else
			{
				raiseError("streamReadings",
						   "Inserting a row into SQLite using a prepared command - asset_code :%s: error :%s: reading :%s: ",
						   asset_code,
						   sqlite3_errmsg(dbHandle),
						   reading.c_str());

				sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION", NULL, NULL, NULL);
				m_streamOpenTransaction = true;
				return -1;
			}
		}

		while (readings[curReading])
		{
			add_row = true;

			// Handles - asset_code
			asset_code = RDS_ASSET_CODE(readings, curReading);

			// Handles - reading
			payload = RDS_PAYLOAD(readings, curReading);
			reading = escape(payload);

			// Handles - user_ts
			memset(&timeinfo, 0, sizeof(struct tm));
			gmtime_r(&RDS_USER_TIMESTAMP(readings, curReading).tv_sec, &timeinfo);
			std::strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", &timeinfo);
			snprintf(micro_s, sizeof(micro_s), ".%06lu", RDS_USER_TIMESTAMP(readings, curReading).tv_usec);

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
					raiseError("streamReadings", "Invalid date |%s|", user_ts);
					add_row = false;
				}
				else
				{
					user_ts = formatted_date;
				}
			}

			if (add_row)
			{
				if (batch_stmt != NULL)
				{
					sqlite3_bind_text(stmt, 1, user_ts,         -1, SQLITE_STATIC);
					sqlite3_bind_text(stmt, 2, asset_code,      -1, SQLITE_STATIC);
					sqlite3_bind_text(stmt, 3, reading.c_str(), -1, SQLITE_STATIC);
				}
			}
			curReading++;


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
					sleep_time_ms = PREP_CMD_RETRY_BASE + ((retries / 2 ) * (random() %  PREP_CMD_RETRY_BACKOFF));
					retries++;

					Logger::getLogger()->info("SQLITE_LOCKED - record :%d: - retry number :%d: sleep time ms :%d:",i, retries, sleep_time_ms);

					std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
				}
				if (sqlite3_resut == SQLITE_BUSY)
				{
					ostringstream threadId;
					threadId << std::this_thread::get_id();

					sleep_time_ms = PREP_CMD_RETRY_BASE + ((retries / 2 ) * (random() %  PREP_CMD_RETRY_BACKOFF));
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
				raiseError("streamReadings",
						   "Inserting a row into SQLite using a prepared command - asset_code :%s: error :%s: reading :%s: ",
						   asset_code,
						   sqlite3_errmsg(dbHandle),
						   reading.c_str());

				sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION", NULL, NULL, NULL);
				m_streamOpenTransaction = true;
				return -1;
			}
		}
		rowNumber = curReading;
	} catch (exception e) {

		raiseError("appendReadings", "Inserting a row into SQLite using a prepared statement  - error :%s:", e.what());

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
	if(batch_stmt != NULL)
	{
		if (sqlite3_finalize(batch_stmt) != SQLITE_OK)
		{
			raiseError("appendReadings","freeing SQLite in memory batch structure - error :%s:", sqlite3_errmsg(dbHandle));
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


	Logger::getLogger()->warn("readingStream Timing with %d rows - stream handling %.3f seconds - commit/finalize %.3f seconds",
				rowNumber, timeT1, timeT2);
#endif

	return rowNumber;
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
sqlite3_stmt *stmt, *batch_stmt;
int           sqlite3_resut;
string        now;

// Retry mechanism
int retries = 0;
int sleep_time_ms = 0;

	ostringstream threadId;
	threadId << std::this_thread::get_id();

#if INSTRUMENT
	Logger::getLogger()->warn("appendReadings start thread :%s:", threadId.str().c_str());

	struct timeval	start, t1, t2, t3, t4, t5;
#endif

#if INSTRUMENT
	gettimeofday(&start, NULL);
#endif

	int len = strlen(readings) + 1;
	char *readingsCopy = NULL;
	ParseResult ok;
#if INSITU_THRESHOLD
	if (len > INSITU_THRESHOLD)
	{
		readingsCopy = (char *)malloc(len);
		memcpy(readingsCopy, readings, len);
		ok = doc.ParseInsitu(readingsCopy);
	}
	else
#endif
	{
		ok = doc.Parse(readings);
	}
	if (!ok)
	{
 		raiseError("appendReadings", GetParseError_En(doc.GetParseError()));
		if (readingsCopy)
		{
			free(readingsCopy);
		}
		return -1;
	}

	if (!doc.HasMember("readings"))
	{
 		raiseError("appendReadings", "Payload is missing a readings array");
		if (readingsCopy)
		{
			free(readingsCopy);
		}
		return -1;
	}
	Value &readingsValue = doc["readings"];
	if (!readingsValue.IsArray())
	{
		raiseError("appendReadings", "Payload is missing the readings array");
		if (readingsCopy)
		{
			free(readingsCopy);
		}
		return -1;
	}

	const char *sql_cmd="INSERT INTO  " READINGS_DB_NAME_BASE ".readings ( user_ts, asset_code, reading ) VALUES  (?,?,?)";
	string cmd = sql_cmd;
	for (int i = 0; i < APPEND_BATCH_SIZE - 1; i++)
	{
		cmd.append(", (?,?,?)");
	}

	sqlite3_prepare_v2(dbHandle, sql_cmd, strlen(sql_cmd), &stmt, NULL);
	sqlite3_prepare_v2(dbHandle, cmd.c_str(), cmd.length(), &batch_stmt, NULL);
	{
	m_writeAccessOngoing.fetch_add(1);
	//unique_lock<mutex> lck(db_mutex);
	sqlite3_exec(dbHandle, "BEGIN TRANSACTION", NULL, NULL, NULL);

#if INSTRUMENT
	gettimeofday(&t1, NULL);
#endif

	Value::ConstValueIterator itr = readingsValue.Begin();
	SizeType nReadings = readingsValue.Size();
	unsigned int nBatches = nReadings / APPEND_BATCH_SIZE;
	Logger::getLogger()->debug("Write %d readings in %d batches of %d", nReadings, nBatches, APPEND_BATCH_SIZE);
       	for (int batch = 0; batch < nBatches; batch++)
	{
		int varNo = 1;
		for (int readingNo = 0; readingNo < APPEND_BATCH_SIZE; readingNo++)
		{
			if (!itr->IsObject())
			{
				char err[132];
				snprintf(err, sizeof(err),
						"Each reading in the readings array must be an object. Reading %d of batch %d", readingNo, batch);
				raiseError("appendReadings",err);
				sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION;", NULL, NULL, NULL);
				if (readingsCopy)
				{
					free(readingsCopy);
				}
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

				if (strlen(asset_code) == 0)
				{
					Logger::getLogger()->warn("Sqlitelb appendReadings - empty asset code value, row is ignored");
					itr++;
					continue;
				}
				// Handles - reading
				StringBuffer buffer;
				Writer<StringBuffer> writer(buffer);
				(*itr)["reading"].Accept(writer);
				reading = escape(buffer.GetString());

				if (stmt != NULL)
				{

					sqlite3_bind_text(batch_stmt, varNo++, user_ts, -1, SQLITE_TRANSIENT);
					sqlite3_bind_text(batch_stmt, varNo++, asset_code, -1, SQLITE_TRANSIENT);
					sqlite3_bind_text(batch_stmt, varNo++, reading.c_str(), -1, SQLITE_TRANSIENT);
				}
			}

			itr++;
			if (itr == readingsValue.End())
				break;
		}


		retries =0;
		sleep_time_ms = 0;

		// Retry mechanism in case SQLlite DB is locked
		do {
			// Insert the row using a lock to ensure one insert at time
			{

				sqlite3_resut = sqlite3_step(batch_stmt);

			}
			if (sqlite3_resut == SQLITE_LOCKED  )
			{
				sleep_time_ms = PREP_CMD_RETRY_BASE + ((retries / 2 ) * (random() %  PREP_CMD_RETRY_BACKOFF));
				retries++;

				Logger::getLogger()->info("SQLITE_LOCKED - record :%d: - retry number :%d: sleep time ms :%d:" ,row ,retries ,sleep_time_ms);

				std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
			}
			if (sqlite3_resut == SQLITE_BUSY)
			{
				ostringstream threadId;
				threadId << std::this_thread::get_id();

				sleep_time_ms = PREP_CMD_RETRY_BASE + ((retries / 2 ) * (random() %  PREP_CMD_RETRY_BACKOFF));
				retries++;

				Logger::getLogger()->info("SQLITE_BUSY - thread :%s: - record :%d: - retry number :%d: sleep time ms :%d:", threadId.str().c_str() ,row, retries, sleep_time_ms);

				std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
			}
		} while (retries < PREP_CMD_MAX_RETRIES && (sqlite3_resut == SQLITE_LOCKED || sqlite3_resut == SQLITE_BUSY));

		if (sqlite3_resut == SQLITE_DONE)
		{
			row += APPEND_BATCH_SIZE;

			sqlite3_clear_bindings(batch_stmt);
			sqlite3_reset(batch_stmt);
		}
		else
		{
			raiseError("appendReadings","Inserting a row into SQLite using a prepared command - asset_code :%s: error :%s: reading :%s: ",
				asset_code,
				sqlite3_errmsg(dbHandle),
				reading.c_str());

			sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION", NULL, NULL, NULL);
			if (readingsCopy)
			{
				free(readingsCopy);
			}
			return -1;
		}


	}

	Logger::getLogger()->debug("Now do the remaining readings");
	// Do individual inserts for the remainder of the readings
	while (itr != readingsValue.End())
	{
		if (!itr->IsObject())
		{
			raiseError("appendReadings","Each reading in the readings array must be an object");
			sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION;", NULL, NULL, NULL);
			if (readingsCopy)
			{
				free(readingsCopy);
			}
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

			if (strlen(asset_code) == 0)
			{
				Logger::getLogger()->warn("Sqlitelb appendReadings - empty asset code value, row is ignored");
				itr++;
				continue;
			}

			// Handles - reading
			StringBuffer buffer;
			Writer<StringBuffer> writer(buffer);
			(*itr)["reading"].Accept(writer);
			reading = escape(buffer.GetString());

			if(stmt != NULL) {

				sqlite3_bind_text(stmt, 1, user_ts         ,-1, SQLITE_TRANSIENT);
				sqlite3_bind_text(stmt, 2, asset_code      ,-1, SQLITE_TRANSIENT);
				sqlite3_bind_text(stmt, 3, reading.c_str(), -1, SQLITE_TRANSIENT);

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
						sleep_time_ms = PREP_CMD_RETRY_BASE + ((retries / 2 ) * (random() %  PREP_CMD_RETRY_BACKOFF));
						retries++;

						Logger::getLogger()->info("SQLITE_LOCKED - record :%d: - retry number :%d: sleep time ms :%d:" ,row ,retries ,sleep_time_ms);

						std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
					}
					if (sqlite3_resut == SQLITE_BUSY)
					{
						ostringstream threadId;
						threadId << std::this_thread::get_id();

						sleep_time_ms = PREP_CMD_RETRY_BASE + ((retries / 2 ) * (random() %  PREP_CMD_RETRY_BACKOFF));
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
					raiseError("appendReadings","Inserting a row into SQLite using a prepared command - asset_code :%s: error :%s: reading :%s: ",
						asset_code,
						sqlite3_errmsg(dbHandle),
						reading.c_str());

					sqlite3_exec(dbHandle, "ROLLBACK TRANSACTION", NULL, NULL, NULL);
					if (readingsCopy)
					{
						free(readingsCopy);
					}
					return -1;
				}
			}
		}
		itr++;
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
	if(batch_stmt != NULL)
	{
		if (sqlite3_finalize(batch_stmt) != SQLITE_OK)
		{
			raiseError("appendReadings","freeing SQLite in memory batch structure - error :%s:", sqlite3_errmsg(dbHandle));
		}
	}

	if (readingsCopy)
	{
		free(readingsCopy);
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

		Logger::getLogger()->warn("appendReadings end   thread :%s: buffer :%10lu: count :%5d: JSON :%6.3f: inserts :%6.3f: finalize :%6.3f:",
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
	FROM  )" READINGS_DB_NAME_BASE R"(.readings
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
 * Perform a query against the readings table
 *
 * retrieveReadings, used by the API, returns timestamp in utc unless
 * otherwise requested.
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
const char	*timezone = "utc";
vector<string>  asset_codes;

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
						strftime(')" F_DATEH24_SEC R"(', user_ts, 'utc')  ||
						substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
						strftime(')" F_DATEH24_MS R"(', ts, 'localtime') AS ts
					FROM )" READINGS_DB_NAME_BASE R"(.readings)";

			sql.append(sql_cmd);
		}
		else
		{
			if (document.Parse(condition.c_str()).HasParseError())
			{
				raiseError("retrieve", "Failed to parse JSON payload");
				return false;
			}

			if (document.HasMember("timezone") && document["timezone"].IsString())
			{
				timezone = document["timezone"].GetString();
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
				sql.append(" FROM  " READINGS_DB_NAME_BASE ".");
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
							sql.append(" strftime('" F_DATEH24_SEC "', user_ts, '");
							sql.append(timezone);
							sql.append("') ");
							sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
							sql.append(" as  user_ts ");
						}
						else if (strcmp(itr->GetString() ,"ts") == 0)
						{
							// Display without TZ expression and microseconds also
							sql.append(" strftime('" F_DATEH24_MS "', ts, '");
							sql.append(timezone);
							sql.append("') ");
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

									sql.append("strftime('" F_DATEH24_SEC "', user_ts, '");
									sql.append(timezone);
									sql.append("') ");
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
									sql.append(", '");
									sql.append(timezone);
									sql.append("')");
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
				sql.append(" FROM  " READINGS_DB_NAME_BASE ".");
			}
			else
			{
				sql.append("SELECT ");
				if (document.HasMember("modifier"))
				{
					sql.append(document["modifier"].GetString());
					sql.append(' ');
				}

				sql.append("id, asset_code, reading, strftime('" F_DATEH24_SEC "', user_ts, '");
				sql.append(timezone);
				sql.append("')  || substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,");
				sql.append("strftime('" F_DATEH24_MS "', ts, '");
				sql.append(timezone);
				sql.append("') AS ts FROM " READINGS_DB_NAME_BASE ".");

			}
			sql.append("readings");
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
	bool flag_retain;

	Logger *logger = Logger::getLogger();

	flag_retain = false;

	if ( (flags & STORAGE_PURGE_RETAIN_ANY) || (flags & STORAGE_PURGE_RETAIN_ALL) )
	{
		flag_retain = true;
	}
	Logger::getLogger()->debug("%s - flags :%X: flag_retain :%d: sent :%ld:", __FUNCTION__, flags, flag_retain, sent);

	// Prepare empty result
	result = "{ \"removed\" : 0, ";
	result += " \"unsentPurged\" : 0, ";
	result += " \"unsentRetained\" : 0, ";
	result += " \"readings\" : 0, ";
	result += " \"method\" : \"time\", ";
	result += " \"duration\" : 0 }";

	logger->info("Purge starting...");
	gettimeofday(&startTv, NULL);
	/*
	 * We fetch the current rowid and limit the purge process to work on just
	 * those rows present in the database when the purge process started.
	 * This prevents us looping in the purge process if new readings become
	 * eligible for purging at a rate that is faster than we can purge them.
	 */
	{
		char *zErrMsg = NULL;
		int rc;
		rc = SQLexec(dbHandle, "readings",
					 "select max(rowid) from " READINGS_DB_NAME_BASE "."  READINGS_TABLE ";",
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
		rc = SQLexec(dbHandle, "readings",
					 "select min(rowid) from " READINGS_DB_NAME_BASE "." READINGS_TABLE ";",
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
		oldest.append("SELECT (strftime('%s','now', 'utc') - strftime('%s', MIN(user_ts)))/360 FROM " READINGS_DB_NAME_BASE "." READINGS_TABLE " where rowid <= ");
		oldest.append(rowidLimit);
		oldest.append(';');
		const char *query = oldest.coalesce();
		char *zErrMsg = NULL;
		int rc;
		int purge_readings = 0;

		// Exec query and get result in 'purge_readings' via 'selectCallback'
		rc = SQLexec(dbHandle, "readings",
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
		if (flag_retain) {

			r = min(sent, rowidLimit);
		} else {
			r = rowidLimit;
		}

		r = max(r, l);
		logger->debug   ("%s:%d: l=%u, r=%u, sent=%u, rowidLimit=%u, minrowidLimit=%u, flags=%u", __FUNCTION__, __LINE__, l, r, sent, rowidLimit, minrowidLimit, flags);

		if (l == r)
		{
			logger->info("No data to purge: min_id == max_id == %u", minrowidLimit);
			return 0;
		}

		unsigned long m=l;
		sqlite3_stmt *idStmt;
		bool isMinId = false;
		while (l <= r)
		{
			unsigned long midRowId = 0;
			unsigned long prev_m = m;
			m = l + (r - l) / 2;
			if (prev_m == m) break;

			// e.g. select id from readings where rowid = 219867307 AND user_ts < datetime('now' , '-24 hours', 'utc');
			SQLBuffer sqlBuffer;
			sqlBuffer.append("select id from " READINGS_DB_NAME_BASE "." READINGS_TABLE " where rowid = ?");
			sqlBuffer.append(" AND user_ts < datetime('now' , '-?");
			sqlBuffer.append(" hours');");
			
			const char *query = sqlBuffer.coalesce();

			rc = sqlite3_prepare_v2(dbHandle, query, -1, &idStmt, NULL);
		
			sqlite3_bind_int(idStmt, 1,(unsigned long) m);
			sqlite3_bind_int(idStmt, 2,(unsigned long) age);

			if (SQLstep(idStmt) == SQLITE_ROW)
			{
				midRowId = sqlite3_column_int(idStmt, 0);
				isMinId = true;
			}
			delete[] query;
			sqlite3_clear_bindings(idStmt);
			sqlite3_reset(idStmt);

			if (rc == SQLITE_ERROR)
			{
				raiseError("purge - phase 1, fetching midRowId ", sqlite3_errmsg(dbHandle));
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

		if(isMinId)
		{
			sqlite3_finalize(idStmt);
		}

		rowidLimit = m;

		{ // Fix the value of rowidLimit

			Logger::getLogger()->debug("%s - s1 rowidLimit :%lu: minrowidLimit :%lu: maxrowidLimit :%lu:", __FUNCTION__, rowidLimit, minrowidLimit, maxrowidLimit);

			SQLBuffer sqlBuffer;
			sqlBuffer.append("select max(id) from " READINGS_DB_NAME_BASE "." READINGS_TABLE " where rowid <= ");
			sqlBuffer.append(rowidLimit);
			sqlBuffer.append(" AND user_ts < datetime('now' , '-");
			sqlBuffer.append(age);
			sqlBuffer.append(" hours');");
			const char *query = sqlBuffer.coalesce();

			rc = SQLexec(dbHandle, "readings",
						 query,
						 rowidCallback,
						 &rowidLimit,
						 &zErrMsg);

			delete[] query;

			if (rc != SQLITE_OK)
			{
				raiseError("purge - phase 1, fetching rowidLimit ", zErrMsg);
				sqlite3_free(zErrMsg);
				return 0;
			}
			Logger::getLogger()->debug("%s - s2 rowidLimit :%lu: minrowidLimit :%lu: maxrowidLimit :%lu:", __FUNCTION__, rowidLimit, minrowidLimit, maxrowidLimit);
		}

		if (minrowidLimit == rowidLimit)
		{
			logger->info("No data to purge");
			return 0;
		}

		rowidMin = minrowidLimit;
	}
	//logger->info("Purge collecting unsent row count");
	if ( ! flag_retain )
	{
		char *zErrMsg = NULL;
		int rc;
		int lastPurgedId;
		SQLBuffer idBuffer;
		idBuffer.append("select id from " READINGS_DB_NAME_BASE "." READINGS_TABLE " where rowid = ");
		idBuffer.append(rowidLimit);
		idBuffer.append(';');
		const char *idQuery = idBuffer.coalesce();
		rc = SQLexec(dbHandle, "readings",
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
#if 0
	if (m_writeAccessOngoing)
	{
		while (m_writeAccessOngoing)
		{
			logger->warn("Yielding for another write access");
			std::this_thread::yield();
		}
	}
#endif

	unsigned int deletedRows = 0;
	unsigned int rowsAffected, totTime=0, prevBlocks=0, prevTotTime=0;
	logger->info("Purge about to delete readings # %ld to %ld", rowidMin, rowidLimit);
	sqlite3_stmt *stmt;
	bool rowsAvailableToPurge = false;
	while (rowidMin < rowidLimit)
	{
		blocks++;
		rowidMin += purgeBlockSize;
		if (rowidMin > rowidLimit)
		{
			rowidMin = rowidLimit;
		}
		
		int rc;
		{
			SQLBuffer sql;
			sql.append("DELETE FROM " READINGS_DB_NAME_BASE "." READINGS_TABLE " WHERE rowid <= ? ;");
			const char *query = sql.coalesce();
			
			rc = sqlite3_prepare_v2(dbHandle, query, strlen(query), &stmt, NULL);
			if (rc != SQLITE_OK)
			{
				raiseError("purgeReadings", sqlite3_errmsg(dbHandle));
				Logger::getLogger()->error("SQL statement: %s", query);
				return 0;
			}
			delete[] query;
		}
		sqlite3_bind_int(stmt, 1,(unsigned long) rowidMin);
		rowsAvailableToPurge = true;
		{
			//unique_lock<mutex> lck(db_mutex);
//		if (m_writeAccessOngoing) db_cv.wait(lck);

			START_TIME;
			// Exec DELETE query: no callback, no resultset
			rc = SQLstep(stmt);

			END_TIME;
			
			logSQL("ReadingsPurge", sqlite3_expanded_sql(stmt));

			logger->debug("%s - DELETE - query :%s: rowsAffected :%ld:",  __FUNCTION__, sqlite3_expanded_sql(stmt) ,rowsAffected);

			totTime += usecs;

			if(usecs>150000)
			{
				std::this_thread::yield();	// Give other threads a chance to run
			}
		}
		if (rc == SQLITE_DONE)
		{
			sqlite3_clear_bindings(stmt);
			sqlite3_reset(stmt);
		}
		else
		{
			raiseError("purge - phase 3", sqlite3_errmsg(dbHandle));
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
			std::this_thread::yield();	// Give other threads a chance to run
		}
		//Logger::getLogger()->debug("Purge delete block #%d with %d readings", blocks, rowsAffected);
	} while (rowidMin  < rowidLimit);
	
	if (rowsAvailableToPurge)
	{
		sqlite3_finalize(stmt);
	}
	
	unsentRetained = maxrowidLimit - rowidLimit;

	numReadings = maxrowidLimit +1 - minrowidLimit - deletedRows;

	if (sent == 0)	// Special case when not north process is used
	{
		unsentPurged = deletedRows;
	}

	gettimeofday(&endTv, NULL);
	unsigned long duration = (1000000 * (endTv.tv_sec - startTv.tv_sec)) + endTv.tv_usec - startTv.tv_usec;

	ostringstream convert;

	convert << "{ \"removed\" : " << deletedRows << ", ";
	convert << " \"unsentPurged\" : " << unsentPurged << ", ";
	convert << " \"unsentRetained\" : " << unsentRetained << ", ";
	convert << " \"readings\" : " << numReadings << ", ";
	convert << " \"method\" : \"time\", ";
	convert << " \"duration\" : " << duration << " }";

	result = convert.str();

	//logger->debug("Purge result=%s", result.c_str());

	logger->info("Purge process complete in %d blocks in %lduS", blocks, duration);

	Logger::getLogger()->debug("%s - age :%lu: flag_retain :%x: sent :%lu: result :%s:", __FUNCTION__, age, flags, flag_retain, result.c_str() );

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
	bool flag_retain;
	struct timeval startTv, endTv;


	Logger *logger = Logger::getLogger();

	gettimeofday(&startTv, NULL);
	flag_retain = false;

	if ( (flags & STORAGE_PURGE_RETAIN_ANY) || (flags & STORAGE_PURGE_RETAIN_ALL) )
	{
		flag_retain = true;
	}
	Logger::getLogger()->debug("%s - flags :%X: flag_retain :%d: sent :%ld:", __FUNCTION__, flags, flag_retain, sent);

	logger->info("Purge by Rows called");
	if (flag_retain)
	{
		limit = sent;
		logger->info("Sent is %lu", sent);
	}
	logger->info("Purge by Rows called with flag_retain %d, rows %lu, limit %lu", flag_retain, rows, limit);
	// Don't save unsent rows

	char *zErrMsg = NULL;
	int rc;
	sqlite3_stmt *stmt;
	sqlite3_stmt *idStmt;
	rc = SQLexec(dbHandle, "readings",
				 "select count(rowid) from " READINGS_DB_NAME_BASE "." READINGS_TABLE ";",
		rowidCallback,
		&rowcount,
		&zErrMsg);

	if (rc != SQLITE_OK)
	{
		raiseError("purge - phaase 0, fetching row count", zErrMsg);
		sqlite3_free(zErrMsg);
		return 0;
	}

	rc = SQLexec(dbHandle, "readings",
				 "select max(id) from " READINGS_DB_NAME_BASE "." READINGS_TABLE ";",
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
	bool rowsAvailableToPurge = true;

	// Create the prepared statements
	SQLBuffer sqlBuffer;
	sqlBuffer.append("select min(id) from " READINGS_DB_NAME_BASE "." READINGS_TABLE ";");
	const char *idquery = sqlBuffer.coalesce();

	rc = sqlite3_prepare_v2(dbHandle, idquery, -1, &idStmt, NULL);
	if (rc != SQLITE_OK)
	{
		raiseError("purgeReadingsByRows", sqlite3_errmsg(dbHandle));
		Logger::getLogger()->error("SQL statement: %s", idquery);
		delete[] idquery;
		return 0;
	}
	delete[] idquery;

	SQLBuffer sql;
	sql.append("delete from " READINGS_DB_NAME_BASE "." READINGS_TABLE "  where id <= ? ;");
	const char *delquery = sql.coalesce();

	rc = sqlite3_prepare_v2(dbHandle, delquery, strlen(delquery), &stmt, NULL);
	
	if (rc != SQLITE_OK)
	{
		raiseError("purgeReadingsByRows", sqlite3_errmsg(dbHandle));
		Logger::getLogger()->error("SQL statement: %s", delquery);
		delete[] delquery;
		return 0;
	}
	delete[] delquery;

	do
	{
		if (rowcount <= rows)
		{
			logger->info("Row count %d is less than required rows %d", rowcount, rows);
			rowsAvailableToPurge = false;
			break;
		}

		if (SQLstep(idStmt) == SQLITE_ROW)
		{
			minId = sqlite3_column_int(idStmt, 0);
		}


		sqlite3_clear_bindings(idStmt);
		sqlite3_reset(idStmt);
		
		if (rc == SQLITE_ERROR)
		{
			raiseError("purge - phaase 0, fetching minimum id", sqlite3_errmsg(dbHandle));
			sqlite3_free(zErrMsg);
			return 0;
		}

		deletePoint = minId + m_purgeBlockSize;
		if (maxId - deletePoint < rows || deletePoint > maxId)
			deletePoint = maxId - rows;

		// Do not delete
		if (flag_retain) {

			if (limit < deletePoint)
			{
				deletePoint = limit;
			}
		}
		
		{
			logger->info("RowCount %lu, Max Id %lu, min Id %lu, delete point %lu", rowcount, maxId, minId, deletePoint);
			
		}
		sqlite3_bind_int(stmt, 1,(unsigned long) deletePoint);

		{
			// Exec DELETE query: no callback, no resultset
			rc = SQLstep(stmt);
			if (rc == SQLITE_DONE)
			{
				sqlite3_clear_bindings(stmt);
				sqlite3_reset(stmt);
			}
			rowsAffected = sqlite3_changes(dbHandle);

			deletedRows += rowsAffected;
			numReadings -= rowsAffected;
			rowcount    -= rowsAffected;

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
		std::this_thread::yield();	// Give other threads a chance to run
	} while (rowcount > rows);

	if (rowsAvailableToPurge)
	{
		sqlite3_finalize(idStmt);
		sqlite3_finalize(stmt);
	}
	

	if (limit)
	{
		unsentRetained = numReadings - rows;
	}

	gettimeofday(&endTv, NULL);
	unsigned long duration = (1000000 * (endTv.tv_sec - startTv.tv_sec)) + endTv.tv_usec - startTv.tv_usec;

	ostringstream convert;

	convert << "{ \"removed\" : " << deletedRows << ", ";
	convert << " \"unsentPurged\" : " << unsentPurged << ", ";
	convert << " \"unsentRetained\" : " << unsentRetained << ", ";
	convert << " \"readings\" : " << numReadings << ", ";
	convert << " \"method\" : \"rows\", ";
	convert << " \"duration\" : " << duration << " }";

	result = convert.str();

	Logger::getLogger()->debug("%s - rows :%lu: flag :%x: sent :%lu: numReadings :%lu:  rowsAffected :%u:  result :%s:", __FUNCTION__, rows, flags, sent, numReadings, rowsAffected, result.c_str() );

	logger->info("Purge by Rows complete: %s", result.c_str());
	return deletedRows;
}

/**
 * Purge readings by asset or purge all readings
 *
 * @param asset		The asset name to purge
 * 			If empty all assets will be removed
 * @return		The number of removed asset records
 */
unsigned int Connection::purgeReadingsAsset(const string& asset)
{
SQLBuffer sql;
unsigned int rowsAffected = 0;
	sql.append("DELETE FROM " READINGS_DB_NAME_BASE "." READINGS_TABLE);
		       
	if (!asset.empty())
	{
		sql.append("  WHERE asset_code = '");
		sql.append(asset);
		sql.append('\'');
	}
	sql.append(';');

	const char *query = sql.coalesce();
	char *zErrMsg = NULL;
	int rc;

	logSQL("ReadingsAssetPurge", query);

#if 0
	if (m_writeAccessOngoing)
	{
		while (m_writeAccessOngoing)
		{
			std::this_thread::yield();
		}
	}
#endif

	START_TIME;
	// Exec DELETE query: no callback, no resultset
	rc = SQLexec(dbHandle, "readings",
			query,
			NULL,
			NULL,
			&zErrMsg);
	END_TIME;

	// Release memory for 'query' var
	delete[] query;

	if (rc != SQLITE_OK)
	{
		raiseError("ReadingsAssetPurge", zErrMsg);
		sqlite3_free(zErrMsg);
		return rowsAffected;
	}

	// Get db changes
	rowsAffected = sqlite3_changes(dbHandle);

	return rowsAffected;
}
