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

#include <string_utils.h>
#include <algorithm>
#include <vector>

#include <readings_catalogue.h>

// 1 enable performance tracking
#define INSTRUMENT	0

#define LOG_AFTER_NERRORS 0

#if INSTRUMENT
#include <sys/time.h>
#endif

// Decode stream data
#define	RDS_USER_TIMESTAMP(stream, x) 	stream[x]->userTs
#define	RDS_ASSET_CODE(stream, x)		stream[x]->assetCode
#define	RDS_PAYLOAD(stream, x)			&(stream[x]->assetCode[0]) + stream[x]->assetCodeLength

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

static time_t connectErrorTime = 0;

// Used to synchronize the shut down of the threads executing appendReadings
static std::atomic<int> m_appendCount(0);
static bool				m_shutdown=false;

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

	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
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


/**
 * Append a set of readings to the readings table
 */
void Connection::setUsedDbId(int dbId) {

	m_NewDbIdList.push_back(dbId);
}

/**
 * Wait until all the threads executing the appendReadings are shutted down
 */
void  Connection::shutdownAppendReadings() {

	ostringstream threadId;
	threadId << std::this_thread::get_id();
	Logger::getLogger()->debug("%s - thread Id :%s: appendReadings shutting down started", __FUNCTION__, threadId.str().c_str());

	m_shutdown=true;

	while (m_appendCount > 0) {

		Logger::getLogger()->debug("%s - thread Id :%s: waiting threads to shut down, count :%d: ", __FUNCTION__, threadId.str().c_str(), int(m_appendCount));
		std::this_thread::sleep_for(std::chrono::milliseconds(150));
	}
	Logger::getLogger()->debug("%s - thread Id :%s: appendReadings shutting down ended", __FUNCTION__, threadId.str().c_str());

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

int stmtArraySize;

	ostringstream threadId;
	threadId << std::this_thread::get_id();

	{
		if (m_shutdown)
		{
			Logger::getLogger()->debug("%s - thread Id :%s: plugin is shutting down, operation cancelled", __FUNCTION__, threadId.str().c_str());
			return -1;
		}

		m_appendCount++;

		Logger::getLogger()->debug("%s - thread Id :%s: operation started , threads count :%d: ", __FUNCTION__,  threadId.str().c_str(), int(m_appendCount) );
	}

	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}

	stmtArraySize = readCatalogue->getReadingPosition(0, 0);
	vector<sqlite3_stmt *> readingsStmt(stmtArraySize + 1, nullptr);

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
		m_appendCount--;
		return -1;
	}

	if (!doc.HasMember("readings"))
	{
 		raiseError("appendReadings", "Payload is missing a readings array");
		m_appendCount--;
		return -1;
	}
	Value &readingsValue = doc["readings"];
	if (!readingsValue.IsArray())
	{
		raiseError("appendReadings", "Payload is missing the readings array");
		m_appendCount--;
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
			m_appendCount--;
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
				ReadingsCatalogue::tyReadingReference ref;

				ref = readCatalogue->getReadingReference(this, asset_code);
				readingsId = ref.tableId;

				Logger::getLogger()->debug("tyReadingReference :%s: :%d: :%d: ", asset_code, ref.dbId, ref.tableId);

				if (readingsId == -1)
				{
					Logger::getLogger()->warn("appendReadings - It was not possible to insert the row for the asset_code :%s: into the readings, row ignored.", asset_code);
					stmt = NULL;
				}
				else
				{
					int nReadings, idxReadings;

					nReadings = readCatalogue->getReadingsCount();
					idxReadings = readCatalogue->getReadingPosition(ref.dbId, ref.tableId);

					Logger::getLogger()->debug("tyReadingReference :%s: :%d: :%d: idxReadings :%d:", asset_code, ref.dbId, ref.tableId, idxReadings);

					if (idxReadings >= stmtArraySize)
					{
						stmtArraySize = idxReadings + 1;
						readingsStmt.resize(stmtArraySize, nullptr);

						Logger::getLogger()->debug("appendReadings: thread :%s: resize size :%d: idx :%d: ", threadId.str().c_str(), stmtArraySize, readingsId);
					}

					if (readingsStmt[idxReadings] == nullptr)
					{
						string dbName = readCatalogue->generateDbName(ref.dbId);
						string dbReadingsName = readCatalogue->generateReadingsName(ref.dbId, readingsId);

						sql_cmd = "INSERT INTO  " + dbName + "." + dbReadingsName + " ( id, user_ts, reading ) VALUES  (?,?,?)";
						rc = SQLPrepare(dbHandle, sql_cmd.c_str(), &readingsStmt[idxReadings]);

						Logger::getLogger()->debug("tyReadingReference sql_cmd  :%s: :%s: :%d: :%d: ", sql_cmd.c_str(), asset_code, ref.dbId, ref.tableId);

						if (rc != SQLITE_OK)
						{
							raiseError("appendReadings", sqlite3_errmsg(dbHandle));
						}
					}
					stmt = readingsStmt[idxReadings];

					lastAsset = asset_code;
				}
			}

			// Handles - reading
			StringBuffer buffer;
			Writer<StringBuffer> writer(buffer);
			(*itr)["reading"].Accept(writer);
			reading = escape(buffer.GetString());

			if(stmt != NULL) {

				sqlite3_bind_int (stmt, 1, readCatalogue->getIncGlobalId());
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

					if(sqlite3_resut != SQLITE_DONE)
					{
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

						sleep_time_ms = PREP_CMD_RETRY_BASE + (random() %  PREP_CMD_RETRY_BACKOFF);
						retries++;

						if (retries >= LOG_AFTER_NERRORS){
							Logger::getLogger()->warn("appendReadings - %s - asset_code :%s: readingsId :%d: thread :%s: dbHandle :%X: record :%d: retry number :%d: sleep time ms :%d:error :%s:",
													  msgError.c_str(),
													  asset_code,
													  readingsId,
													  threadId.str().c_str() ,
													  dbHandle,
													  row,
													  retries,
													  sleep_time_ms,
													  sqlite3_errmsg(dbHandle));
						}


						std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time_ms));
					}
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
					m_appendCount--;
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

	m_appendCount--;

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
unsigned int minGlobalId;
unsigned int idWindow;
unsigned long rowsCount;

	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}

	if (id == 1)
	{
		// at the first extract, Verifies if there are data having id above the current searched window
		minGlobalId = readCatalogue->getMinGlobalId(this->getDbHandle());
		idWindow = id + blksize;

		if (idWindow < minGlobalId)
		{
			id = minGlobalId;
			Logger::getLogger()->debug("%s - first extraction, data extracted from the id :%lu:", __FUNCTION__, id);
		}
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
	rc = sqlite3_prepare_v2(dbHandle, sql_cmd.c_str(),-1,&stmt,NULL);
	if (rc != SQLITE_OK)
	{
		raiseError("retrieve", sqlite3_errmsg(dbHandle));

		// Failure
		return false;
	}
	else
	{
		// Call result set mapping
		rc = mapResultSet(stmt, resultSet, &rowsCount);

		if (rowsCount == 0)
		{
			// If no data were processed, it verifies if there are data having id above the current searched window
			minGlobalId = readCatalogue->getMinGlobalId(this->getDbHandle());
			idWindow = id + blksize;

			if (idWindow < minGlobalId)
			{
				id = minGlobalId;

				// Delete result set
				sqlite3_finalize(stmt);

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
				// Prepare the SQL statement and get the result set
				rc = sqlite3_prepare_v2(dbHandle, sql_cmd.c_str(),-1,&stmt,NULL);
				if (rc != SQLITE_OK)
				{
					raiseError("retrieve", sqlite3_errmsg(dbHandle));

					// Failure
					return false;
				}
				// Call result set mapping
				rc = mapResultSet(stmt, resultSet ,&rowsCount);

				if (rowsCount != 0)
				{
					Logger::getLogger()->debug("%s - following extractions, data extracted from the id :%lu:", __FUNCTION__, id);
				}
			}
		}

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

	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
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

	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
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
		unsigned long r;
		if (flags & 0x01) {

			r = min(sent, rowidLimit);
		} else {
			r = rowidLimit;
		}

		r = max(r, l);
		logger->debug ("s:%d: l=%u, r=%u, sent=%u, rowidLimit=%u, minrowidLimit=%u, flags=%u", __FUNCTION__, __LINE__, l, r, sent, rowidLimit, minrowidLimit, flags);
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


			delete[] query;

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

			Logger::getLogger()->debug("%s - rowidLimit :%lu: minrowidLimit :%lu: midRowId :%lu:", __FUNCTION__, rowidLimit, minrowidLimit, midRowId);
		}

		rowidLimit = m;

		Logger::getLogger()->debug("%s - rowidLimit :%lu: minrowidLimit :%lu: maxrowidLimit :%lu:", __FUNCTION__, rowidLimit, minrowidLimit, maxrowidLimit);


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
	unsigned long rowsAffected;
	unsigned int totTime=0, prevBlocks=0, prevTotTime=0;
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

	Logger::getLogger()->debug("%s - age :%lu: flag :%x: sent :%lu: result :%s:", __FUNCTION__, age, flags, sent, result.c_str() );

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

	// rowidCallback expects unsigned long
	unsigned long rowcount, minId, maxId;
	unsigned long rowsAffected;
	unsigned long  deletePoint;
	char *zErrMsg = NULL;
	int rc;

	Logger *logger = Logger::getLogger();

	ostringstream threadId;
	threadId << std::this_thread::get_id();
	ReadingsCatalogue *readCatalogue = ReadingsCatalogue::getInstance();

	{
		// Attaches the needed databases if the queue is not empty
		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();

		if ( ! m_NewDbIdList.empty())
		{
			readCatalogue->connectionAttachDbList(this->getDbHandle(), m_NewDbIdList);
		}
		attachSync->unlock();
	}

	logger->info("Purge by Rows called");
	if ((flags & 0x01) == 0x01)
	{
		limit = sent;
		logger->info("Sent is %lu", sent);
	}
	logger->info("Purge by Rows called with flags %x, rows %lu, limit %lu", flags, rows, limit);

	rowsAffected = 0;
	// Don't save unsent rows


	{ // Calc rowcount
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
	}

	{ // Calc maxId
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
					 &maxId,
					 &zErrMsg);

		if (rc != SQLITE_OK)
		{
			raiseError("purge - phaase 0, fetching maximum id", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
	}

	numReadings = rowcount;
	rowsAffected = 0;
	do
	{
		if (rowcount <= rows)
		{
			logger->info("Row count %d is less than required rows %d", rowcount, rows);
			break;
		}

		{ // Calc minId
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
						 &minId,
						 &zErrMsg);

			if (rc != SQLITE_OK)
			{
				raiseError("purge - phaase 0, fetching minimum id", zErrMsg);
				sqlite3_free(zErrMsg);
				return 0;
			}
		}
		unsigned long deletePoint = minId + 10000;

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

		sql.append("DELETE FROM  _dbname_._tablename_ WHERE id <= ");
		sql.append(deletePoint);
		const char *query = sql.coalesce();

		{
			ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();

			//unique_lock<mutex> lck(db_mutex);
//			if (m_writeAccessOngoing) db_cv.wait(lck);

			// Exec DELETE query: no callback, no resultset
			rc = readCat->purgeAllReadings(dbHandle, query ,&zErrMsg, &rowsAffected);

			deletedRows += rowsAffected;
			numReadings -= rowsAffected;
			rowcount    -= rowsAffected;

			// Release memory for 'query' var
			delete[] query;
			logger->debug("Deleted :%lu: rows", rowsAffected);
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

	Logger::getLogger()->debug("%s - rows :%lu: flag :%x: sent :%lu:  numReadings :%lu:  rowsAffected :%u:  result :%s:", __FUNCTION__, rows, flags, sent, numReadings, rowsAffected, result.c_str() );

	return deletedRows;
}
#endif

/**
 * SQLIte wrapper to retry statements when the database error occurs
 *
 */
int Connection::SQLPrepare(sqlite3 *dbHandle, const char *sqlCmd, sqlite3_stmt **readingsStmt)
{
	int retries = 0, rc;

	do {
		rc = sqlite3_prepare_v2(dbHandle, sqlCmd, -1, readingsStmt, NULL);


		if (rc != SQLITE_OK)
		{

			if (retries >= LOG_AFTER_NERRORS){
				Logger::getLogger()->warn("SQLPrepare - error :%s: dbHandle :%X: sqlCmd :%s: retry :%d: of :%d:",
										  sqlite3_errmsg(dbHandle),
										  dbHandle,
										  sqlCmd,
										  rc,
										  MAX_RETRIES);

			}

			retries++;
			int interval = (retries * RETRY_BACKOFF);
			usleep(interval);	// sleep retries milliseconds
		}
	} while (retries < MAX_RETRIES && (rc != SQLITE_OK));

	if (rc != SQLITE_OK)
	{
		Logger::getLogger()->error("SQLPrepare - Database error after maximum retries");
	}

	return rc;
}
