/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */
#include <connection.h>
#include <connection_manager.h>
#include <sql_buffer.h>
#include <iostream>
#include <sqlite3.h>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/error.h"
#include "rapidjson/error/en.h"
#include <string>
#include <map>
#include <stdarg.h>
#include <stdlib.h>
#include <sstream>
#include <logger.h>
#include <time.h>
#include <unistd.h>
#include <utils.h>
#include <chrono>
#include <thread>
#include <sys/time.h>

/*
 * Control the way purge deletes readings. The block size sets a limit as to how many rows
 * get deleted in each call, whilst the sleep interval controls how long the thread sleeps
 * between deletes. The idea is to not keep the database locked too long and allow other threads
 * to have access to the database between blocks.
 */
#define PURGE_SLEEP_MS 2500
#define PURGE_DELETE_BLOCK_SIZE	1000

/**
 * SQLite3 storage plugin for FogLAMP
 */

using namespace std;
using namespace rapidjson;

#define CONNECT_ERROR_THRESHOLD		5*60	// 5 minutes

#define MAX_RETRIES			20	// Maximum no. of retries when a lock is encountered
#define RETRY_BACKOFF			2000	// Multipler to backoff DB retry on lock

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

#define _DB_NAME              "/foglamp.sqlite"

#define LEN_BUFFER_DATE 100
#define F_TIMEH24_S     	"%H:%M:%S"
#define F_DATEH24_S     	"%Y-%m-%d %H:%M:%S"
#define F_DATEH24_M     	"%Y-%m-%d %H:%M"
#define F_DATEH24_H     	"%Y-%m-%d %H"
// This is the default datetime format in FogLAMP: 2018-05-03 18:15:00.622
#define F_DATEH24_MS    	"%Y-%m-%d %H:%M:%f"
// Format up to seconds
#define F_DATEH24_SEC    	"%Y-%m-%d %H:%M:%S"
#define SQLITE3_NOW     	"strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')"
// The default precision is milliseconds, it adds microseconds and timezone
#define SQLITE3_NOW_READING     "strftime('%Y-%m-%d %H:%M:%f000+00:00', 'now')"
#define SQLITE3_FOGLAMP_DATETIME_TYPE "DATETIME"
static time_t connectErrorTime = 0;
map<string, string> sqliteDateFormat = {
						{"HH24:MI:SS",
							F_TIMEH24_S},
						{"YYYY-MM-DD HH24:MI:SS.MS",
							F_DATEH24_MS},
						{"YYYY-MM-DD HH24:MI:SS",
							F_DATEH24_S},
						{"YYYY-MM-DD HH24:MI",
							F_DATEH24_M},
						{"YYYY-MM-DD HH24",
							F_DATEH24_H},
						{"", ""}
					};

/**
 * This SQLIte3 query callback returns a formatted date
 * by SELECT strftime('format', column, 'locatime')
 *
 * @param data         Output parameter to update with new datetime
 * @param nCols        The number of columns or the row
 * @param colValues    The column values
 * @param colNames     The column names
 * @return             0 on success, 1 otherwise
 */
static int dateCallback(void *data,
			int nCols,
			char **colValues,
			char **colNames)
{
	if (colValues[0] != NULL)
	{
		memcpy((char *)data,
			colValues[0],
			strlen(colValues[0]));
		// OK
		return 0;
	}
	else
	{
		// Failure
		return 1;
	}
}

/**
 * Apply FogLAMP default datetime formatting
 * to a detected DATETIME datatype column
 *
 * @param pStmt    Current SQLite3 result set
 * @param i        Current column index
 * @param          Output parameter for new date
 * @return         True is format has been applied,
 *		   False otherwise
 */
bool Connection::applyColumnDateTimeFormat(sqlite3_stmt *pStmt,
					   int i,
					   string& newDate)
{

	bool apply_format = false;
	string formatStmt = {};

	if (sqlite3_column_database_name(pStmt, i) != NULL &&
	    sqlite3_column_table_name(pStmt, i)    != NULL)
	{

		if ((strcmp(sqlite3_column_origin_name(pStmt, i), "user_ts") == 0) &&
		    (strcmp(sqlite3_column_table_name(pStmt, i), "readings") == 0) &&
		    (strlen((char *) sqlite3_column_text(pStmt, i)) == 32))
		{

			// Extract milliseconds and microseconds for the user_ts field of the readings table
			formatStmt = string("SELECT strftime('");
			formatStmt += string(F_DATEH24_SEC);
			formatStmt += "', '" + string((char *) sqlite3_column_text(pStmt, i));
			formatStmt += "')";
			formatStmt += " || substr('" + string((char *) sqlite3_column_text(pStmt, i));
			formatStmt += "', instr('" + string((char *) sqlite3_column_text(pStmt, i));
			formatStmt += "', '.'), 7)";

			apply_format = true;
		}
		else
		{
			/**
			 * Handle here possible unformatted DATETIME column type
			 * If (column_name == column_original_name) AND
			 * (sqlite3_column_table_name() == "DATETIME")
			 * we assume the column has not been formatted
			 * by any datetime() or strftime() SQLite function.
			 * Thus we apply default FOGLAMP formatting:
			 * "%Y-%m-%d %H:%M:%f"
			 */
			if (sqlite3_column_database_name(pStmt, i) != NULL &&
			    sqlite3_column_table_name(pStmt, i) != NULL &&
			    (strcmp(sqlite3_column_origin_name(pStmt, i),
				    sqlite3_column_name(pStmt, i)) == 0))
			{
				const char *pzDataType;
				int retType = sqlite3_table_column_metadata(dbHandle,
									    sqlite3_column_database_name(pStmt, i),
									    sqlite3_column_table_name(pStmt, i),
									    sqlite3_column_name(pStmt, i),
									    &pzDataType,
									    NULL, NULL, NULL, NULL);

				// Check whether to Apply dateformat
				if (pzDataType != NULL &&
				    retType == SQLITE_OK &&
				    strcmp(pzDataType, SQLITE3_FOGLAMP_DATETIME_TYPE) == 0 &&
				    strcmp(sqlite3_column_origin_name(pStmt, i),
					   sqlite3_column_name(pStmt, i)) == 0)
				{
					// Column metadata found and column datatype is "pzDataType"
					formatStmt = string("SELECT strftime('");
					formatStmt += string(F_DATEH24_MS);
					formatStmt += "', '" + string((char *) sqlite3_column_text(pStmt, i));
					formatStmt += "')";

					apply_format = true;

				}
				else
				{
					// Format not done
					// Just log the error if present
					if (retType != SQLITE_OK)
					{
						Logger::getLogger()->error("SQLite3 failed " \
                                                                "to call sqlite3_table_column_metadata() " \
                                                                "for column '%s'",
									   sqlite3_column_name(pStmt, i));
					}
				}
			}
		}
	}

	if (apply_format)
	{

		char* zErrMsg = NULL;
		// New formatted data
		char formattedData[100] = "";

		// Exec the format SQL
		int rc = SQLexec(dbHandle,
				 formatStmt.c_str(),
				 dateCallback,
				 formattedData,
				 &zErrMsg);

		if (rc == SQLITE_OK )
		{
			// Use new formatted datetime value
			newDate.assign(formattedData);

			return true;
		}
		else
		{
			Logger::getLogger()->error("SELECT dateformat '%s': error %s",
						   formatStmt.c_str(),
						   zErrMsg);

			sqlite3_free(zErrMsg);
		}

	}

	return false;
}

