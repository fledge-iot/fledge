#ifndef _CONNECTION_H
#define _CONNECTION_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <sql_buffer.h>
#include <string>
#include <rapidjson/document.h>
#include <sqlite3.h>
#include <mutex>
#include <reading_stream.h>
#include <schema.h>
#include <map>
#include <vector>
#include <atomic>

#define TRACK_CONNECTION_USER		0 // Set to 1 to get dianositcs about connection pool use

#define READINGS_DB_FILE_NAME     "/" READINGS_DB_NAME_BASE "_1.db"
#define READINGS_DB               READINGS_DB_NAME_BASE "_1"
#define READINGS_TABLE            "readings"
#define READINGS_TABLE_MEM       READINGS_TABLE "_1"


// Set plugin name for log messages
#ifndef PLUGIN_LOG_NAME
#define PLUGIN_LOG_NAME "SQLite3"
#endif

// Retry mechanism
#define PREP_CMD_MAX_RETRIES		50	// Maximum no. of retries when a lock is encountered
#define PREP_CMD_RETRY_BASE 		50	// Base time to wait for
#define PREP_CMD_RETRY_BACKOFF		50	// Variable time to wait for

#define MAX_RETRIES			40	// Maximum no. of retries when a lock is encountered
#define RETRY_BACKOFF			50	// Multipler to backoff DB retry on lock

/*
 * Control the way purge deletes readings. The block size sets a limit as to how many rows
 * get deleted in each call, whilst the sleep interval controls how long the thread sleeps
 * between deletes. The idea is to not keep the database locked too long and allow other threads
 * to have access to the database between blocks.
 */
#define PURGE_SLEEP_MS 500

#define PURGE_DELETE_BLOCK_SIZE	    10000
#define MIN_PURGE_DELETE_BLOCK_SIZE	1000
#define MAX_PURGE_DELETE_BLOCK_SIZE	10000

#define TARGET_PURGE_BLOCK_DEL_TIME	(70*1000) 	// 70 msec
#define PURGE_BLOCK_SZ_GRANULARITY	5 	// 5 rows
#define RECALC_PURGE_BLOCK_SIZE_NUM_BLOCKS	30	// recalculate purge block size after every 30 blocks

#define PURGE_SLOWDOWN_AFTER_BLOCKS 5
#define PURGE_SLOWDOWN_SLEEP_MS 500

#define SECONDS_PER_DAY "86400.0"
// 2440587.5 is the julian day at 1/1/1970 0:00 UTC.
#define JULIAN_DAY_START_UNIXTIME "2440587.5"


#define START_TIME std::chrono::high_resolution_clock::time_point t1 = std::chrono::high_resolution_clock::now();
#define END_TIME std::chrono::high_resolution_clock::time_point t2 = std::chrono::high_resolution_clock::now(); \
				 auto usecs = std::chrono::duration_cast<std::chrono::microseconds>( t2 - t1 ).count();


int dateCallback(void *data, int nCols, char **colValues, char **colNames);
bool applyColumnDateFormat(const std::string& inFormat,
			   const std::string& colName,
			   std::string& outFormat,
			   bool roundMs = false);

bool applyColumnDateFormatLocaltime(const std::string& inFormat,
				    const std::string& colName,
				    std::string& outFormat,
				    bool roundMs = false);

int rowidCallback(void *data,
		  int nCols,
		  char **colValues,
		  char **colNames);

int selectCallback(void *data,
		   int nCols,
		   char **colValues,
		   char **colNames);

int countCallback(void *data,
		  int nCols,
		  char **colValues,
		  char **colNames);

bool applyDateFormat(const std::string& inFormat, std::string& outFormat);