/**
 * Apply the specified date format
 * using the available formats in SQLite3
 * for a specific column
 *
 * If the requested format is not availble
 * the input column is used as is.
 * Additionally milliseconds could be rounded
 * upon request.
 * The routine return false if datwe format is not
 * found and the caller might decide to raise an error
 * or use the non formatted value
 *
 * @param inFormat     Input date format from application
 * @param colName      The column name to format
 * @param outFormat    The formatted column
 * @return             True if format has been applied or
 *		       false id no format is in use.
 */
static bool applyColumnDateFormat(const string& inFormat,
				  const string& colName,
				  string& outFormat,
				  bool roundMs = false)

{
bool retCode;
	// Get format, if any, from the supported formats map
	const string format = sqliteDateFormat[inFormat];
	if (!format.empty())
	{
		// Apply found format via SQLite3 strftime()
		outFormat.append("strftime('");
		outFormat.append(format);
		outFormat.append("', ");

		// Check whether we have to round milliseconds
		if (roundMs == true &&
		    format.back() == 'f')
		{
			outFormat.append("cast(round((julianday(");
			outFormat.append(colName);
			outFormat.append(") - 2440587.5)*86400 -0.00005, 3) AS FLOAT), 'unixepoch'");
		}
		else
		{
			outFormat.append(colName);
		}

		outFormat.append(", 'localtime')");	// MR TRY THIS
		retCode = true;
	}
	else
	{
		// Use column as is
		outFormat.append(colName);
		retCode = false;
	}

	return retCode;
}

/**
 * Apply the specified date format
 * using the available formats in SQLite3
 * for a specific column
 *
 * If the requested format is not availble
 * the input column is used as is.
 * Additionally milliseconds could be rounded
 * upon request.
 * The routine return false if datwe format is not
 * found and the caller might decide to raise an error
 * or use the non formatted value
 *
 * @param inFormat     Input date format from application
 * @param colName      The column name to format
 * @param outFormat    The formatted column
 * @return             True if format has been applied or
 *		       false id no format is in use.
 */
static bool applyColumnDateFormatLocaltime(const string& inFormat,
				  const string& colName,
				  string& outFormat,
				  bool roundMs = false)

{
bool retCode;
	// Get format, if any, from the supported formats map
	const string format = sqliteDateFormat[inFormat];
	if (!format.empty())
	{
		// Apply found format via SQLite3 strftime()
		outFormat.append("strftime('");
		outFormat.append(format);
		outFormat.append("', ");

		// Check whether we have to round milliseconds
		if (roundMs == true &&
		    format.back() == 'f')
		{
			outFormat.append("cast(round((julianday(");
			outFormat.append(colName);
			outFormat.append(") - 2440587.5)*86400 -0.00005, 3) AS FLOAT), 'unixepoch'");
		}
		else
		{
			outFormat.append(colName);
		}

		outFormat.append(", 'localtime')");	// MR force localtime
		retCode = true;
	}
	else
	{
		// Use column as is
		outFormat.append(colName);
		retCode = false;
	}

	return retCode;
}

/**
 * Apply the specified date format
 * using the available formats in SQLite3
 *
 * @param inFormat     Input date format from application
 * @param outFormat    The formatted column
 * @return             True if format has been applied or
 *		       false
 */
static bool applyDateFormat(const string& inFormat,
			    string& outFormat)

{
bool retCode;
	// Get format, if any, from the supported formats map
	const string format = sqliteDateFormat[inFormat];
	if (!format.empty())
	{
		// Apply found format via SQLite3 strftime()
		outFormat.append("strftime('");
		outFormat.append(format);
		outFormat.append("', ");

		return true;
	}
	else
	{
		return false;
	}
}

/**
 * Create a SQLite3 database connection
 */
Connection::Connection()
{
	string dbPath;
	const char *defaultConnection = getenv("DEFAULT_SQLITE_DB_FILE");

	m_logSQL = false;
	m_queuing = 0;

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

	/**
	 * Make a connection to the database
	 * and check backend connection was successfully made
	 * Note:
	 *   we assume the database already exists, so the flag
	 *   SQLITE_OPEN_CREATE is not added in sqlite3_open_v2 call
	 */
	if (sqlite3_open_v2(dbPath.c_str(),
			    &dbHandle,
			    SQLITE_OPEN_READWRITE,
			    NULL) != SQLITE_OK)
	{
		const char* dbErrMsg = sqlite3_errmsg(dbHandle);
		const char* errMsg = "Failed to open the SQLite3 database";

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
		int rc;
		char *zErrMsg = NULL;
		/*
		 * Build the ATTACH DATABASE command in order to get
		 * 'foglamp.' prefix in all SQL queries
		 */
		SQLBuffer attachDb;
		attachDb.append("ATTACH DATABASE '");
		attachDb.append(dbPath + "' AS foglamp;");

		const char *sqlStmt = attachDb.coalesce();

		// Exec the statement
		rc = SQLexec(dbHandle,
			     sqlStmt,
			     NULL,
			     NULL,
			     &zErrMsg);

		// Check result
		if (rc != SQLITE_OK)
		{
			const char* errMsg = "Failed to attach 'foglamp' database in";
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
			Logger::getLogger()->info("Connected to SQLite3 database: %s",
						  dbPath.c_str());
		}
		//Release sqlStmt buffer
		delete[] sqlStmt;
	}
}

/**
 * Destructor for the database connection.
 * Close the connection to SQLite3 db
 */
Connection::~Connection()
{
	sqlite3_close_v2(dbHandle);
}

/**
 * Enable or disable the tracing of SQL statements
 *
 * @param flag	Desired state of the SQL trace flag
 */
void Connection::setTrace(bool flag)
{
	m_logSQL = flag;
}
/**
 * Map a SQLite3 result set to a string version of a JSON document
 *
 * @param res          Sqlite3 result set
 * @param resultSet    Output Json as string
 * @return             SQLite3 result code of sqlite3_step(res)
 *
 */