class Connection {
	public:
		Connection();
		~Connection();
#ifndef SQLITE_SPLIT_READINGS
		bool		createSchema(const std::string& schema);
		bool		retrieve(const std::string& schema,
					 const std::string& table,
					 const std::string& condition,
					 std::string& resultSet);
		int		insert(const std::string& schema,
					const std::string& table,
					const std::string& data);
		int		update(const std::string& schema,
						const std::string& table,
						const std::string& data);
		int		deleteRows(const std::string& schema,
						const std::string& table,
						const std::string& condition);
		int		create_table_snapshot(const std::string& table, const std::string& id);
		int		load_table_snapshot(const std::string& table, const std::string& id);
		int		delete_table_snapshot(const std::string& table, const std::string& id);
		bool		get_table_snapshots(const std::string& table, std::string& resultSet);
#endif
		int		appendReadings(const char *readings);
		int 		readingStream(ReadingStream **readings, bool commit);
		bool		fetchReadings(unsigned long id, unsigned int blksize,
						std::string& resultSet);
		bool		retrieveReadings(const std::string& condition,
						 std::string& resultSet);
		unsigned int	purgeReadings(unsigned long age, unsigned int flags,
						unsigned long sent, std::string& results);
		unsigned int	purgeReadingsByRows(unsigned long rowcount, unsigned int flags,
						unsigned long sent, std::string& results);
		long		tableSize(const std::string& table);
		void		setTrace(bool);
		bool		formatDate(char *formatted_date, size_t formatted_date_size, const char *date);
		bool		aggregateQuery(const rapidjson::Value& payload, std::string& resultSet);
		bool		getNow(std::string& Now);

		sqlite3		*getDbHandle() {return dbHandle;};
		void		setUsedDbId(int dbId);

		void		shutdownAppendReadings();
		unsigned int	purgeReadingsAsset(const std::string& asset);
		bool		vacuum();
		bool		supportsReadings() { return ! m_noReadings; };
#if TRACK_CONNECTION_USER
		void		setUsage(std::string usage) { m_usage = usage; };
		void		clearUsage() { m_usage = ""; };
		std::string	getUsage() { return m_usage; };
#endif

	private:
		std::string	operation(const char *sql);
		std::vector<int>
		       		m_NewDbIdList;            // Newly created databases that should be attached

		bool		m_streamOpenTransaction;
		int		m_queuing;
		std::mutex	m_qMutex;
		int		SQLPrepare(sqlite3 *dbHandle, const char *sqlCmd, sqlite3_stmt **readingsStmt);
		int		SQLexec(sqlite3 *db, const std::string& table, const char *sql,
				int (*callback)(void*,int,char**,char**),
					void *cbArg, char **errmsg);

		int		SQLstep(sqlite3_stmt *statement);
		bool		m_logSQL;
		void		raiseError(const char *operation, const char *reason,...);
		sqlite3		*dbHandle;
		SchemaManager	*m_schemaManager;
		int		mapResultSet(void *res, std::string& resultSet, unsigned long *rowsCount = nullptr);
#ifndef SQLITE_SPLIT_READINGS
		bool		jsonWhereClause(const rapidjson::Value& whereClause, SQLBuffer&, std::vector<std::string>  &asset_codes, bool convertLocaltime = false, std::string prefix = "");
#else
		bool		jsonWhereClause(const rapidjson::Value& whereClause, SQLBuffer&, bool convertLocaltime = false, std::string prefix = "");
#endif
		bool		jsonModifiers(const rapidjson::Value&, SQLBuffer&, bool isTableReading = false);
#ifndef SQLITE_SPLIT_READINGS
		bool		jsonAggregates(const rapidjson::Value&,
					       const rapidjson::Value&,
					       SQLBuffer&,
					       SQLBuffer&,
					       bool &isOptAggregate,
					       bool isTableReading = false,
					       bool isExtQuery = false
					       );
#else
	bool			jsonAggregates(const rapidjson::Value&,
		                               const rapidjson::Value&,
		                               SQLBuffer&,
		                               SQLBuffer&,
		                               bool isTableReading = false);
#endif
		bool		returnJson(const rapidjson::Value&, SQLBuffer&, SQLBuffer&);
		char		*trim(char *str);
		const std::string
				escape(const std::string&);
		bool		applyColumnDateTimeFormat(sqlite3_stmt *pStmt,
						int i,
						std::string& newDate);
		void		logSQL(const char *, const char *);
		bool		selectColumns(const rapidjson::Value& document, SQLBuffer& sql, int level);
		bool 		appendTables(const std::string& schema, const rapidjson::Value& document, SQLBuffer& sql, int level);
		bool		processJoinQueryWhereClause(const rapidjson::Value& query, SQLBuffer& sql, std::vector<std::string>  &asset_codes, int level);
		bool		m_noReadings;
#if TRACK_CONNECTION_USER
		std::string	m_usage;
#endif
};

#endif