int Connection::mapResultSet(void* res, string& resultSet)
{
// Cast to SQLite3 result set
sqlite3_stmt* pStmt = (sqlite3_stmt *)res;
// JSON generic document
Document doc;
// SQLite3 return code
int rc;
// Number of returned rows, number of columns
unsigned long nRows = 0, nCols = 0;

	// Create the JSON document
	doc.SetObject();
	// Get document allocator
	Document::AllocatorType& allocator = doc.GetAllocator();
	// Create the array for returned rows
	Value rows(kArrayType);
	// Rows counter, set it to 0 now
	Value count;
	count.SetInt(0);

	// Iterate over all the rows in the resultSet
	while ((rc = SQLstep(pStmt)) == SQLITE_ROW)
	{
		// Get number of columns for current row
		nCols = sqlite3_column_count(pStmt);
		// Create the 'row' object
		Value row(kObjectType);

		// Build the row with all fields
		for (int i = 0; i < nCols; i++)
		{
			// JSON document for the current row
			Document d;
			// Set object name as the column name
			Value name(sqlite3_column_name(pStmt, i), allocator);
			// Get the "TEXT" value of the column value
			char* str = (char *)sqlite3_column_text(pStmt, i);

			// Check the column value datatype
			switch (sqlite3_column_type(pStmt, i))
			{
				case (SQLITE_NULL):
				{
					row.AddMember(name, "", allocator);
					break;
				}
				case (SQLITE3_TEXT):
				{

					/**
					 * Handle here possible unformatted DATETIME column type
					 */
					string newDate;
					if (applyColumnDateTimeFormat(pStmt, i, newDate))
					{
						// Use new formatted datetime value
						str = (char *)newDate.c_str();
					}

					Value value;
					if (!d.Parse(str).HasParseError())
					{
						// JSON parsing ok, use the document
						value = Value(d, allocator);
					}
					else
					{
						// Use (char *) value
						value = Value(str, allocator);
					}
					// Add name & value to the current row
					row.AddMember(name, value, allocator);
					break;
				}
				case (SQLITE_INTEGER):
				{
					int64_t intVal = atol(str);
					// Add name & value to the current row
					row.AddMember(name, intVal, allocator);
					break;
				}
				case (SQLITE_FLOAT):
				{
					double dblVal = atof(str);
					// Add name & value to the current row
					row.AddMember(name, dblVal, allocator);
					break;
				}
				default:
				{
					// Default: use  (char *) value
					Value value(str != NULL ? str : "", allocator);
					// Add name & value to the current row
					row.AddMember(name, value, allocator);
					break;
				}
			}
		}

		// All fields added: increase row counter
		nRows++;

		// Add the current row to the all rows object
		rows.PushBack(row, allocator);
	}

	// All rows added: update rows count
	count.SetInt(nRows);

	// Add 'rows' and 'count' to the final JSON document
	doc.AddMember("count", count, allocator);
	doc.AddMember("rows", rows, allocator);

	/* Write out the JSON document we created */
	StringBuffer buffer;
	Writer<StringBuffer> writer(buffer);
	doc.Accept(writer);

	// Set the result as a CPP string 
	resultSet = buffer.GetString();

	// Return SQLite3 ret code
	return rc;
}

/**
 * This SQLIte3 query callback just returns the number of rows seen
 * by a SELECT statement in the 'data' parameter
 *
 * @param data         Output parameter to update with number of rows
 * @param nCols        The number of columns or the row
 * @param colValues    The column values
 * @param colNames     The column names
 * @return             0 on success, 1 otherwise
 */
static int selectCallback(void *data,
			  int nCols,
			  char **colValues,
			  char **colNames)
{
int *nRows = (int *)data;
	// Increment the number of rows seen
	*nRows++;

	// Set OK
	return 0;
}

/**
 * This SQLIte3 query count callback just returns the number of rows
 * as per 'count(*)' column
 * by a SELECT statement in the 'data' parameter
 *
 * @param data         Output parameter to update with number of rows
 * @param nCols        The number of columns or the row
 * @param colValues    The column values
 * @param colNames     The column names
 * @return             0 on success, 1 otherwise
 */
static int countCallback(void *data,
			 int nCols,
			 char **colValues,
			 char **colNames)
{
int *nRows = (int *)data;

	// Return the value of the first column: the count(*)
	*nRows = atoi(colValues[0]);

	// Set OK
	return 0;
}

/**
 * This SQLIte3 query rowid callback just returns the rowid
 * by a SELECT statement in the 'data' parameter
 *
 * @param data         Output parameter to update with rowid
 * @param nCols        The number of columns or the row
 * @param colValues    The column values
 * @param colNames     The column names
 * @return             0 on success, 1 otherwise
 */
static int rowidCallback(void *data,
			 int nCols,
			 char **colValues,
			 char **colNames)
{
unsigned long *rowid = (unsigned long *)data;

	// Return the value of the first column: the count(*)
	if (colValues[0])
		*rowid = strtoul(colValues[0], NULL, 10);
	else
		*rowid = 0;

	// Set OK
	return 0;
}

/**
 * Perform a query against a common table
 *
 */
bool Connection::retrieve(const string& table,
			  const string& condition,
			  string& resultSet)
{
// Default template parameter uses UTF8 and MemoryPoolAllocator.
Document	document;
SQLBuffer	sql;
// Extra constraints to add to where clause
SQLBuffer	jsonConstraints;

	try {
		if (dbHandle == NULL)
		{
			raiseError("retrieve", "No SQLite 3 db connection available");
			return false;
		}

		if (condition.empty())
		{
			sql.append("SELECT * FROM foglamp.");
			sql.append(table);
		}
		else
		{
			if (document.Parse(condition.c_str()).HasParseError())
			{
				raiseError("retrieve", "Failed to parse JSON payload");
				return false;
			}
			if (document.HasMember("aggregate"))
			{
				sql.append("SELECT ");
				if (document.HasMember("modifier"))
				{
					sql.append(document["modifier"].GetString());
					sql.append(' ');
				}
				if (!jsonAggregates(document, document["aggregate"], sql, jsonConstraints))
				{
					return false;
				}
				sql.append(" FROM foglamp.");
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
						sql.append(itr->GetString());
					}
					else
					{
						if (itr->HasMember("column"))
						{
							if (! (*itr)["column"].IsString())
							{
								raiseError("rerieve",
									   "column must be a string");
								return false;
							}
							if (itr->HasMember("format"))
							{
								if (! (*itr)["format"].IsString())
								{
									raiseError("rerieve",
										   "format must be a string");
									return false;
								}

								// SQLite 3 date format.
								string new_format;
								applyColumnDateFormat((*itr)["format"].GetString(),
										      (*itr)["column"].GetString(),
										      new_format, true);
								// Add the formatted column or use it as is
								sql.append(new_format);
							}
							else if (itr->HasMember("timezone"))
							{
								if (! (*itr)["timezone"].IsString())
								{
									raiseError("rerieve",
										   "timezone must be a string");
									return false;
								}
								// SQLite3 doesnt support time zone formatting
								if (strcasecmp((*itr)["timezone"].GetString(), "utc") != 0)
								{
									raiseError("retrieve",
										   "SQLite3 plugin does not support timezones in qeueries");
									return false;
								}
								else
								{
									sql.append("strftime('%Y-%m-%d %H:%M:%f', ");
									sql.append((*itr)["column"].GetString());
									sql.append(", 'utc')");
								}
							}
							else
							{
								sql.append((*itr)["column"].GetString());
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
				sql.append(" FROM foglamp.");
			}
			else
			{
				sql.append("SELECT ");
				if (document.HasMember("modifier"))
				{
					sql.append(document["modifier"].GetString());
					sql.append(' ');
				}
				sql.append(" * FROM foglamp.");
			}
			sql.append(table);
			if (document.HasMember("where"))
			{
				sql.append(" WHERE ");
			 
				if (document.HasMember("where"))
				{
					if (!jsonWhereClause(document["where"], sql, true))
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
			if (!jsonModifiers(document, sql))
			{
				return false;
			}
		}
		sql.append(';');

		const char *query = sql.coalesce();
		char *zErrMsg = NULL;
		int rc;
		sqlite3_stmt *stmt;

		logSQL("CommonRetrive", query);

		// Prepare the SQL statement and get the result set
		rc = sqlite3_prepare_v2(dbHandle, query, -1, &stmt, NULL);

		if (rc != SQLITE_OK)
		{
			raiseError("retrieve", sqlite3_errmsg(dbHandle));
			Logger::getLogger()->error("SQL statement: %s", query);
			delete[] query;
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
			Logger::getLogger()->error("SQL statement: %s", query);
			delete[] query;
			// Failure
			return false;
		}

		// Release memory for 'query' var
		delete[] query;
		// Success
		return true;
	} catch (exception e) {
		raiseError("retrieve", "Internal error: %s", e.what());
	}
}

/**
 * Insert data into a table
 */
int Connection::insert(const std::string& table, const std::string& data)
{
SQLBuffer	sql;
Document	document;
SQLBuffer	values;
int		col = 0;
 
	if (document.Parse(data.c_str()).HasParseError())
	{
		raiseError("insert", "Failed to parse JSON payload\n");
		return -1;
	}
 	sql.append("INSERT INTO foglamp.");
	sql.append(table);
	sql.append(" (");
	for (Value::ConstMemberIterator itr = document.MemberBegin();
		itr != document.MemberEnd(); ++itr)
	{
		if (col)
			sql.append(", ");
		sql.append(itr->name.GetString());
 
		if (col)
			values.append(", ");
		if (itr->value.IsString())
		{
			const char *str = itr->value.GetString();
			if (strcmp(str, "now()") == 0)
			{
				values.append(SQLITE3_NOW);
			}
			else
			{
				values.append('\'');
				values.append(escape(str));
				values.append('\'');
			}
		}
		else if (itr->value.IsDouble())
			values.append(itr->value.GetDouble());
		else if (itr->value.IsNumber())
			values.append(itr->value.GetInt());
		else if (itr->value.IsObject())
		{
			StringBuffer buffer;
			Writer<StringBuffer> writer(buffer);
			itr->value.Accept(writer);
			values.append('\'');
			values.append(escape(buffer.GetString()));
			values.append('\'');
		}
		col++;
	}
	sql.append(") values (");
	const char *vals = values.coalesce();
	sql.append(vals);
	delete[] vals;
	sql.append(");");

	const char *query = sql.coalesce();
	logSQL("CommonInsert", query);
	char *zErrMsg = NULL;
	int rc;

	// Exec INSERT statement: no callback, no result set
	rc = SQLexec(dbHandle,
		     query,
		     NULL,
		     NULL,
		     &zErrMsg);

	// Check exec result
	if (rc == SQLITE_OK )
	{
		// Success. Release memory for 'query' var
		delete[] query;
		return sqlite3_changes(dbHandle);
	}

	raiseError("insert", zErrMsg);
	Logger::getLogger()->error("SQL statement: %s", query);
	sqlite3_free(zErrMsg);

	// Release memory for 'query' var
	delete[] query;

	// Failure
	return -1;
}

/**
 * Perform an update against a common table
 * This routine uses SQLite 3 JSON1 extension:
 *
 *    json_set(field, '$.key.value', the_value)
 *
 */
int Connection::update(const string& table, const string& payload)
{
// Default template parameter uses UTF8 and MemoryPoolAllocator.
Document	document;
SQLBuffer	sql;

	int 	row = 0;
	ostringstream convert;

	std::size_t arr = payload.find("updates");
	bool changeReqd = (arr == std::string::npos || arr > 8);
	if (changeReqd)
		{
		convert << "{ \"updates\" : [ ";
		convert << payload;
		convert << " ] }";
		}

	if (document.Parse(changeReqd?convert.str().c_str():payload.c_str()).HasParseError())
	{
		raiseError("update", "Failed to parse JSON payload");
		return -1;
	}
	else
	{
		Value &updates = document["updates"];
		if (!updates.IsArray())
		{
			raiseError("update", "Payload is missing the updates array");
			return -1;
		}
		
		sql.append("BEGIN TRANSACTION;");
		int i=0;
		for (Value::ConstValueIterator iter = updates.Begin(); iter != updates.End(); ++iter,++i)
		{
			if (!iter->IsObject())
			{
				raiseError("update",
					   "Each entry in the update array must be an object");
				return -1;
			}
			sql.append("UPDATE foglamp.");
			sql.append(table);
			sql.append(" SET ");

			int		col = 0;
			if ((*iter).HasMember("values"))
			{
				const Value& values = (*iter)["values"];
				for (Value::ConstMemberIterator itr = values.MemberBegin();
						itr != values.MemberEnd(); ++itr)
				{
					if (col != 0)
					{
						sql.append( ", ");
					}
					sql.append(itr->name.GetString());
					sql.append(" = ");
		 
					if (itr->value.IsString())
					{
						const char *str = itr->value.GetString();
						if (strcmp(str, "now()") == 0)
						{
							sql.append(SQLITE3_NOW);
						}
						else
						{
							sql.append('\'');
							sql.append(escape(str));
							sql.append('\'');
						}
					}
					else if (itr->value.IsDouble())
						sql.append(itr->value.GetDouble());
					else if (itr->value.IsNumber())
						sql.append(itr->value.GetInt());
					else if (itr->value.IsObject())
					{
						StringBuffer buffer;
						Writer<StringBuffer> writer(buffer);
						itr->value.Accept(writer);
						sql.append('\'');
						sql.append(escape(buffer.GetString()));
						sql.append('\'');
					}
					col++;
				}
			}
			if ((*iter).HasMember("expressions"))
			{
				const Value& exprs = (*iter)["expressions"];
				if (!exprs.IsArray())
				{
					raiseError("update", "The property exressions must be an array");
					return -1;
				}
				for (Value::ConstValueIterator itr = exprs.Begin(); itr != exprs.End(); ++itr)
				{
					if (col != 0)
					{
						sql.append( ", ");
					}
					if (!itr->IsObject())
					{
						raiseError("update",
							   "expressions must be an array of objects");
						return -1;
					}
					if (!itr->HasMember("column"))
					{
						raiseError("update",
							   "Missing column property in expressions array item");
						return -1;
					}
					if (!itr->HasMember("operator"))
					{
						raiseError("update",
							   "Missing operator property in expressions array item");
						return -1;
					}
					if (!itr->HasMember("value"))
					{
						raiseError("update",
							   "Missing value property in expressions array item");
						return -1;
					}
					sql.append((*itr)["column"].GetString());
					sql.append(" = ");
					sql.append((*itr)["column"].GetString());
					sql.append(' ');
					sql.append((*itr)["operator"].GetString());
					sql.append(' ');
					const Value& value = (*itr)["value"];
		 
					if (value.IsString())
					{
						const char *str = value.GetString();
						if (strcmp(str, "now()") == 0)
						{
							sql.append(SQLITE3_NOW);
						}
						else
						{
							sql.append('\'');
							sql.append(str);
							sql.append('\'');
						}
					}
					else if (value.IsDouble())
						sql.append(value.GetDouble());
					else if (value.IsNumber())
						sql.append(value.GetInt());
					else if (value.IsObject())
					{
						StringBuffer buffer;
						Writer<StringBuffer> writer(buffer);
						value.Accept(writer);
						sql.append('\'');
						sql.append(buffer.GetString());
						sql.append('\'');
					}
					col++;
				}
			}
			if ((*iter).HasMember("json_properties"))
			{
				const Value& exprs = (*iter)["json_properties"];
				if (!exprs.IsArray())
				{
					raiseError("update",
						   "The property json_properties must be an array");
					return -1;
				}
				for (Value::ConstValueIterator itr = exprs.Begin(); itr != exprs.End(); ++itr)
				{
					if (col != 0)
					{
						sql.append( ", ");
					}
					if (!itr->IsObject())
					{
						raiseError("update",
							   "json_properties must be an array of objects");
						return -1;
					}
					if (!itr->HasMember("column"))
					{
						raiseError("update",
							   "Missing column property in json_properties array item");
						return -1;
					}
					if (!itr->HasMember("path"))
					{
						raiseError("update",
							   "Missing path property in json_properties array item");
						return -1;
					}
					if (!itr->HasMember("value"))
					{
						raiseError("update",
							  "Missing value property in json_properties array item");
						return -1;
					}
					sql.append((*itr)["column"].GetString());

					// SQLite 3 JSON1 extension: json_set
					// json_set(field, '$.key.value', the_value)
					sql.append(" = json_set(");
					sql.append((*itr)["column"].GetString());
					sql.append(", '$.");

					const Value& path = (*itr)["path"];
					if (!path.IsArray())
					{
						raiseError("update",
							   "The property path must be an array");
						return -1;
					}
					int pathElement = 0;
					for (Value::ConstValueIterator itr2 = path.Begin();
						itr2 != path.End(); ++itr2)
					{
						if (pathElement > 0)
						{
							sql.append('.');
						}
						if (itr2->IsString())
						{
							sql.append(itr2->GetString());
						}
						else
						{
							raiseError("update",
								   "The elements of path must all be strings");
							return -1;
						}
						pathElement++;
					}
					sql.append("', ");
					const Value& value = (*itr)["value"];
		 
					if (value.IsString())
					{
						const char *str = value.GetString();
						if (strcmp(str, "now()") == 0)
						{
							sql.append(SQLITE3_NOW);
						}
						else
						{
							sql.append("\"");
							sql.append(str);
							sql.append("\"");
						}
					}
					else if (value.IsDouble())
					{
						sql.append(value.GetDouble());
					}
					else if (value.IsNumber())
					{
						sql.append(value.GetInt());
					}
					else if (value.IsObject())
					{
						StringBuffer buffer;
						Writer<StringBuffer> writer(buffer);
						value.Accept(writer);
						sql.append('\'');
						sql.append(buffer.GetString());
						sql.append('\'');
					}
					sql.append(")");
					col++;
				}
			}
			if (col == 0)
			{
				raiseError("update",
					   "Missing values or expressions object in payload");
				return -1;
			}
			if ((*iter).HasMember("condition"))
			{
				sql.append(" WHERE ");
				if (!jsonWhereClause((*iter)["condition"], sql))
				{
					return false;
				}
			}
			else if ((*iter).HasMember("where"))
			{
				sql.append(" WHERE ");
				if (!jsonWhereClause((*iter)["where"], sql))
				{
					return false;
				}
			}
		sql.append(';');
		}
	}
	sql.append("COMMIT TRANSACTION;");
	
	const char *query = sql.coalesce();
	logSQL("CommonUpdate", query);
	char *zErrMsg = NULL;
	int update = 0;
	int rc;

	// Exec the UPDATE statement: no callback, no result set
	rc = SQLexec(dbHandle,
		     query,
		     NULL,
		     NULL,
		     &zErrMsg);

	// Check result code
	if (rc != SQLITE_OK)
	{
		raiseError("update", zErrMsg);
		sqlite3_free(zErrMsg);
		if (sqlite3_get_autocommit(dbHandle)==0) // transaction is still open, do rollback
		{
			rc=SQLexec(dbHandle,
				"ROLLBACK TRANSACTION;",
				NULL,
				NULL,
				&zErrMsg);
			if (rc != SQLITE_OK)
			{
				raiseError("rollback", zErrMsg);
				sqlite3_free(zErrMsg);
			}
		}
		Logger::getLogger()->error("SQL statement: %s", query);
		// Release memory for 'query' var
		delete[] query;
		return -1;
	}
	else
	{
		// Release memory for 'query' var
		delete[] query;
		update = sqlite3_changes(dbHandle);
		if (update == 0)
		{
 			raiseError("update", "No rows where updated");
			return -1;
		}

		// Return success
		return update;
	}

	// Return failure
	return -1;
}

/**
 * Perform a delete against a common table
 *
 */
int Connection::deleteRows(const string& table, const string& condition)
{
// Default template parameter uses UTF8 and MemoryPoolAllocator.
Document document;
SQLBuffer	sql;
 
	sql.append("DELETE FROM foglamp.");
	sql.append(table);
	if (! condition.empty())
	{
		sql.append(" WHERE ");
		if (document.Parse(condition.c_str()).HasParseError())
		{
			raiseError("delete", "Failed to parse JSON payload");
			return -1;
		}
		else
		{
			if (document.HasMember("where"))
			{
				if (!jsonWhereClause(document["where"], sql))
				{
					return -1;
				}
			}
			else
			{
				raiseError("delete",
					   "JSON does not contain where clause");
				return -1;
			}
		}
	}
	sql.append(';');

	const char *query = sql.coalesce();
	logSQL("CommonDelete", query);
	char *zErrMsg = NULL;
	int delete_rows;
	int rc;

	// Exec the DELETE statement: no callback, no result set
	rc = SQLexec(dbHandle,
		     query,
		     NULL,
		     NULL,
		     &zErrMsg);


	// Check result code
	if (rc == SQLITE_OK)
	{
		// Success. Release memory for 'query' var
		delete[] query;
        	return sqlite3_changes(dbHandle);
	}
	else
	{
 		raiseError("delete", zErrMsg);
		sqlite3_free(zErrMsg);
		Logger::getLogger()->error("SQL statement: %s", query);
		delete[] query;

		// Failure
		return -1;
	}
}

/**
 * Format a date to a fixed format with milliseconds, microseconds and
 * timezone expressed, examples :
 *
 *   case - formatted |2019-01-01 10:01:01.000000+00:00| date |2019-01-01 10:01:01|
 *   case - formatted |2019-02-01 10:02:01.000000+00:00| date |2019-02-01 10:02:01.0|
 *   case - formatted |2019-02-02 10:02:02.841000+00:00| date |2019-02-02 10:02:02.841|
 *   case - formatted |2019-02-03 10:02:03.123456+00:00| date |2019-02-03 10:02:03.123456|
 *   case - formatted |2019-03-01 10:03:01.100000+00:00| date |2019-03-01 10:03:01.1+00:00|
 *   case - formatted |2019-03-02 10:03:02.123000+00:00| date |2019-03-02 10:03:02.123+00:00|
 *   case - formatted |2019-03-03 10:03:03.123456+00:00| date |2019-03-03 10:03:03.123456+00:00|
 *   case - formatted |2019-03-04 10:03:04.123456+01:00| date |2019-03-04 10:03:04.123456+01:00|
 *   case - formatted |2019-03-05 10:03:05.123456-01:00| date |2019-03-05 10:03:05.123456-01:00|
 *   case - formatted |2019-03-04 10:03:04.123456+02:30| date |2019-03-04 10:03:04.123456+02:30|
 *   case - formatted |2019-03-05 10:03:05.123456-02:30| date |2019-03-05 10:03:05.123456-02:30|
 *
 * @param out	false if the date is invalid
 *
 */
bool Connection::formatDate(char *formatted_date, size_t buffer_size, const char *date) {

	struct timeval tv = {0};
	struct tm tm  = {0};
	char *valid_date = nullptr;

	// Extract up to seconds
	memset(&tm, 0, sizeof(tm));
	valid_date = strptime(date, "%Y-%m-%d %H:%M:%S", &tm);

	if (! valid_date)
	{
		return (false);
	}

	strftime (formatted_date, buffer_size, "%Y-%m-%d %H:%M:%S", &tm);

	// Work out the microseconds from the fractional part of the seconds
	char fractional[10] = {0};
	sscanf(date, "%*d-%*d-%*d %*d:%*d:%*d.%[0-9]*", fractional);
	// Truncate to max 6 digits
	fractional[6] = 0;
	int multiplier = 6 - (int)strlen(fractional);
	if (multiplier < 0)
		multiplier = 0;
	while (multiplier--)
		strcat(fractional, "0");

	strcat(formatted_date ,".");
	strcat(formatted_date ,fractional);

	// Handles timezone
	char timezone_hour[5] = {0};
	char timezone_min[5] = {0};
	char sign[2] = {0};

	sscanf(date, "%*d-%*d-%*d %*d:%*d:%*d.%*d-%2[0-9]:%2[0-9]", timezone_hour, timezone_min);
	if (timezone_hour[0] != 0)
	{
		strcat(sign, "-");
	}
	else
	{
		memset(timezone_hour, 0, sizeof(timezone_hour));
		memset(timezone_min,  0, sizeof(timezone_min));

		sscanf(date, "%*d-%*d-%*d %*d:%*d:%*d.%*d+%2[0-9]:%2[0-9]", timezone_hour, timezone_min);
		if  (timezone_hour[0] != 0)
		{
			strcat(sign, "+");
		}
		else
		{
			// No timezone is expressed in the source date
			// the default UTC is added
			strcat(formatted_date, "+00:00");
		}
	}

	if (sign[0] != 0)
	{
		if (timezone_hour[0] != 0)
		{
			strcat(formatted_date, sign);

			// Pad with 0 if an hour having only 1 digit was provided
			// +1 -> +01
			if (strlen(timezone_hour) == 1)
				strcat(formatted_date, "0");

			strcat(formatted_date, timezone_hour);
			strcat(formatted_date, ":");
		}

		if (timezone_min[0] != 0)
		{
			strcat(formatted_date, timezone_min);

			// Pad with 0 if minutes having only 1 digit were provided
			// 3 -> 30
			if (strlen(timezone_min) == 1)
				strcat(formatted_date, "0");

		}
		else
		{
			// Minutes aren't expressed in the source date
			strcat(formatted_date, "00");
		}
	}


	return (true);


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
 * Fetch a block of readings from the reading table
 * It might not work with SQLite 3
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
char sqlbuffer[1100];
char *zErrMsg = NULL;
int rc;
int retrieve;

	// SQL command to extract the data from the foglamp.readings
	const char *sql_cmd = R"(
	SELECT
		id,
		asset_code,
		read_key,
		reading,
		strftime('%%Y-%%m-%%d %%H:%%M:%%S', user_ts, 'utc')  ||
		substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
		strftime('%%Y-%%m-%%d %%H:%%M:%%f', ts, 'utc') AS ts
	FROM foglamp.readings
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
						read_key,
						reading,
						strftime('%Y-%m-%d %H:%M:%S', user_ts, 'localtime')  ||
						substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
						strftime('%Y-%m-%d %H:%M:%f', ts, 'localtime') AS ts
					FROM foglamp.readings)";

			sql.append(sql_cmd);
		}
		else
		{
			if (document.Parse(condition.c_str()).HasParseError())
			{
				raiseError("retrieve", "Failed to parse JSON payload");
				return false;
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
				if (!jsonAggregates(document, document["aggregate"], sql, jsonConstraints))
				{
					return false;
				}
				sql.append(" FROM foglamp.");
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
						sql.append(itr->GetString());
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

										sql.append("strftime('%Y-%m-%d %H:%M:%S', user_ts, 'utc') ");
										sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
										if (! itr->HasMember("alias"))
										{
											sql.append(" AS ");
											sql.append((*itr)["column"].GetString());
										}
									}
									else
									{
										sql.append("strftime('%Y-%m-%d %H:%M:%f', ");
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

										sql.append("strftime('%Y-%m-%d %H:%M:%S', user_ts, 'localtime') ");
										sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
										if (! itr->HasMember("alias"))
										{
											sql.append(" AS ");
											sql.append((*itr)["column"].GetString());
										}
									}
									else
									{
										sql.append("strftime('%Y-%m-%d %H:%M:%f', ");
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

									sql.append("strftime('%Y-%m-%d %H:%M:%S', user_ts, 'localtime') ");
									sql.append(" || substr(user_ts, instr(user_ts, '.'), 7) ");
									if (! itr->HasMember("alias"))
									{
										sql.append(" AS ");
										sql.append((*itr)["column"].GetString());
									}
								}
								else
								{
									sql.append("strftime('%Y-%m-%d %H:%M:%f', ");
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
				sql.append(" FROM foglamp.");
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
						read_key,
						reading,
						strftime('%Y-%m-%d %H:%M:%S', user_ts, 'localtime')  ||
						substr(user_ts, instr(user_ts, '.'), 7) AS user_ts,
						strftime('%Y-%m-%d %H:%M:%f', ts, 'localtime') AS ts
					FROM foglamp.)";

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
			if (!jsonModifiers(document, sql))
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
unsigned long rowidLimit = 0, rowidMin;
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
		     "select max(rowid) from foglamp.readings;",
	  	     rowidCallback,
		     &rowidLimit,
		     &zErrMsg);

		if (rc != SQLITE_OK)
		{
 			raiseError("purge - phaase 0, fetching rowid limit ", zErrMsg);
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
		oldest.append("SELECT (strftime('%s','now', 'localtime') - strftime('%s', MIN(user_ts)))/360 FROM foglamp.readings where rowid <= ");
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
		 * Refine rowid limit to just those rows older than age hours
		 */
		char *zErrMsg = NULL;
		int rc;
		SQLBuffer sqlBuffer;
		sqlBuffer.append("select max(rowid) from foglamp.readings where user_ts < datetime('now' , '-");
		sqlBuffer.append(age);
		sqlBuffer.append(" hours', 'localtime')");
		if ((flags & 0x01) == 0x01)	// Don't delete unsent rows
		{
			sqlBuffer.append(" AND id < ");
			sqlBuffer.append(sent);
		}
		sqlBuffer.append(';');
		const char *query = sqlBuffer.coalesce();
		rc = SQLexec(dbHandle,
		     query,
	  	     rowidCallback,
		     &rowidLimit,
		     &zErrMsg);
		delete query;

		if (rowidLimit == 0)
		{
 			logger->info("No data to purge");
			return 0;
		}

		if (rc != SQLITE_OK)
		{
 			raiseError("purge - phaase 0, fetching rowid limit ", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
		rc = SQLexec(dbHandle,
		     "select min(rowid) from foglamp.readings;",
	  	     rowidCallback,
		     &rowidMin,
		     &zErrMsg);

		if (rc != SQLITE_OK)
		{
 			raiseError("purge - phaase 0, fetching rowid limit ", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
	}
	logger->info("Purge collecting unsent row count");
	if ((flags & 0x01) == 0)
	{
		// Get number of unsent rows we are about to remove
		SQLBuffer unsentBuffer;
		unsentBuffer.append("SELECT count(ROWID) FROM foglamp.readings WHERE  user_ts < datetime('now', '-");
		unsentBuffer.append(age);
		unsentBuffer.append(" hours', 'localtime') AND id > ");
		unsentBuffer.append(sent);
		unsentBuffer.append(" AND rowid <= ");
		unsentBuffer.append(rowidLimit);
		unsentBuffer.append(';');
		const char *query = unsentBuffer.coalesce();
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
 			raiseError("purge - phaase 2", zErrMsg);
			sqlite3_free(zErrMsg);
			return 0;
		}
	}
	
	unsigned int deletedRows = 0;
	char *zErrMsg = NULL;
	unsigned int rowsAffected;
	logger->info("Purge about to delete the readings %ld to %ld in blocks", rowidMin, rowidLimit);
	while (rowidMin < rowidLimit)
	{
		blocks++;
		rowidMin += PURGE_DELETE_BLOCK_SIZE;
		if (rowidMin > rowidLimit)
		{
			rowidMin = rowidLimit;
		}
		SQLBuffer sql;
		sql.append("DELETE FROM foglamp.readings WHERE rowid <= ");
		sql.append(rowidMin);
		sql.append(';');
		const char *query = sql.coalesce();
		logSQL("ReadingsPurge", query);
		// Exec DELETE query: no callback, no resultset
		int rc = SQLexec(dbHandle,
			     query,
			     NULL,
			     NULL,
			     &zErrMsg);


		if (rc != SQLITE_OK)
		{
			raiseError("purge - phase 3", zErrMsg);
			sqlite3_free(zErrMsg);
			// Release memory for 'query' var
			delete[] query;
			return 0;
		}

		// Get db changes
		rowsAffected = sqlite3_changes(dbHandle);
		deletedRows += rowsAffected;
		Logger::getLogger()->info("Purge delete block of %d readings", rowsAffected);

		// Sleep for a while to release locks on the database if anybody is waiting
		if (m_queuing)
		{
			std::this_thread::sleep_for(std::chrono::milliseconds(PURGE_SLEEP_MS));
		}
	} while (rowidMin  < rowidLimit);

	SQLBuffer retainedBuffer;
	retainedBuffer.append("SELECT count(ROWID) FROM foglamp.readings WHERE id > ");
	retainedBuffer.append(sent);
	retainedBuffer.append(';');
	const char *query_r = retainedBuffer.coalesce();
	logSQL("ReadingsPurge", query_r);
	int retained_unsent = 0;

	// Exec query and get result in 'retained_unsent' via 'countCallback'
	int rc = SQLexec(dbHandle,
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
 		raiseError("purge - phase 4", zErrMsg);
		sqlite3_free(zErrMsg);
	}

	logger->info("Got retained unsetn row count");

	int readings_num = 0;
	// Exec query and get result in 'readings_num' via 'countCallback'
	rc = SQLexec(dbHandle,
		     "SELECT count(ROWID) FROM foglamp.readings where asset_code = asset_code",
		     countCallback,
	  	     &readings_num,
		     &zErrMsg);

	if (rc == SQLITE_OK)
	{
		numReadings = readings_num;
	}
	else
	{
 		raiseError("purge - phase 5", zErrMsg);
		sqlite3_free(zErrMsg);
	}

	ostringstream convert;

	convert << "{ \"removed\" : " << deletedRows << ", ";
	convert << " \"unsentPurged\" : " << unsentPurged << ", ";
	convert << " \"unsentRetained\" : " << unsentRetained << ", ";
    	convert << " \"readings\" : " << numReadings << " }";

	result = convert.str();

	gettimeofday(&endTv, NULL);
	unsigned long duration = (1000000 * (endTv.tv_sec - startTv.tv_sec)) + endTv.tv_usec - startTv.tv_usec;
	logger->info("Purge process complete in %d blocks after %lduS", blocks, duration);

	return deletedRows;
}

/**
 * Process the aggregate options and return the columns to be selected
 */
bool Connection::jsonAggregates(const Value& payload,
				const Value& aggregates,
				SQLBuffer& sql,
				SQLBuffer& jsonConstraint)
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
				sql.append(col);
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
				sql.append((*itr)["column"].GetString());
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
				applyColumnDateFormat(grp["format"].GetString(),
						      grp["column"].GetString(),
						      new_format);
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
					// Use JulianDay, with microseconds
					sql.append(tb["size"].GetString());
					sql.append(" * round(");
					sql.append("strftime('%J', ");
					sql.append(tb["timestamp"].GetString());
					sql.append(") / ");
					sql.append(tb["size"].GetString());
					sql.append(", 6)");
				}
				else
				{
					sql.append(tb["timestamp"].GetString());
				}
				sql.append(")");
			}
			else
			{
				/**
				 * No date format found: we should return an error.
				 * Note: currently if input Json payload has no 'result' member
				 * raiseError() results in no data being sent to the client
				 * For the time being we just use JulianDay, with microseconds
				 */
				sql.append(", datetime(");
				if (tb.HasMember("size"))
				{
					sql.append(tb["size"].GetString());
					sql.append(" * round(");
				}
				// Use JulianDay, with microseconds
				sql.append("strftime('%J', ");
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
				sql.append(")");
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
			 * - we use JulianDay in order to get milliseconds.
			 */
			sql.append("strftime('%J', ");
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

			sql.append(")");
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
 * Process the modifers for limit, skip, sort and group
 */
bool Connection::jsonModifiers(const Value& payload, SQLBuffer& sql)
{
	if (payload.HasMember("timebucket") && payload.HasMember("sort"))
	{
		raiseError("query modifiers",
			   "Sort and timebucket modifiers can not be used in the same payload");
		return false;
	}

	if (payload.HasMember("group"))
	{
		sql.append(" GROUP BY ");
		if (payload["group"].IsObject())
		{
			const Value& grp = payload["group"];
			if (grp.HasMember("format"))
			{
				/**
				 * SQLite 3 date format is limited.
				 * Handle all availables formats here.
				 */
				string new_format;
				applyColumnDateFormat(grp["format"].GetString(),
						      grp["column"].GetString(),
						      new_format);
				// Add the formatted column or use it as is
				sql.append(new_format);
			}
		}
		else
		{
			sql.append(payload["group"].GetString());
		}
	}

	if (payload.HasMember("sort"))
	{
		sql.append(" ORDER BY ");
		const Value& sortBy = payload["sort"];
		if (sortBy.IsObject())
		{
			if (! sortBy.HasMember("column"))
			{
				raiseError("Select sort", "Missing property \"column\"");
				return false;
			}
			sql.append(sortBy["column"].GetString());
			sql.append(' ');
			if (! sortBy.HasMember("direction"))
			{
				sql.append("ASC");
			}
			else
			{
				sql.append(sortBy["direction"].GetString());
			}
		}
		else if (sortBy.IsArray())
		{
			int index = 0;
			for (Value::ConstValueIterator itr = sortBy.Begin(); itr != sortBy.End(); ++itr)
			{
				if (!itr->IsObject())
				{
					raiseError("select sort",
						   "Each element in the sort array must be an object");
					return false;
				}
				if (! itr->HasMember("column"))
				{
					raiseError("Select sort", "Missing property \"column\"");
					return false;
				}
				if (index)
				{
					sql.append(", ");
				}
				index++;
				sql.append((*itr)["column"].GetString());
				sql.append(' ');
				if (! itr->HasMember("direction"))
				{
					 sql.append("ASC");
				}
				else
				{
					sql.append((*itr)["direction"].GetString());
				}
			}
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
		if (payload.HasMember("group"))
		{
			sql.append(", ");
		}
		else
		{
			sql.append(" GROUP BY ");
		}

		// Use DateTime Y-m-d H:M:S from JulianDay
                sql.append("datetime(strftime('%J', ");
                sql.append(tb["timestamp"].GetString());
                sql.append("))");

		sql.append(" ORDER BY ");

		// Use DateTime Y-m-d H:M:S fromt JulianDay
                sql.append("datetime(strftime('%J', ");
                sql.append(tb["timestamp"].GetString());
                sql.append("))");

		sql.append(" DESC");
	}

	if (payload.HasMember("limit"))
	{
		if (!payload["limit"].IsInt())
		{
			raiseError("limit",
				   "Limit must be specfied as an integer");
			return false;
		}
		sql.append(" LIMIT ");
		try {
			sql.append(payload["limit"].GetInt());
		} catch (exception e) {
			raiseError("limit",
				   "Bad value for limit parameter: %s",
				   e.what());
			return false;
		}
	}

	// OFFSET must go after LIMIT
	if (payload.HasMember("skip"))
	{
		// Add no limits
		if (!payload.HasMember("limit"))
		{
			sql.append(" LIMIT -1");
		}

		if (!payload["skip"].IsInt())
		{
			raiseError("skip",
				   "Skip must be specfied as an integer");
			return false;
		}
		sql.append(" OFFSET ");
		sql.append(payload["skip"].GetInt());
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
 * This routine uses SQLit3 JSON1 extension functions
 */
bool Connection::returnJson(const Value& json,
			    SQLBuffer& sql,
			    SQLBuffer& jsonConstraint)
{
	if (! json.IsObject())
	{
		raiseError("retrieve", "The json property must be an object");
		return false;
	}
	if (!json.HasMember("column"))
	{
		raiseError("retrieve", "The json property is missing a column property");
		return false;
	}
	// Call JSON1 SQLite3 extension routine 'json_extract'
	// json_extract(field, '$.key1.key2') AS value
	sql.append("json_extract(");
	sql.append(json["column"].GetString());
	sql.append(", '$.");
	if (!json.HasMember("properties"))
	{
		raiseError("retrieve", "The json property is missing a properties property");
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
			if (prev.length())
			{
				jsonConstraint.append(prev);
				jsonConstraint.append(".");
			}
			field++;
			// Append Json field for query
			sql.append(itr->GetString());
			prev = itr->GetString();
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
	sql.append("') ");

	return true;
}

/**
 * Remove whitespace at both ends of a string
 */
char *Connection::trim(char *str)
{
char *ptr;

	while (*str && *str == ' ')
		str++;

	ptr = str + strlen(str) - 1;
	while (ptr > str && *ptr == ' ')
	{
		*ptr = 0;
		ptr--;
	}
	return str;
}

/**
 * Raise an error to return from the plugin
 */
void Connection::raiseError(const char *operation, const char *reason, ...)
{
ConnectionManager *manager = ConnectionManager::getInstance();
char	tmpbuf[512];

	va_list ap;
	va_start(ap, reason);
	vsnprintf(tmpbuf, sizeof(tmpbuf), reason, ap);
	va_end(ap);
	Logger::getLogger()->error("SQLite3 storage plugin raising error: %s", tmpbuf);
	manager->setError(operation, tmpbuf, false);
}

/**
 * Return the sie of a given table in bytes
 */
long Connection::tableSize(const string& table)
{
SQLBuffer buf;

 	raiseError("tableSize", "Not available in SQLite3 storage plugin");
	return -1;
}


/**
 * char* escape routine
 */
const char *Connection::escape(const char *str)
{
static char *lastStr = NULL;
const char    *p1;
char *p2;

    if (strchr(str, '\'') == NULL)
    {
        return str;
    }

    if (lastStr !=  NULL)
    {
        free(lastStr);
    }
    lastStr = (char *)malloc(strlen(str) * 2);

    p1 = str;
    p2 = lastStr;
    while (*p1)
    {
        if (*p1 == '\'')
        {
            *p2++ = '\'';
            *p2++ = '\'';
            p1++;
        }
        else
        {
            *p2++ = *p1++;
        }
    }
    *p2 = 0;
    return lastStr;
}

/**
 * String escape routine
 */
const string Connection::escape(const string& str)
{
char    *buffer;
const char    *p1;
char  *p2;
string  newString;

    if (str.find_first_of('\'') == string::npos)
    {
        return str;
    }

    buffer = (char *)malloc(str.length() * 2);

    p1 = str.c_str();
    p2 = buffer;
    while (*p1)
    {
        if (*p1 == '\'')
        {
            *p2++ = '\'';
            *p2++ = '\'';
            p1++;
        }
        else
        {
            *p2++ = *p1++;
        }
    }
    *p2 = 0;
    newString = string(buffer);
    free(buffer);
    return newString;
}

/**
 * Optionally log SQL statement execution
 *
 * @param	tag	A string tag that says why the SQL is being executed
 * @param	stmt	The SQL statement itself
 */
void Connection::logSQL(const char *tag, const char *stmt)
{
	if (m_logSQL)
	{
		Logger::getLogger()->info("%s: %s", tag, stmt);
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
int Connection::SQLexec(sqlite3 *db, const char *sql, int (*callback)(void*,int,char**,char**),
  			void *cbArg, char **errmsg)
{
int retries = 0, rc;

	do {
#if DO_PROFILE
		ProfileItem *prof = new ProfileItem(sql);
#endif
		rc = sqlite3_exec(db, sql, callback, cbArg, errmsg);
#if DO_PROFILE
		prof->complete();
		profiler.insert(prof);
#endif
		retries++;
		if (rc == SQLITE_LOCKED || rc == SQLITE_BUSY)
		{
			m_qMutex.lock();
			m_queuing++;
#if DO_PROFILE_RETRIES
			if (maxQueue < m_queuing)
				maxQueue = m_queuing;
#endif
			m_qMutex.unlock();
			usleep(retries * RETRY_BACKOFF);	// sleep retries milliseconds
			m_qMutex.lock();
			m_queuing--;
			m_qMutex.unlock();
		}
	} while (retries < MAX_RETRIES && (rc == SQLITE_LOCKED || rc == SQLITE_BUSY));
#if DO_PROFILE_RETRIES
	retryStats[retries-1]++;
	if (++numStatements > RETRY_REPORT_THRESHOLD - 1)
	{
		numStatements = 0;
		Logger *log = Logger::getLogger();
		log->info("Storage layer statement retry profile");
		for (int i = 0; i < MAX_RETRIES-1; i++)
		{
			log->info("%2d: %d", i, retryStats[i]);
			retryStats[i] = 0;
		}
		log->info("Too many retries: %d", retryStats[MAX_RETRIES-1]);
		retryStats[MAX_RETRIES-1] = 0;
		log->info("Maximum retry queue length: %d", maxQueue);
		maxQueue = 0;
	}
#endif

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

int Connection::SQLstep(sqlite3_stmt *statement)
{
int retries = 0, rc;

	do {
#if DO_PROFILE
		ProfileItem *prof = new ProfileItem(sqlite3_sql(statement));
#endif
		rc = sqlite3_step(statement);
#if DO_PROFILE
		prof->complete();
		profiler.insert(prof);
#endif
		retries++;
		if (rc == SQLITE_LOCKED || rc == SQLITE_BUSY)
		{
			usleep(retries * RETRY_BACKOFF);	// sleep retries milliseconds
		}
	} while (retries < MAX_RETRIES && (rc == SQLITE_LOCKED || rc == SQLITE_BUSY));
#if DO_PROFILE_RETRIES
	retryStats[retries-1]++;
	if (++numStatements > 1000)
	{
		numStatements = 0;
		Logger *log = Logger::getLogger();
		log->info("Storage layer statement retry profile");
		for (int i = 0; i < MAX_RETRIES-1; i++)
		{
			log->info("%2d: %d", i, retryStats[i]);
			retryStats[i] = 0;
		}
		log->info("Too many retries: %d", retryStats[MAX_RETRIES-1]);
		retryStats[MAX_RETRIES-1] = 0;
	}
#endif

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
