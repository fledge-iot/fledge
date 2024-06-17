/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <connection.h>
#include <connection_manager.h>
#include <sql_buffer.h>
#include <iostream>
#include <libpq-fe.h>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/error.h"
#include "rapidjson/error/en.h"
#include <string>
#include <vector>
#include <stdarg.h>
#include <stdlib.h>
#include <sstream>
#include <logger.h>
#include <time.h>
#include <algorithm>
#include <math.h>
#include <sys/time.h>

#include "json_utils.h"

#include <iostream>
#include <chrono>
#include <thread>

using namespace std;
using namespace rapidjson;

static time_t connectErrorTime = 0;
#define CONNECT_ERROR_THRESHOLD		5*60	// 5 minutes
#define MSG_LEN 5000

//
// Used for the purge operation - start
//
#define PURGE_DELETE_BLOCK_SIZE	    10000
#define MIN_PURGE_DELETE_BLOCK_SIZE	1000
#define MAX_PURGE_DELETE_BLOCK_SIZE	10000

#define TARGET_PURGE_BLOCK_DEL_TIME	(70*1000) 	// 70 msec
#define PURGE_BLOCK_SZ_GRANULARITY	5 	// 5 rows
#define RECALC_PURGE_BLOCK_SIZE_NUM_BLOCKS	30	// recalculate purge block size after every 30 blocks

#define START_TIME std::chrono::high_resolution_clock::time_point t1 = std::chrono::high_resolution_clock::now();
#define END_TIME std::chrono::high_resolution_clock::time_point t2 = std::chrono::high_resolution_clock::now(); \
				 auto usecs = std::chrono::duration_cast<std::chrono::microseconds>( t2 - t1 ).count();
//
// Used for the purge operation - end


#define LEN_BUFFER_DATE 100
// Format timestamp having microseconds
#define F_DATEH24_US    	"YYYY-MM-DD HH24:MI:SS.US"

static int purgeBlockSize = PURGE_DELETE_BLOCK_SIZE;

const vector<string>  pg_column_reserved_words = {
	"user"
};

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
		    strcmp(agg["operation"].GetString(), "all") == 0)
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
		if (bucket.HasMember("format") && size >= 1)
		{
			sql.append("to_char(");
			sql.append("\"");
			sql.append("timestamp");
			sql.append("\"");
			sql.append(", '");
			sql.append(bucket["format"].GetString());
			sql.append("')");
		}
		else
		{
			if (size < 1)
			{
				// sub-second granularity to time bucket size:
				// force output formatting with microseconds
				sql.append("to_char(");
				sql.append("\"");
				sql.append("timestamp");
				sql.append("\"");
				sql.append(", '");
				sql.append("YYYY-MM-DD HH24:MI:SS.US");
				sql.append("')");
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
	sql.append(", (('{' || string_agg('\"' || x || '\" : ' || resd, ', ') || '}')::jsonb) AS reading ");

	// subquery
	sql.append("FROM ( SELECT  x, asset_code, max(timestamp) AS timestamp, ");
	// Add mon
	sql.append("'{\"min\" : ' || min((reading->>x)::float) || ', ");
	// Add max
	sql.append("\"max\" : ' || max((reading->>x)::float) || ', ");
	// Add avg
	sql.append("\"average\" : ' || avg((reading->>x)::float) || ', ");
	// Add count
	sql.append("\"count\" : ' || count(reading->>x) || ', ");
	// Add sum
	sql.append("\"sum\" : ' || sum((reading->>x)::float) || '}' AS resd ");

	// subquery
	sql.append("FROM ( SELECT asset_code, ");
	sql.append(timeColumn);
	sql.append(", to_timestamp(");

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
	if (size != 1)
	{
		sql.append(size_format);
		if (size > 1)
		{
			sql.append(" * round(extract(epoch from ");
		}
		else
		{
			sql.append(" * round((extract(epoch from ");
		}
		sql.append(timeColumn);
		sql.append(" ) / ");
		sql.append(size_format);
		sql.append(')');
		if (size > 1)
		{
			sql.append(')');
		}
		else
		{
			sql.append("::numeric, 6))");
		}
	}
	else
	{
		sql.append(" round(extract(epoch from ");
		sql.append(timeColumn);
		sql.append(") / 1)) ");
	}
	sql.append(" AS \"timestamp\", reading, ");

	// Get all datapoints in 'reading' field
	sql.append("jsonb_object_keys(reading) AS x FROM fledge.readings ");

	// Add where condition
	sql.append("WHERE ");

	vector<string>  asset_codes;
	if (!jsonWhereClause(payload["where"], sql, asset_codes))
	{
		raiseError("retrieve", "aggregateQuery: failure while building WHERE clause");
		return false;
	}

	// sort results
	sql.append(" ORDER BY ");
	sql.append(timeColumn);
	sql.append(" DESC) tmp ");

	// Add group by
	sql.append("GROUP BY x, asset_code, ");

	sql.append("round(extract(epoch from ");
	sql.append(timeColumn);
	sql.append(") / ");
	if (size != 1)
	{
		sql.append(size_format);
	}
	else
	{
		sql.append('1'); 
	}
	sql.append(") ");

	// sort results
	sql.append("ORDER BY timestamp DESC) tbl ");

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

	logSQL("CommonRetrieve", query);

	PGresult *res = PQexec(dbConnection, query);

	delete[] query;

	if (PQresultStatus(res) == PGRES_TUPLES_OK)
	{
		mapResultSet(res, resultSet);
		PQclear(res);
		return true;
	}
	char *SQLState = PQresultErrorField(res, PG_DIAG_SQLSTATE);
	if (!strcmp(SQLState, "22P02")) // Conversion error
	{
		raiseError("retrieve", "Unable to convert data to the required type");
	}
	else
	{
		raiseError("retrieve", PQerrorMessage(dbConnection));
	}
	PQclear(res);
	return false;
}

/**
 * Create a database connection
 */
Connection::Connection() : m_maxReadingRows(INSERT_ROW_LIMIT)
{
	const char *defaultConninfo = "dbname = fledge";
	char *connInfo = NULL;
	
	if ((connInfo = getenv("DB_CONNECTION")) == NULL)
	{
		connInfo = (char *)defaultConninfo;
	}
 
	/* Make a connection to the database */
	dbConnection = PQconnectdb(connInfo);

	/* Check to see that the backend connection was successfully made */
	if (PQstatus(dbConnection) != CONNECTION_OK)
	{
		if (connectErrorTime == 0 || (time(0) - connectErrorTime > CONNECT_ERROR_THRESHOLD))
		{
			Logger::getLogger()->error("Failed to connect to the database: %s",
				PQerrorMessage(dbConnection));
			connectErrorTime = time(0);
		}
		throw runtime_error("Unable to connect to PostgreSQL database");
	}
	
	logSQL("Set", "session time zone 'UTC' ");
	PGresult *res = PQexec(dbConnection, " set session time zone 'UTC' ");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		Logger::getLogger()->error("set session time zone failed: %s", PQerrorMessage(dbConnection));
	}
	PQclear(res);
}

/**
 * Destructor for the database connection. Close the connection
 * to Postgres
 */
Connection::~Connection()
{
	PQfinish(dbConnection);
}

/**
 * Perform a query against a common table
 *
 */
bool Connection::retrieve(const string& schema,
			const string& table,
			const string& condition,
			string& resultSet)
{
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
SQLBuffer	sql;
SQLBuffer	jsonConstraints;	// Extra constraints to add to where clause
vector<string>  asset_codes;

	try {
		if (condition.empty())
		{
			sql.append("SELECT * FROM ");
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
				if (!jsonAggregates(document, document["aggregate"], sql, jsonConstraints, false))
				{
					return false;
				}
				sql.append(" FROM ");
			}
			else if (document.HasMember("join"))
                        {
                                sql.append("SELECT ");
                                selectColumns(document, sql, 0);
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
						sql.append("\"");
						sql.append(itr->GetString());
						sql.append("\"");
					}
					else
					{
						if (itr->HasMember("column"))
						{
							if (! (*itr)["column"].IsString())
							{
								raiseError("rerieve", "column must be a string");
								return false;
							}
							if (itr->HasMember("format"))
							{
								if (! (*itr)["format"].IsString())
								{
									raiseError("rerieve", "format must be a string");
									return false;
								}
								sql.append("to_char(");
								sql.append("\"");
								sql.append((*itr)["column"].GetString());
								sql.append("\"");
								sql.append(", '");
								sql.append((*itr)["format"].GetString());
								sql.append("')");
							}
							else if (itr->HasMember("timezone"))
							{
								if (! (*itr)["timezone"].IsString())
								{
									raiseError("rerieve", "timezone must be a string");
									return false;
								}
								sql.append("\"");
								sql.append((*itr)["column"].GetString());
								sql.append("\"");
								sql.append(" AT TIME ZONE '");
								sql.append((*itr)["timezone"].GetString());
								sql.append("' ");
							}
							else
							{
								sql.append("\"");
								sql.append((*itr)["column"].GetString());
								sql.append("\"");
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
							raiseError("retrieve", "return object must have either a column or json property");
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
				sql.append(" * FROM ");
			}

			if (document.HasMember("join"))
                        {
                                sql.append(" FROM ");
                                sql.append(table);
                                sql.append(" t0");
                                appendTables(schema, document, sql, 1);
                        }
                        else
                        {
                                sql.append(table);
                        }
			if (document.HasMember("where"))
			{
				sql.append(" WHERE ");

				if (document.HasMember("join"))
                                {
                                        if (!jsonWhereClause(document["where"], sql, asset_codes, false, "t0."))
                                        {
                                                return false;
                                        }

                                        // Now and the join condition itself
                                        string col0, col1;
                                        const Value& join = document["join"];
                                        if (join.HasMember("on") && join["on"].IsString())
                                        {
                                                col0 = join["on"].GetString();
                                        }
                                        else
                                        {

                                                raiseError("rerieve", "Missing on item");
                                                return false;
                                        }
                                        if (join.HasMember("table"))
                                        {
                                                const Value& table = join["table"];
                                                if (table.HasMember("column") && table["column"].IsString())
                                                {
                                                        col1 = table["column"].GetString();
                                                }
                                                else
                                                {
                                                        raiseError("QueryTable", "Missing column in join table");
                                                        return false;
                                                }
                                        }
                                        sql.append(" AND t0.");
                                        sql.append(col0);
                                        sql.append(" = t1.");
                                        sql.append(col1);
                                        sql.append(" ");
                                        if (join.HasMember("query") && join["query"].IsObject())
                                        {
                                                sql.append("AND  ");
                                                const Value& query = join["query"];
                                                processJoinQueryWhereClause(query, sql, asset_codes, 1);
                                        }
                                }
				else if (document.HasMember("where"))
				{
					if (!jsonWhereClause(document["where"], sql, asset_codes))
					{
						return false;
					}
				}
				else
				{
					raiseError("retrieve", "JSON does not contain where clause");
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
		logSQL("CommonRetrieve", query);

		PGresult *res = PQexec(dbConnection, query);
		delete[] query;
		if (PQresultStatus(res) == PGRES_TUPLES_OK)
		{
			mapResultSet(res, resultSet);
			PQclear(res);

			return true;
		}
		char *SQLState = PQresultErrorField(res, PG_DIAG_SQLSTATE);
		if (!strcmp(SQLState, "22P02"))	// Conversion error
		{
			raiseError("retrieve", "Unable to convert data to the required type");
		}
		else
		{
			raiseError("retrieve", PQerrorMessage(dbConnection));
		}
		PQclear(res);
		return false;
	} catch (exception e) {
		raiseError("retrieve", "Internal error: %s", e.what());
	}
	return false;
}

/**
 * Perform a query against the readings table
 *
 */
bool Connection::retrieveReadings(const string& condition, string& resultSet)
{
	Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
	SQLBuffer	sql;
	SQLBuffer	jsonConstraints;	// Extra constraints to add to where clause

	const string table = "readings";

	try {
		if (condition.empty())
		{
			const char *sql_cmd = R"(
					SELECT
						id,
						asset_code,
						reading,
						to_char(user_ts, ')" F_DATEH24_US R"(') as user_ts,
						to_char(ts, ')" F_DATEH24_US R"(') as ts
					FROM fledge.)";

			sql.append(sql_cmd);
			sql.append(table);
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
							sql.append("to_char(user_ts, '" F_DATEH24_US "') as user_ts");
						}
						else if (strcmp(itr->GetString() ,"ts") == 0)
						{
							// Display without TZ expression and microseconds also
							sql.append("to_char(ts, '" F_DATEH24_US "') as ts");
						}
						else
						{
							sql.append("\"");
							sql.append(itr->GetString());
							sql.append("\"");
						}
					}
					else
					{
						if (itr->HasMember("column"))
						{
							if (! (*itr)["column"].IsString())
							{
								raiseError("rerieve", "column must be a string");
								return false;
							}
							if (itr->HasMember("format"))
							{
								if (! (*itr)["format"].IsString())
								{
									raiseError("rerieve", "format must be a string");
									return false;
								}
								sql.append("to_char(");
								sql.append("\"");
								sql.append((*itr)["column"].GetString());
								sql.append("\"");
								sql.append(", '");
								sql.append((*itr)["format"].GetString());
								sql.append("')");
							}
							else if (itr->HasMember("timezone"))
							{
								if (! (*itr)["timezone"].IsString())
								{
									raiseError("rerieve", "timezone must be a string");
									return false;
								}
								sql.append("\"");
								sql.append((*itr)["column"].GetString());
								sql.append("\"");
								sql.append(" AT TIME ZONE '");
								sql.append((*itr)["timezone"].GetString());
								sql.append("' ");
							}
							else
							{
								if (strcmp((*itr)["column"].GetString() ,"user_ts") == 0)
								{
									// Display without TZ expression and microseconds also
									sql.append("to_char(user_ts, '" F_DATEH24_US "')");
									if (! itr->HasMember("alias"))
									{
										sql.append(" AS \"user_ts\" ");
									}
								}
								else if (strcmp((*itr)["column"].GetString() ,"ts") == 0)
								{
									// Display without TZ expression and microseconds also
									sql.append("to_char(ts, '" F_DATEH24_US "')");
									if (! itr->HasMember("alias"))
									{
										sql.append(" AS \"ts\" ");
									}
								}
								else
								{
									sql.append("\"");
									sql.append((*itr)["column"].GetString());
									sql.append("\"");
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
							raiseError("retrieve", "return object must have either a column or json property");
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
						to_char(user_ts, ')" F_DATEH24_US R"(') as user_ts,
						to_char(ts, ')" F_DATEH24_US R"(') as ts
					FROM fledge.)";

				sql.append(sql_cmd);
			}
			sql.append(table);
			if (document.HasMember("where"))
			{
				sql.append(" WHERE ");

				if (document.HasMember("where"))
				{
					vector<string>  asset_codes;
					if (!jsonWhereClause(document["where"], sql, asset_codes))
					{
						return false;
					}
				}
				else
				{
					raiseError("retrieve", "JSON does not contain where clause");
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
		logSQL("CommonRetrieve", query);

		PGresult *res = PQexec(dbConnection, query);
		delete[] query;
		if (PQresultStatus(res) == PGRES_TUPLES_OK)
		{
			mapResultSet(res, resultSet);
			PQclear(res);
			return true;
		}
		char *SQLState = PQresultErrorField(res, PG_DIAG_SQLSTATE);
		if (!strcmp(SQLState, "22P02"))	// Conversion error
		{
			raiseError("retrieve", "Unable to convert data to the required type");
		}
		else
		{
			raiseError("retrieve", PQerrorMessage(dbConnection));
		}
		PQclear(res);
		return false;
	} catch (exception e) {
		raiseError("retrieve", "Internal error: %s", e.what());
	}
	return false;
}


/**
 * Insert data into a table
 */
int Connection::insert(const std::string& table, const std::string& data)
{
SQLBuffer	sql;
Document	document;
ostringstream convert;
std::size_t arr = data.find("inserts");

	// Check first the 'inserts' property in JSON data
	bool stdInsert = (arr == std::string::npos || arr > 8);
	// If input data is not an array of iserts
	// create an array with one element
	if (stdInsert)
	{
		convert << "{ \"inserts\" : [ ";
		convert << data;
		convert << " ] }";
	}

	if (document.Parse(stdInsert ? convert.str().c_str() : data.c_str()).HasParseError())
	{
		raiseError("insert", "Failed to parse JSON payload\n");
		return -1;
	}

	// Get the array with row(s)
	Value &inserts = document["inserts"];
	if (!inserts.IsArray())
	{
		raiseError("insert", "Payload is missing the inserts array");
		return -1;
	}

	// Number of inserts
	int ins = 0;

	// Iterate through insert array
	for (Value::ConstValueIterator iter = inserts.Begin();
					iter != inserts.End();
					++iter)
	{
		if (!iter->IsObject())
		{
			raiseError("insert",
				   "Each entry in the insert array must be an object");
			return -1;
		}

		int col = 0;
		SQLBuffer values;

	 	sql.append("INSERT INTO ");
		sql.append(table);
		sql.append(" (");

		for (Value::ConstMemberIterator itr = (*iter).MemberBegin();
						itr != (*iter).MemberEnd();
						++itr)
		{
			// Append column name
			if (col)
			{
				sql.append(", ");
			}
			string field_name = double_quote_reserved_column_name(itr->name.GetString());
			sql.append(field_name);

			// Append column value
			if (col)
			{
				values.append(", ");
			}
			if (itr->value.IsString())
			{
				const char *str = itr->value.GetString();
				// Check if the string is a function
				if (isFunction(str))
				{
					values.append(str);
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
		sql.append(") VALUES (");
		const char *vals = values.coalesce();
		sql.append(vals);
		delete[] vals;
		sql.append(");");

		// Increment row count
		ins++;
	}

	const char *query = sql.coalesce();
	logSQL("CommonInsert", query);
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return atoi(PQcmdTuples(res));
	}
 	raiseError("insert", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
}

/**
 * Perform an update against a common table
 *
 */
int Connection::update(const string& table, const string& payload)
{
// Default template parameter uses UTF8 and MemoryPoolAllocator.
Document	document;
SQLBuffer	sql;

	int 	row = 0;
	ostringstream convert;
	bool 	allowZero = false;

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
		
		int i=0;
		for (Value::ConstValueIterator iter = updates.Begin(); iter != updates.End(); ++iter,++i)
		{
			if (!iter->IsObject())
			{
				raiseError("update",
					   "Each entry in the update array must be an object");
				return -1;
			}
			sql.append("UPDATE ");
			sql.append(table);
			sql.append(" SET ");

			int 	col = 0;
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
					sql.append("\"");
					sql.append(itr->name.GetString());
					sql.append("\"");
					sql.append(" = ");
		 
					if (itr->value.IsString())
					{
						const char *str = itr->value.GetString();
						// Check if the string is a function
						if (isFunction(str))
						{
							sql.append(str);
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
					// Handle JSON value null: "item" : null
					else if (itr->value.IsNull())
					{
						sql.append("NULL");
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
					sql.append("\"");
					sql.append((*itr)["column"].GetString());
					sql.append("\"");
					sql.append(" = ");
					sql.append("\"");
					sql.append((*itr)["column"].GetString());
					sql.append("\"");
					sql.append(' ');
					sql.append((*itr)["operator"].GetString());
					sql.append(' ');
					const Value& value = (*itr)["value"];
		 
					if (value.IsString())
					{
						const char *str = value.GetString();
						// Check if the string is a function
						if (isFunction(str))
						{
							sql.append(str);
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
						sql.append(escape(buffer.GetString()));
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
					sql.append("\"");
					sql.append((*itr)["column"].GetString());
					sql.append("\"");
					sql.append(" = jsonb_set(");
					sql.append((*itr)["column"].GetString());
					sql.append(", '{");

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
							sql.append(',');
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
					sql.append("}', ");
					const Value& value = (*itr)["value"];
		 
					if (value.IsString())
					{
						const char *str = value.GetString();
						// Check if the string is a function
						if (isFunction(str))
						{
							sql.append("'\"");
							sql.append(str);
							sql.append("\"'");
						}
						else
						{
							StringBuffer buffer;
							Writer<StringBuffer> writer(buffer);
							value.Accept(writer);
							sql.append("'\"");
							sql.append(escape_double_quotes(escape(JSONunescape(buffer.GetString()))));
							sql.append("\"'");
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

						std::string buffer_escaped = "\"";
						buffer_escaped.append(escape_double_quotes(buffer.GetString()));
						buffer_escaped.append( "\"");

						sql.append('\'');
						sql.append(buffer_escaped);
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
				vector<string>  asset_codes;
				if (!jsonWhereClause((*iter)["condition"], sql, asset_codes))
				{
					return false;
				}
			}
			else if ((*iter).HasMember("where"))
			{
				vector<string>  asset_codes;
				sql.append(" WHERE ");
				if (!jsonWhereClause((*iter)["where"], sql, asset_codes))
				{
					return false;
				}
			}
			if (iter->HasMember("modifier") && (*iter)["modifier"].IsArray())
			{
				const Value& modifier = (*iter)["modifier"];
				for (Value::ConstValueIterator modifiers = modifier.Begin(); modifiers != modifier.End(); ++modifiers)
                		{
					if (modifiers->IsString())
					{
						string mod = modifiers->GetString();
						if (mod.compare("allowzero") == 0)
						{
							allowZero = true;
						}
					}
				}
			}
		sql.append(';');
		}
	}

	const char *query = sql.coalesce();
	logSQL("CommonUpdate", query);
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		int rowsUpdated = atoi(PQcmdTuples(res));
		if (rowsUpdated == 0 && allowZero == false)
		{
 			raiseError("update", "No rows where updated");
			return -1;
		}
		PQclear(res);
		return atoi(PQcmdTuples(res));
	}
 	raiseError("update", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
}

/**
 * Perform a delete against a common table
 *
 */
int Connection::deleteRows(const string& table, const string& condition)
{
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
SQLBuffer	sql;
 
	sql.append("DELETE FROM ");
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
				vector<string>  asset_codes;
				if (!jsonWhereClause(document["where"], sql, asset_codes))
				{
					return -1;
				}
			}
			else
			{
				raiseError("delete", "JSON does not contain where clause");
				return -1;
			}
		}
	}
	sql.append(';');

	const char *query = sql.coalesce();
	logSQL("CommonDelete", query);
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return atoi(PQcmdTuples(res));
	}
 	raiseError("delete", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
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

	const char *head = "INSERT INTO fledge.readings ( user_ts, asset_code, reading ) VALUES ";
	sql.append(head);

	int count = 0;
	for (Value::ConstValueIterator itr = rdings.Begin(); itr != rdings.End(); ++itr)
	{
		if (count == m_maxReadingRows)
		{
			sql.append(';');

			const char *query = sql.coalesce();
			logSQL("ReadingsAppend", query);
			PGresult *res = PQexec(dbConnection, query);
			delete[] query;
			if (PQresultStatus(res) != PGRES_COMMAND_OK)
			{
				raiseError("appendReadings", PQerrorMessage(dbConnection));
				PQclear(res);
				return -1;
			}
			PQclear(res);

			sql.clear();
			sql.append(head);
			count = 0;
		}
		if (!itr->IsObject())
		{
			raiseError("appendReadings",
					"Each reading in the readings array must be an object");
			return -1;
		}
		add_row = true;
		const char *asset_code = (*itr)["asset_code"].GetString();
		if (strlen(asset_code) == 0)
		{
			Logger::getLogger()->warn("Postgres appendReadings - empty asset code value, row is ignored");
			continue;
		}

		const char *str = (*itr)["user_ts"].GetString();
		// Check if the string is a function
		if (isFunction(str))
		{
			if (count)
				sql.append(", (");
			else
				sql.append('(');

			sql.append(str);
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
				if (count)
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
			count++;

			// Handles - asset_code
			sql.append(",\'");
			sql.append(asset_code);
			sql.append("', '");

			// Handles - reading
			StringBuffer buffer;
			Writer<StringBuffer> writer(buffer);
			(*itr)["reading"].Accept(writer);
			sql.append(escape(buffer.GetString()));
			sql.append("\' ");

			sql.append(')');
		}
	}

	if (count == 0)
	{
		// No rows in final block
		return 0;
	}
	sql.append(';');

	const char *query = sql.coalesce();

	if (row > 0)
	{
		logSQL("ReadingsAppend", query);
		PGresult *res = PQexec(dbConnection, query);
		delete[] query;
		if (PQresultStatus(res) == PGRES_COMMAND_OK)
		{
			PQclear(res);
			return atoi(PQcmdTuples(res));
		}
 		raiseError("appendReadings", PQerrorMessage(dbConnection));
		PQclear(res);
		return -1;
	}
	else
	{
		delete[] query;
		return 0;
	}
}

/**
 * Fetch a block of readings from the reading table
 */
bool Connection::fetchReadings(unsigned long id, unsigned int blksize, std::string& resultSet)
{
char	sqlbuffer[200];

	snprintf(sqlbuffer, sizeof(sqlbuffer),
		"SELECT id, asset_code, reading, user_ts AT TIME ZONE 'UTC' as \"user_ts\", ts AT TIME ZONE 'UTC' as \"ts\" FROM fledge.readings WHERE id >= %ld ORDER BY id LIMIT %d;", id, blksize);

	logSQL("ReadingsFetch", sqlbuffer);
	PGresult *res = PQexec(dbConnection, sqlbuffer);
	if (PQresultStatus(res) == PGRES_TUPLES_OK)
	{
		mapResultSet(res, resultSet);
		PQclear(res);
		return true;
	}
 	raiseError("retrieve", PQerrorMessage(dbConnection));
	PQclear(res);
	return false;
}



/**
 * Purge readings from the reading table
 */
unsigned int  Connection::purgeReadings(unsigned long age, unsigned int flags, unsigned long sent, std::string& result)
{
	unsigned long rowidLimit = 0, minrowidLimit = 0, maxrowidLimit = 0, rowidMin;

	string sqlCommand;
	SQLBuffer sql;
	long unsentPurged = 0;
	long unsentRetained = 0;
	long numReadings = 0;
	bool flag_retain;
	int blocks = 0;
	struct timeval startTv{}, endTv{};

	const char *logSection="ReadingsPurgeByAge";

	Logger *logger = Logger::getLogger();

	flag_retain = false;

	if ( (flags & STORAGE_PURGE_RETAIN_ANY) || (flags & STORAGE_PURGE_RETAIN_ALL) )
	{
		flag_retain = true;
	}
	Logger::getLogger()->debug("%s - flags :%X: flag_retain :%d: sent :%lu:", __FUNCTION__, flags, flag_retain, sent);

	// Prepare empty result
	result = "{ \"removed\" : 0, ";
	result += " \"unsentPurged\" : 0, ";
	result += " \"unsentRetained\" : 0, ";
	result += " \"readings\" : 0, ";
	result += " \"method\" : \"age\", ";
	result += " \"duration\" : 0 }";

	logger->info("Purge starting...");
	gettimeofday(&startTv, NULL);

	/*
	 * We fetch the current rowid and limit the purge process to work on just
	 * those rows present in the database when the purge process started.
	 * This prevents us looping in the purge process if new readings become
	 * eligible for purging at a rate that is faster than we can purge them.
	 */
	rowidLimit = purgeOperation("SELECT max(id) from fledge.readings;", logSection,
						   "ReadingsPurgeByAge - phase 1, fetching maximum id",
						   true);
	if (rowidLimit == -1) {
		return 0;
	}
	maxrowidLimit = rowidLimit;

	minrowidLimit = purgeOperation("SELECT min(id) from fledge.readings;", logSection,
						   "ReadingsPurgeByAge - phase 1, fetching minimum id", true);
	if (minrowidLimit == -1) {
		return 0;
	}
	//###   #########################################################################################:

	if (age == 0)
	{
		/*
		 * An age of 0 means remove the oldest hours data.
		 * So set age based on the data we have and continue.
		 */

		sqlCommand = "SELECT round(extract(epoch FROM (now() - min(user_ts)))/360) FROM fledge.readings WHERE id <=" + to_string (rowidLimit) + ";";
		age = purgeOperation(sqlCommand.c_str() , logSection,
					   "ReadingsPurgeByAge - phase 1, calculating age", true);
		if (age == -1) {
			return 0;
		}
	}

	Logger::getLogger()->debug("%s - rowidLimit :%lu: maxrowidLimit :%lu: maxrowidLimit :%lu: age :%lu:", __FUNCTION__, rowidLimit, maxrowidLimit, minrowidLimit, age);

	{
		/*
		 * Refine rowid limit to just those rows older than age hours.
		 */
		unsigned long l = minrowidLimit;
		unsigned long r;
		if (flag_retain) {

			r = min(sent, rowidLimit);
		} else {
			r = rowidLimit;
		}

		r = max(r, l);
		logger->debug   ("%s - l=%u, r=%u, sent=%u, rowidLimit=%u, minrowidLimit=%u, flags=%u", __FUNCTION__, l, r, sent, rowidLimit, minrowidLimit, flags);

		if (l == r)
		{
			logger->info("V2 No data to purge: min_id == max_id == %u", minrowidLimit);
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
			sqlCommand = "SELECT id FROM fledge.readings WHERE id = " + to_string (m) + " AND user_ts < (now() - INTERVAL '" + to_string (age) + " hours');";
			midRowId = purgeOperation(sqlCommand.c_str() , logSection, "ReadingsPurgeByAge - phase 2, fetching midRowId", true);
			if (midRowId == -1) {
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

		Logger::getLogger()->debug("%s - s1 rowidLimit :%lu: minrowidLimit :%lu: maxrowidLimit :%lu:", __FUNCTION__, rowidLimit, minrowidLimit, maxrowidLimit);

		sqlCommand = "SELECT max(id) FROM fledge.readings WHERE id <= " + to_string (rowidLimit) + " AND user_ts < (now() - INTERVAL '" + to_string (age) + " hours');";
		rowidLimit = purgeOperation(sqlCommand.c_str() , logSection, "ReadingsPurgeByAge - phase 2, checking rowidLimit", true);

		if (rowidLimit == -1) {
			return 0;
		}

		Logger::getLogger()->debug("%s - s2 rowidLimit :%lu: minrowidLimit :%lu: maxrowidLimit :%lu:", __FUNCTION__, rowidLimit, minrowidLimit, maxrowidLimit);

		if (minrowidLimit == rowidLimit)
		{
			logger->info("No data to purge");
			return 0;
		}

		rowidMin = minrowidLimit;
		Logger::getLogger()->debug("%s - m :%lu: rowidMin :%lu: ",__FUNCTION__ ,m,  rowidMin);
	}

	
	if ( ! flag_retain )
	{
		unsigned long lastPurgedId;

		sqlCommand = "SELECT id FROM fledge.readings WHERE id = " + to_string (rowidLimit) + ";";
		lastPurgedId = purgeOperation(sqlCommand.c_str() , logSection, "ReadingsPurgeByAge - phase 2, fetching unsentPurged", true);
		if (lastPurgedId == -1) {
			return 0;
		}

		if (sent != 0 && lastPurgedId > sent)	// Unsent readings will be purged
		{
			// Get number of unsent rows we are about to remove
			unsentPurged = rowidLimit - sent;
		}
		Logger::getLogger()->debug("%s - lastPurgedId :%d: unsentPurged :%ld:" ,__FUNCTION__, lastPurgedId, unsentPurged);
	}

	unsigned int deletedRows = 0;
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

		{
			sqlCommand = "DELETE FROM fledge.readings WHERE id <=" + to_string(rowidMin) + ";" ;

			START_TIME;
			rowsAffected = purgeOperation(sqlCommand.c_str() , logSection, "ReadingsPurgeByAge - phase 3, deleting readings", false);
			END_TIME;

			logger->debug("%s - DELETE sql :%s: rowsAffected :%ld:",  __FUNCTION__, sqlCommand.c_str() ,rowsAffected);

			if (rowsAffected == -1) {
				return 0;
			}
			totTime += usecs;

			if(usecs>150000)
			{
				std::this_thread::sleep_for(std::chrono::milliseconds(100+usecs/10000));
			}
		}

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

	logger->debug   ("%s - sent=%u, minrowidLimit=%u, maxrowidLimit=%u, rowidLimit=%u deletedRows=%u", __FUNCTION__, sent, minrowidLimit, maxrowidLimit, rowidLimit, deletedRows);

	unsentRetained = maxrowidLimit - rowidLimit;

	numReadings = maxrowidLimit +1 - minrowidLimit - deletedRows;

	if (sent == 0)	// Special case when not north process is used
	{
		unsentPurged = deletedRows;
	}

	ostringstream convert;

	unsigned long duration;
	gettimeofday(&endTv, NULL);
	duration = (1000000 * (endTv.tv_sec - startTv.tv_sec)) + endTv.tv_usec - startTv.tv_usec;

	convert << "{ \"removed\" : "       << deletedRows    << ", ";
	convert << " \"unsentPurged\" : "   << unsentPurged   << ", ";
	convert << " \"unsentRetained\" : " << unsentRetained << ", ";
	convert << " \"readings\" : "       << numReadings    << ", ";
	convert << " \"method\" : \"age\", ";
	convert << " \"duration\" : "       << duration       << " }";

	result = convert.str();

	duration = duration / 1000; // milliseconds
	logger->info("Purge process complete in %d blocks in %ld milliseconds", blocks, duration);

	Logger::getLogger()->debug("%s - age :%lu: flag_retain :%x: sent :%lu: result :%s:", __FUNCTION__, age, flags, flag_retain, result.c_str() );

	return deletedRows;
}

/**
 * Execute a SQL command for the purge task
 */
unsigned long Connection::purgeOperation(const char *sql, const char *logSection, const char *phase, bool retrieve)
{
	SQLBuffer sqlBuffer;
	const char *query;
	unsigned long value;
	PGresult *res;
	bool error;
	char *PGValue {};

	error = false;
	value = 0;

	Logger::getLogger()->debug("%s - sql :%s: logSection :%s: phase :%s:", __FUNCTION__, sql, logSection, phase);

	sqlBuffer.append(sql);
	query = sqlBuffer.coalesce();
	logSQL(logSection, query);
	res = PQexec(dbConnection, query);
	delete[] query;

	if (retrieve) {
		if (PQresultStatus(res) == PGRES_TUPLES_OK) {

			PGValue = PQgetvalue(res, 0, 0);
			if (PGValue)
				value = (unsigned long) atol(PGValue);

		} else {
			error = true;
		}
	} else {
		if (PQresultStatus(res) == PGRES_COMMAND_OK) {
			value = (unsigned long)atoi(PQcmdTuples(res));
		} else {
			error = true;
		}
	}

	if (error)
	{
		raiseError(phase, PQerrorMessage(dbConnection));
		value = -1;
	}

	PQclear(res);

	return value;
}

/**
 * Purge readings from the reading table leaving a number of rows equal to the parameter rows
 */
unsigned int  Connection::purgeReadingsByRows(unsigned long rows,
					unsigned int flags,
					unsigned long sent,
					std::string& result)
{
	unsigned long deletedRows = 0, unsentPurged = 0, unsentRetained = 0, numReadings = 0;
	unsigned long limit = 0;
	unsigned long rowcount, minId, maxId;
	unsigned long rowsAffectedLastComand;
	unsigned long deletePoint;
	struct timeval startTv, endTv;

	string sqlCommand;
	bool flag_retain;

	const char *logSection="ReadingsPurgeByRows";

	Logger *logger = Logger::getLogger();

	gettimeofday(&startTv, NULL);
	flag_retain = false;

	if ( (flags & STORAGE_PURGE_RETAIN_ANY) || (flags & STORAGE_PURGE_RETAIN_ALL) )
	{
		flag_retain = true;
	}
	Logger::getLogger()->debug(" %s - flags :%X: flag_retain :%s: sent :%ld:", __FUNCTION__, flags, flag_retain ? "true" : "false", sent);

	logger->info("Purge by Rows called");
	if (flag_retain)
	{
		limit = sent;
		logger->info("Sent is %lu", sent);
	}
	logger->info("Purge by Rows called with flag_retain %X, rows %lu, limit %lu", flag_retain, rows, limit);


	rowcount = purgeOperation("SELECT count(*) from fledge.readings;", logSection,
							  "ReadingsPurgeByRows - phase 1, fetching row count", true);
	if (rowcount == -1) {
		return 0;
	}

	maxId = purgeOperation("SELECT max(id) from fledge.readings;", logSection,
						   "ReadingsPurgeByRows - phase 1, fetching maximum id",
						   true);
	if (maxId == -1) {
		return 0;
	}

	numReadings = rowcount;
	rowsAffectedLastComand = 0;
	deletedRows = 0;

	do
	{
		if (rowcount <= rows)
		{
			logger->info("Row count %d is less than required rows %d", rowcount, rows);
			break;
		}

		minId = purgeOperation("SELECT min(id) from fledge.readings;", logSection,
							   "ReadingsPurgeByRows - phase 2, fetching minimum id", true);
		if (minId == -1) {
			return 0;
		}

		deletePoint = minId + 10000;
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

			sqlCommand = "DELETE FROM fledge.readings WHERE id <= " +  to_string(deletePoint);
			rowsAffectedLastComand = purgeOperation(sqlCommand.c_str(), logSection, "ReadingsPurgeByRows - phase 2, deleting readings", false);

			deletedRows += rowsAffectedLastComand;
			numReadings -= rowsAffectedLastComand;
			rowcount    -= rowsAffectedLastComand;

			logger->debug("Deleted %lu rows", rowsAffectedLastComand);
			if (rowsAffectedLastComand == 0)
			{
				break;
			}
			if (limit != 0 && sent != 0)
			{
				unsentPurged = deletePoint - sent;
			}
			else if (!limit)
			{
				unsentPurged += rowsAffectedLastComand;
			}
		}
	} while (rowcount > rows);

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

	Logger::getLogger()->debug("%s - Purge by Rows complete - rows :%lu: flag :%x: sent :%lu:  numReadings :%lu:  rowsAffected :%u:  result :%s:", __FUNCTION__, rows, flags, sent, numReadings, rowsAffectedLastComand, result.c_str() );

	return deletedRows;

}

/**
 * Map a SQL result set to a JSON document
 */
void Connection::mapResultSet(PGresult *res, string& resultSet)
{
int nFields, i, j;
Document doc;

	doc.SetObject();    // Create the JSON document
	Document::AllocatorType& allocator = doc.GetAllocator();
	nFields = PQnfields(res); // No. of columns in resultset
	Value rows(kArrayType);   // Setup a rows array
	Value count;
	count.SetInt(PQntuples(res)); // Create the count
	doc.AddMember("count", count, allocator);

	// Iterate over the rows
	for (i = 0; i < PQntuples(res); i++)
	{
		Value row(kObjectType); // Create a row
		for (j = 0; j < nFields; j++)
		{
			/**
			 * TODO Improve handling of Oid's
			 *
			 * Current OID detection is based on
			 *
			 * SELECT oid, typname FROM pg_type;
			 */

			/**
			 * If PQgetvalue() is pointer to an empty string,
			 * we assume that is a NULL and we return
			 * the "" value no matter the OID value
			 */
			if (!strlen(PQgetvalue(res, i, j)))
			{
				Value value("", allocator);
				Value name(PQfname(res, j), allocator);
				row.AddMember(name, value, allocator);

				// Get the next column
				continue;
			}

			/* PQgetvalue() has a value, check OID */	
			Oid oid = PQftype(res, j);
			switch (oid)
			{
				case 3802: // JSON type hard coded in this example: jsonb
				{
					Document d;
					if (d.Parse(PQgetvalue(res, i, j)).HasParseError())
					{
						raiseError("resultSet", "Failed to parse: %s\n", PQgetvalue(res, i, j));
						continue;
					}
					Value value(d, allocator);
					Value name(PQfname(res, j), allocator);
					row.AddMember(name, value, allocator);
					break;
				}
				case 23:    //INT 4 bytes: int4
				{
					int32_t intVal = atoi(PQgetvalue(res, i, j));
					Value name(PQfname(res, j), allocator);
					row.AddMember(name, intVal, allocator);
					break;
				}
				case 21:    //SMALLINT 2 bytes: int2
				{
					int16_t intVal = (short)atoi(PQgetvalue(res, i, j));
					Value name(PQfname(res, j), allocator);
					row.AddMember(name, intVal, allocator);
					break;
				}
				case 20:    //BIG INT 8 bytes: int8
				{
					int64_t intVal = atol(PQgetvalue(res, i, j));
					Value name(PQfname(res, j), allocator);
					row.AddMember(name, intVal, allocator);
					break;
				}
				case 700: // float4
				case 701: // float8
				case 710: // this OID doesn't exist
				{
					double dblVal = atof(PQgetvalue(res, i, j));
					Value name(PQfname(res, j), allocator);
					row.AddMember(name, dblVal, allocator);
					break;
				}
				case 1184: // Timestamp: timestamptz
				{
					char *str = PQgetvalue(res, i, j);
					Value value(str, allocator);
					Value name(PQfname(res, j), allocator);
					row.AddMember(name, value, allocator);
					break;
				}
				default:
				{
					char *str = PQgetvalue(res, i, j);
					if (oid == 1042) // char(x) rather than varchar so trim white space
					{
						str = trim(str);
					}
					Value value(str, allocator);
					Value name(PQfname(res, j), allocator);
					row.AddMember(name, value, allocator);
					break;
				}
			}
		}
		rows.PushBack(row, allocator);  // Add the row
	}
	doc.AddMember("rows", rows, allocator); // Add the rows to the JSON
	/* Write out the JSON document we created */
	StringBuffer buffer;
	Writer<StringBuffer> writer(buffer);
	doc.Accept(writer);
	resultSet = buffer.GetString();
}

/**
 * Process the aggregate options and return the columns to be selected
 *
 * @param payload           To evaluate for the generation of the SQLcommands
 * @param aggregates        To evaluate for the generation of the SQL commands
 * @param jsonConstraint    To evaluate for the generation of the SQL commands
 * @param isTableReading    True if the handled table is the readings for which
 *                          a specific format should be applied
 * @param sql		    The sql commands relates to payload, aggregates
 *                          and jsonConstraint
 *
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
			raiseError("Select aggregation", "Missing property \"operation\"");
			return false;
		}
		if ((! aggregates.HasMember("column")) && (! aggregates.HasMember("json")))
		{
			raiseError("Select aggregation", "Missing property \"column\" or \"json\"");
			return false;
		}

		string column_name = aggregates["column"].GetString();

		sql.append(aggregates["operation"].GetString());
		sql.append('(');
		if (aggregates.HasMember("column"))
		{
			if (strcmp(aggregates["operation"].GetString(), "count") != 0)
			{
				// an operation different from the 'count' is requested
				if (isTableReading && (column_name.compare("user_ts") == 0) )
				{
					sql.append("to_char(user_ts, '" F_DATEH24_US "')");
				}
				else
				{
					sql.append("\"");
					sql.append(column_name);
					sql.append("\"");
				}
			}
			else
			{
				// 'count' operation is requested
				sql.append(column_name);
			}
		}
		else if (aggregates.HasMember("json"))
		{
			const Value& json = aggregates["json"];
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
			sql.append('(');
			sql.append("\"");

			sql.append(json["column"].GetString());
			sql.append("\"");
			sql.append("->");
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
				jsonConstraint.append(json["column"].GetString());
				int field = 0;
				string prev;
				for (Value::ConstValueIterator itr = jsonFields.Begin(); itr != jsonFields.End(); ++itr)
				{
					if (field)
					{
						sql.append("->>");
					}
					if (prev.length() > 0)
					{
						jsonConstraint.append("->>'");
						jsonConstraint.append(prev);
						jsonConstraint.append("'");
					}
					prev = itr->GetString();
					field++;
					sql.append('\'');
					sql.append(itr->GetString());
					sql.append('\'');
				}
				jsonConstraint.append(" ? '");
				jsonConstraint.append(prev);
				jsonConstraint.append("'");
			}
			else
			{
				sql.append('\'');
				sql.append(jsonFields.GetString());
				sql.append('\'');
				if (! jsonConstraint.isEmpty())
				{
					jsonConstraint.append(" AND ");
				}
				jsonConstraint.append(json["column"].GetString());
				jsonConstraint.append(" ? '");
				jsonConstraint.append(jsonFields.GetString());
				jsonConstraint.append("'");
			}
			sql.append(")::float");
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
					sql.append("to_char(user_ts, '" F_DATEH24_US "')");
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
				sql.append("CASE WHEN jsonb_typeof(");
				sql.append("\"");
				sql.append(json["column"].GetString());
				sql.append("\"");
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
				jsonConstraint.append(json["column"].GetString());
				if (jsonFields.IsArray())
				{
					string prev;
					for (Value::ConstValueIterator itr = jsonFields.Begin(); itr != jsonFields.End(); ++itr)
					{
						if (prev.length() > 0)
						{
							jsonConstraint.append("->>'");
							jsonConstraint.append(prev);
							jsonConstraint.append("'");
						}
						prev = itr->GetString();
						sql.append("->>'");
						sql.append(itr->GetString());
						sql.append('\'');
					}
					jsonConstraint.append(" ? '");
					jsonConstraint.append(prev);
					jsonConstraint.append("'");
				}
				else
				{
					sql.append("->'");
					sql.append(jsonFields.GetString());
					sql.append('\'');
					sql.append(") != 'number' THEN 0 ELSE (");

					sql.append("\"");
					sql.append(json["column"].GetString());
					sql.append("\"");
					sql.append("->>'");
					sql.append(jsonFields.GetString());
					sql.append('\'');
					jsonConstraint.append(" ? '");
					jsonConstraint.append(jsonFields.GetString());
					jsonConstraint.append("'");

					sql.append(")::float");

				}
			}
			sql.append(" END) AS \"");
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
				sql.append("to_char(");
				sql.append("\"");
				sql.append(grp["column"].GetString());
				sql.append("\"");
				sql.append(", '");
				sql.append(grp["format"].GetString());
				sql.append("')");
			}
			else
			{
				sql.append("\"");
				sql.append(grp["column"].GetString());
				sql.append("\"");
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
			// Double quotes commented to allow a group by of the type : date(history_ts), key
			//sql.append("\"");
			sql.append(payload["group"].GetString());
			//sql.append("\"");
		}
	}
	if (payload.HasMember("timebucket"))
	{
		const Value& tb = payload["timebucket"];
		if (! tb.IsObject())
		{
			raiseError("Select data", "The \"timebucket\" property must be an object");
			return false;
		}
		if (! tb.HasMember("timestamp"))
		{
			raiseError("Select data", "The \"timebucket\" object must have a timestamp property");
			return false;
		}
		if (tb.HasMember("format"))
		{
			sql.append(", to_char(to_timestamp(");
		}
		else
		{
			sql.append(", to_timestamp(");
		}
		if (tb.HasMember("size"))
		{
			sql.append(tb["size"].GetString());
			sql.append(" * ");
		}
		sql.append("floor(extract(epoch from ");
		sql.append(tb["timestamp"].GetString());
		sql.append(") / ");
		if (tb.HasMember("size"))
		{
			sql.append(tb["size"].GetString());
		}
		else
		{
			sql.append(1);
		}
		sql.append("))");
		if (tb.HasMember("format"))
		{
			sql.append(", '");
			sql.append(tb["format"].GetString());
			sql.append("')");
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
		raiseError("query modifiers", "Sort and timebucket modifiers can not be used in the same payload");
		return false;
	}

	// Count columns
	unsigned int nAggregates = 0;
	if (payload.HasMember("aggregate") &&
	    payload["aggregate"].IsArray())
	{
		nAggregates = payload["aggregate"].Size();
	}

	string groupColumn;
	if (payload.HasMember("group"))
	{
		sql.append(" GROUP BY ");
		if (payload["group"].IsObject())
		{
			const Value& grp = payload["group"];
			if (grp.HasMember("format"))
			{
				sql.append("to_char(");
				sql.append("\"");
				sql.append(grp["column"].GetString());
				sql.append("\"");
				sql.append(", '");
				sql.append(grp["format"].GetString());
				sql.append("')");

				// Get the column name in GROUP BY
				groupColumn = grp["column"].GetString();
			}
		}
		else
		{
			// Double quotes commented to allow a group by of the type : date(history_ts), key
			//sql.append("\"");
			sql.append(payload["group"].GetString());
			//sql.append("\"");

			// Get the column name in GROUP BY
			groupColumn = payload["group"].GetString();
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

			// Check wether column name in GROUP BY is the same
			// of column name in ORDER BY
			if (!groupColumn.empty() &&
			    groupColumn.compare(sortBy["column"].GetString()) == 0 &&
			    nAggregates)
			{
				// Note that the GROUP BY column is added as last one
				// in the column names for SELECT
				// The ORDER BY column name is now replaced by a column
				// number, without double quotes
				// The column number is nAggregates + 1
				// Example: SELECT MIN(id), MAX(id), AVG(id) ..
				// nAggregates value is 3
				// Final SQL statement is: SELECT ... ORDER BY 4
				sql.append(nAggregates + 1);
			}
			else
			{
				sql.append("\"");
				sql.append(sortBy["column"].GetString());
				sql.append("\"");
			}
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
					sql.append(", ");
				index++;
				sql.append("\"");
				sql.append((*itr)["column"].GetString());
				sql.append("\"");
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
			raiseError("Select data", "The \"timebucket\" property must be an object");
			return false;
		}
		if (! tb.HasMember("timestamp"))
		{
			raiseError("Select data", "The \"timebucket\" object must have a timestamp property");
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
		sql.append("floor(extract(epoch from ");
		sql.append(tb["timestamp"].GetString());
		sql.append(") / ");
		if (tb.HasMember("size"))
		{
			sql.append(tb["size"].GetString());
		}
		else
		{
			sql.append(1);
		}
		sql.append(") ORDER BY ");
		sql.append("floor(extract(epoch from ");
		sql.append(tb["timestamp"].GetString());
		sql.append(") / ");
		if (tb.HasMember("size"))
		{
			sql.append(tb["size"].GetString());
		}
		else
		{
			sql.append(1);
		}
		sql.append(") DESC");
	}

	if (payload.HasMember("skip"))
	{
		if (!payload["skip"].IsInt())
		{
			raiseError("skip", "Skip must be specfied as an integer");
			return false;
		}
		sql.append(" OFFSET ");
		sql.append(payload["skip"].GetInt());
	}

	if (payload.HasMember("limit"))
	{
		if (!payload["limit"].IsInt())
		{
			raiseError("limit", "Limit must be specfied as an integer");
			return false;
		}
		sql.append(" LIMIT ");
		try {
			sql.append(payload["limit"].GetInt());
		} catch (exception e) {
			raiseError("limit", "Bad value for limit parameter: %s", e.what());
			return false;
		}
	}
	return true;
}

/**
 * Convert a JSON where clause into a PostresSQL where clause
 *
 */
bool Connection::jsonWhereClause(const Value& whereClause,
				SQLBuffer& sql,
				vector<string>  &asset_codes,
				bool convertLocaltime, // not in use
				const string prefix)
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

	// Handle WHERE 1 = 1, 0.55 = 0.55 etc
	string whereColumnName = whereClause["column"].GetString();
	char* p;
	double converted = strtod(whereColumnName.c_str(), &p);
	if (*p)
	{
		// Double quote column name
		if (prefix.empty())
		{
			sql.append("\"");
		}

		// Add prefix
		if (!prefix.empty())
		{
			sql.append(prefix);

		}

		sql.append(whereColumnName);

		// Double quote column name
		if (prefix.empty())
		{
			sql.append("\"");
		}
	}
	else
	{
		// Use numeric value
		sql.append(whereColumnName);
	}

	sql.append(' ');
	string cond = whereClause["condition"].GetString();

	if (cond.compare("isnull") == 0)
	{
		sql.append("isnull ");
	}
	else if (cond.compare("notnull") == 0)
	{
		sql.append("notnull ");
	}
	else
	{
		if (!whereClause.HasMember("value"))
		{
			raiseError("where clause", "The \"where\" object is missing a \"value\" property");
			return false;
		}
		if (!cond.compare("older"))
		{
			if (!whereClause["value"].IsInt())
			{
				raiseError("where clause", "The \"value\" of an \"older\" condition must be an integer");
				return false;
			}
			sql.append("< now() - INTERVAL '");
			sql.append(whereClause["value"].GetInt());
			sql.append(" seconds'");
		}
		else if (!cond.compare("newer"))
		{
			if (!whereClause["value"].IsInt())
			{
				raiseError("where clause", "The \"value\" of an \"newer\" condition must be an integer");
				return false;
			}
			sql.append("> now() - INTERVAL '");
			sql.append(whereClause["value"].GetInt());
			sql.append(" seconds'");
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
				string value = whereClause["value"].GetString();
				sql.append(escape(value));
				sql.append('\'');

				// Identify a specific operation to restrinct the tables involved
				if (whereColumnName.compare("asset_code") == 0)
				{
					if ( cond.compare("=") == 0)
					{
						asset_codes.push_back(value);
					}
				}
			}
		}
	}
 
	if (whereClause.HasMember("and"))
	{
		sql.append(" AND ");
		vector<string>  asset_codes;
		if (!jsonWhereClause(whereClause["and"], sql, asset_codes, false, prefix))
		{
			return false;
		}
	}
	if (whereClause.HasMember("or"))
	{
		vector<string>  asset_codes;
		sql.append(" OR ");
		if (!jsonWhereClause(whereClause["or"], sql, asset_codes, false, prefix))
		{
			return false;
		}
	}

	return true;
}

bool Connection::returnJson(const Value& json, SQLBuffer& sql, SQLBuffer& jsonConstraint)
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
	sql.append(json["column"].GetString());
	sql.append("->");
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
		jsonConstraint.append(json["column"].GetString());
		int field = 0;
		string prev;
		for (Value::ConstValueIterator itr = jsonFields.Begin(); itr != jsonFields.End(); ++itr)
		{
			if (field)
			{
				sql.append("->");
			}
			if (prev.length())
			{
				jsonConstraint.append("->'");
				jsonConstraint.append(prev);
				jsonConstraint.append('\'');
			}
			field++;
			sql.append('\'');
			sql.append(itr->GetString());
			sql.append('\'');
			prev = itr->GetString();
		}
		jsonConstraint.append(" ? '");
		jsonConstraint.append(prev);
		jsonConstraint.append("'");
	}
	else
	{
		sql.append('\'');
		sql.append(jsonFields.GetString());
		sql.append('\'');
		if (! jsonConstraint.isEmpty())
		{
			jsonConstraint.append(" AND ");
		}
		jsonConstraint.append(json["column"].GetString());
		jsonConstraint.append(" ? '");
		jsonConstraint.append(jsonFields.GetString());
		jsonConstraint.append("'");
	}

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
	Logger::getLogger()->error("PostgreSQL storage plugin raising error: %s", tmpbuf);
	manager->setError(operation, tmpbuf, false);
}

/**
 * Return the sie of a given table in bytes
 */
long Connection::tableSize(const string& table)
{
SQLBuffer buf;

	buf.append("SELECT pg_total_relation_size(relid) FROM pg_catalog.pg_statio_user_tables WHERE relname = '");
	buf.append(table);
	buf.append("'");
	const char *query = buf.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) == PGRES_TUPLES_OK)
	{
		long tSize = atol(PQgetvalue(res, 0, 0));
		PQclear(res);
		return tSize;
	}
 	raiseError("tableSize", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
}

/**
  * Add double quotes for words that are reserved as a column name
  * Sample : user to "user"
  *
  * @param column_name  Column name to be evaluated
  * @param out	        Final name of the column
  */
const string Connection::double_quote_reserved_column_name(const string &column_name)
{
	string final_column_name;

	if ( std::find(pg_column_reserved_words.begin(),
		       pg_column_reserved_words.end(),
		       column_name)
	     != pg_column_reserved_words.end()
		)
	{
		final_column_name = "\"" + column_name + "\"";
	}
	else
	{
		final_column_name = column_name;
	}

	return(final_column_name);
}

/**
  * Converts the input string quoting the double quotes : "  to \"
  *
  * @param str   String to convert
  * @param out	Converted string
  */
const string Connection::escape_double_quotes(const string& str)
{
	char		*buffer;
	const char	*p1;
	char  		*p2;
	string		newString;

	if (str.find_first_of('\"') == string::npos)
	{
		return str;
	}

	buffer = (char *)malloc(str.length() * 2);

	p1 = str.c_str();
	p2 = buffer;
	while (*p1)
	{
		if (*p1 == '\"')
		{
			*p2++ = '\\';
			*p2++ = '\"';
			p1++;
		}
		else if (*p1 == '\\' ) // Take care of previously escaped quotes
		{
			*p2++ = '\\';
			*p2++ = '\\';
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
 * Create snapshot of a common table
 *
 * @param table		The table to snapshot
 * @param id		The snapshot id
 * @return		-1 on error, >= 0 on success
 *
 * The new created table name has the name:
 * $table_snap$id
 */
int Connection::create_table_snapshot(const string& table, const string& id)
{
	string query = "SELECT * INTO TABLE fledge.";
	query += table + "_snap" +  id + " FROM fledge." + table;

	logSQL("CreateTableSnapshot", query.c_str());

	PGresult *res = PQexec(dbConnection, query.c_str());
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return 1;
	}

	raiseError("create_table_snapshot", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
}

/**
 * Set the contents of a common table from a snapshot
 *
 * @param table		The table to fill
 * @param id		The snapshot id of the table
 * @return		-1 on error, >= 0 on success
 *
 */
int Connection::load_table_snapshot(const string& table, const string& id)
{
	string purgeQuery = "DELETE FROM fledge." + table;
	string query = "START TRANSACTION; " + purgeQuery;
	query += "; INSERT INTO fledge." + table;
	query += " SELECT * FROM fledge." + table + "_snap" + id;
	query += "; COMMIT;";

	logSQL("LoadTableSnapshot", query.c_str());

	PGresult *res = PQexec(dbConnection, query.c_str());
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return 1;
	}
	else
	{
		PGresult *resRollback = PQexec(dbConnection, "ROLLBACK;");
		if (PQresultStatus(resRollback) != PGRES_COMMAND_OK)
		{
			raiseError(" rollback load_table_snapshot",
				   PQerrorMessage(dbConnection));
		}
		PQclear(resRollback);
	}

	raiseError("load_table_snapshot", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
}

/**
 * Delete a snapshot of a common table
 *
 * @param table		The table to snapshot
 * @param id		The snapshot id
 * @return		-1 on error, >= 0 on success
 */
int Connection::delete_table_snapshot(const string& table, const string& id)
{
	string query = "DROP TABLE fledge." + table + "_snap" + id;

	logSQL("DeleteTableSnapshot", query.c_str());

	PGresult *res = PQexec(dbConnection, query.c_str());
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return 1;
	}

	raiseError("delete_table_snapshot", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
}

/**
 * Get list of snapshots for a given common table
 *
 * @param table         The given table name
 * @param resultSet	Output data buffer
 * @return		True on success, false on database errors
 */
bool Connection::get_table_snapshots(const string& table,
                                     string& resultSet)
{               
SQLBuffer sql;  
	try
	{
		sql.append("SELECT REPLACE(table_name, '");
		sql.append(table);
		sql.append("_snap', '') AS id FROM information_schema.tables ");
		sql.append("WHERE table_schema = 'fledge' AND table_name LIKE '");
		sql.append(table);
		sql.append("_snap%';");

		const char *query = sql.coalesce();
		logSQL("GetTableSnapshots", query);

		PGresult *res = PQexec(dbConnection, query);
		delete[] query;
		if (PQresultStatus(res) == PGRES_TUPLES_OK)
		{
			mapResultSet(res, resultSet);
			PQclear(res);

			return true;
		}
		char *SQLState = PQresultErrorField(res, PG_DIAG_SQLSTATE);
		if (!strcmp(SQLState, "22P02")) // Conversion error
		{
			raiseError("get_table_snapshots", "Unable to convert data to the required type");
		}
		else
		{
			raiseError("get_table_snapshots", PQerrorMessage(dbConnection));
		}
		PQclear(res);
		return false;
	} catch (exception e) {
		raiseError("get_table_snapshots", "Internal error: %s", e.what());
	}
	return false;
}

/**
 * Check to see if the str is a function
 *
 * @param str   The string to check
 * @return true if the string contains a function call
 */
bool Connection::isFunction(const char *str) const
{
	return strcmp(str, "now()") == 0;
}

/**
 * In the case of a join add the columns to select from for all the tables in
 * the join
 *
 * @param document	The query we are processing
 * @param sql		The SQLBuffer we are writing
 * @param level		The table number we are processing
 */
bool Connection::selectColumns(const Value& document, SQLBuffer& sql, int level)
{
SQLBuffer	jsonConstraints;

	string tag = "t" + to_string(level) + ".";

	if (document.HasMember("return"))
	{
		int col = 0;
		const Value& columns = document["return"];
		if (! columns.IsArray())
		{
			raiseError("retrieve", "The property return must be an array");
			return false;
		}
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
				sql.append(tag);
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
							raiseError("rerieve", "format must be a string");
							return false;
						}
						sql.append("to_char(");
						sql.append("\"");
						sql.append((*itr)["column"].GetString());
						sql.append("\"");
						sql.append(", '");
						sql.append((*itr)["format"].GetString());
						sql.append("')");
					}
					else if (itr->HasMember("timezone"))
					{
						if (! (*itr)["timezone"].IsString())
						{
							raiseError("rerieve", "timezone must be a string");
							return false;
						}
						sql.append("\"");
						sql.append((*itr)["column"].GetString());
						sql.append("\"");
						sql.append(" AT TIME ZONE '");
						sql.append((*itr)["timezone"].GetString());
						sql.append("' ");
					}
					else
					{
						sql.append(tag);
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
	}
	else
	{
		sql.append('*');
		return true;
	}
	if (document.HasMember("join"))
	{
		const Value& join = document["join"];
		if (join.HasMember("query"))
		{
			const Value& query = join["query"];
			sql.append(", ");
			if (!selectColumns(query, sql, ++level))
			{
				raiseError("commonRetrieve", "Join failed to add select columns");
				return false;
			}
		}
	}
	return true;
}


/**
 * In the case of a join add the tables to select from for all the tables in
 * the join
 *
 * @param document	The query we are processing
 * @param sql		The SQLBuffer we are writing
 * @param level		The table number we are processing
 */
bool Connection::appendTables(const string& schema,
			const Value& document,
			SQLBuffer& sql,
			int level)
{
	string tag = "t" + to_string(level);
	if (document.HasMember("join"))
	{
		const Value& join = document["join"];
		if (join.HasMember("table"))
		{
			const Value& table = join["table"];
			if (!table.HasMember("name"))
			{
				raiseError("commonRetrieve", "Joining table is missing a table name");
				return false;
			}
			const Value& name = table["name"];
			if (!name.IsString())
			{
				raiseError("commonRetrieve", "Joining table name is not a string");
				return false;
			}

			sql.append(", ");
                        sql.append(schema);
                        sql.append('.');
                        sql.append(name.GetString());
                        sql.append(" ");
                        sql.append(tag);
			if (join.HasMember("query"))
			{
				const Value& query = join["query"];
				appendTables(schema, query, sql, ++level);
			}
			else
			{
				raiseError("commonRetrieve", "Join is missing a join query definition");
				return false;
			}
		}
		else
		{
			raiseError("commonRetrieve", "Join is missing a table definition");
			return false;
		}
	}
	return true;
}

/**
 * Recurse down and add the where cluase and join terms for each
 * new table joined to the query
 *
 * @param query	The JSON query
 * @param sql	The SQLBuffer we are writing the data to
 * @param asset_codes   The asset codes
 * @param level	The nesting level of the joined table
 */
bool Connection::processJoinQueryWhereClause(const Value& query,
						SQLBuffer& sql,
						std::vector<std::string> &asset_codes,
						int level)
{
	string tag = "t" + to_string(level) + ".";
	if (!jsonWhereClause(query["where"], sql, asset_codes, false, tag))
	{
		return false;
	}

	if (query.HasMember("join"))
	{
		// Now and the join condition itself
		string col0, col1;
		const Value& join = query["join"];
		if (join.HasMember("on") && join["on"].IsString())
		{
			col0 = join["on"].GetString();
		}
		else
		{
			return false;
		}
		if (join.HasMember("table"))
		{
			const Value& table = join["table"];
			if (table.HasMember("column") && table["column"].IsString())
			{
				col1 = table["column"].GetString();
			}
			else
			{
				raiseError("Joined query", "Missing join column in table");
				return false;
			}
		}
		sql.append(" AND ");
		sql.append(tag);
		sql.append(col0);
		sql.append(" = t");
		sql.append(level + 1);
		sql.append(".");
		sql.append(col1);
		sql.append(" ");
		if (join.HasMember("query") && join["query"].IsObject())
		{
			sql.append(" AND ");
			const Value& query = join["query"];
			processJoinQueryWhereClause(query, sql, asset_codes, level + 1);
		}
	}
	return true;
}

/**
 * Find existing payload schema from the DB fledge.service_schema table 
 *
 * @param service   The string containing service name 
 * @param name      The string containing schema name
 * @return 	    resultSet string containing the output of the sql query executed
 */

bool Connection::findSchemaFromDB(const std::string &service, const std::string &schema, std::string &resultSet)
{

	SQLBuffer sql;
        try
        {
		sql.append("select * from fledge.service_schema where service = '");
		sql.append(service);
		sql.append("'");
		sql.append(" and name = '");
	        sql.append(schema);
	      	sql.append("';");
                const char *query = sql.coalesce();
                logSQL("findSchemaFromDB", query);

                PGresult *res = PQexec(dbConnection, query);
                delete[] query;
                if (PQresultStatus(res) == PGRES_TUPLES_OK)
                {
                        mapResultSet(res, resultSet);
                        PQclear(res);

                        return true;
		}
		else
		{
			char *SQLState = PQresultErrorField(res, PG_DIAG_SQLSTATE);
                	if (!strcmp(SQLState, "22P02")) // Conversion error
                 	{
                        	raiseError("findSchemaFromDB", "Unable to convert data to the required type");
                 	}
                 	else
                 	{
                        	raiseError("findSchemaFromDB", PQerrorMessage(dbConnection));
                 	}
                 	PQclear(res);
                 	return false;
         	}
	}catch (exception e) {
                	raiseError("findSchemaFromDB", "Internal error: %s", e.what());
        }
         
	return false;
}

/**
 * This function parses the fledge.service_schema table payload retrieved in 
 * and outputs a set of data structures containg the information about the tables
 * and their columns and indexes
 *
 * @param[out] 	version   version retrieved form payload  
 * @param[in]   res       output containing payload information
 * @param[out]  tableColumnMap map[tablename ---> set of columns]
 * @param[out]  tableIndexMap  map[tablename ---> indexes] where each index is a comma separated string of columns
 * @param[ouy]  schemaCreationRequest which is like this is first schema creation request or
 *              schema already exist in the DB
 * @return      true if parsing is successful else false 
 */

bool Connection::parseDatabaseStorageSchema(int &version,const std::string &res, 
		 std::unordered_map<std::string, std::unordered_set<columnRec, columnRecHasher, columnRecComparator> > &tableColumnMap,
		 std::unordered_map<std::string, std::vector<std::string> > &tableIndexMap,
		 bool &schemaCreationRequest)
{
	Document document;

	if (document.Parse(res.c_str()).HasParseError())
        {
       		raiseError("parseDatabaseStorageSchema", "%s:%d Failed to parse JSON payload (DB query response) %s at %d",__FUNCTION__, __LINE__, GetParseError_En(document.GetParseError()), document.GetErrorOffset());

	        return false;
        }
	if (!document.HasMember("count"))
	{
		raiseError("parseDatabaseStorageSchema", "%s:%d count absent from database query response to fledge.service_schema",__FUNCTION__, __LINE__);
                return false;
	}
	int count = document["count"].GetInt();
	if ( count == 0)
	{
		Logger::getLogger()->debug("%s:%d count = 0, returning from function parseDatabaseStorageSchema", __FUNCTION__, __LINE__);
		schemaCreationRequest = true;
		return true;
	}
        if (!document.HasMember("rows"))
        {
        	raiseError("parseDatabaseStorageSchema", "%s:%d rows absent from database query reponse to fledge.service_schema", __FUNCTION__, __LINE__);
        	return false;
        }
        else
	{
		Value& rows = document["rows"];
                if (!rows.IsArray())
                {
                	raiseError("parseDatabaseStorageSchema", "%s:%d The property rows in database query reponse to fledge.service_schema must be an array", __FUNCTION__, __LINE__);
                        return false;
                }
                else
                {
			if (rows.Size() < 1)
			{
				raiseError("parseDatabaseStorageSchema", "%s:%d rows array from database query reponse to fledge.service_schema has size 0", __FUNCTION__, __LINE__);
		                return false;
			}
			// The above check ensures rows[0] can be accessed
			Value& firstRow = rows[0];

			if (!firstRow.HasMember("version"))
			{
				 raiseError("parseDatabaseStorageSchema", "%s:%d rows[0] in fledge.service_schema does not have version", __FUNCTION__, __LINE__);
				 return false;
			}

			if(!firstRow["version"].IsInt())
                        {
                        	raiseError("parseDatabaseStorageSchema", "%s %d extracting version in rows[0],expecting an int value here", __FUNCTION__, __LINE__);
				return false;
                        }
			version = firstRow["version"].GetInt();

			if (!firstRow.HasMember("definition"))
                        {
                                 raiseError("parseDatabaseStorageSchema", "%s:%d rows[0] in fledge.service_schema does not have definition", __FUNCTION__, __LINE__);
                                 return false;
                        }
			if (!firstRow["definition"].IsString())
			{
				raiseError("parseDatabaseStorageSchema", "%s:%d The property definition in rows[0] in fledge.service_schema must be a string", __FUNCTION__, __LINE__);
				return false;
			}
			std::string defStr = firstRow["definition"].GetString();
			if (defStr.empty())
			{
				raiseError("parseDatabaseStorageSchema", "%s:%d The rows[0][definition] in fledge.service_schema is empty", __FUNCTION__, __LINE__);
				return false;
			}

			Document docDefStr;
			if (docDefStr.Parse(defStr.c_str()).HasParseError())
        		{
                		raiseError("parseDatabaseStorageSchema", "%s:%d Failed to parse JSON starting at definition in database query reponse to fledge.service_schema %s:%d ", __FUNCTION__, __LINE__, GetParseError_En(docDefStr.GetParseError()),docDefStr.GetErrorOffset());
                		return false;
        		}

			if (!docDefStr.HasMember("tables"))
                        {
                                raiseError("parseDatabaseStorageSchema", "%s:%d tables section not present in payload obtained from fledge.service_schema ",__FUNCTION__, __LINE__);
                                return false;
                        }

			Value& tables = docDefStr["tables"];
			if (!tables.IsArray())
			{
				raiseError("parseDatabaseStorageSchema", "%s:%d The tables section obtained from payload in fledge.service_schema must be anarray", __FUNCTION__, __LINE__);
				return false;
			}

			// Iterate over the table s list and prepare the data structures
			for (rapidjson::SizeType i = 0; i < tables.Size(); i++)
                        {
				if (!tables[i].HasMember("name"))
				{
					raiseError("parseDatabaseStorageSchema", "%s:%d The tables[%d] section in payload in fledge.service_schema does not have name field", __FUNCTION__, __LINE__, i);
                                	return false;
				}
				if (!tables[i]["name"].IsString())
                        	{
                                	raiseError("parseDatabaseStorageSchema", "%s:%d The property name in tables[%d] in fledge.service_schema must be a string", __FUNCTION__, __LINE__, i);
                                	return false;
                        	}
                        	std::string name = tables[i]["name"].GetString();

				if (!tables[i].HasMember("columns"))
                                {
                                        raiseError("parseDatabaseStorageSchema", "%s:%d The tables[%d] section in payload in fledge.service_schema does not have columns field", __FUNCTION__, __LINE__, i);
                                        return false;
                                }

                        	Value& columns = tables[i]["columns"];

				std::unordered_set<columnRec, columnRecHasher, columnRecComparator> columnSet;
				std::vector<std::string> indexesVec;

	                        if (!columns.IsArray())
                        	{
 	                       		raiseError("parseDatabaseStorageSchema", "%s:%d The property columns in table %s must be an array", __FUNCTION__, __LINE__, name.c_str());
                                	return false;
                        	}

				Logger::getLogger()->debug("%s:%d Extracting the columns of table name %s", __FUNCTION__, __LINE__, name.c_str());

                        	for (auto& v : columns.GetArray())
                        	{
       	                		if (v.IsObject())
					{
						if (v.HasMember("column"))
                                                {
                                                	if (!v["column"].IsString())
                                                        {
                                                        	Logger::getLogger()->error("%s :%d, table %s,extracting column name, expecting a string value here", __FUNCTION__, __LINE__, name.c_str());
                                                        }
                                                        else
                                                        {
								columnRec c;
								c.column = v["column"].GetString();
								if ( c.column.empty())
								{
									raiseError("parseDatabaseStorageSchema", "%s :%d, table %s, column name empty,inconsistent DB", __FUNCTION__, __LINE__, name.c_str());
									return false;
								}
								if (v.HasMember("type"))
								{
									if (!v["type"].IsString())
                                                        		{
                                                                		Logger::getLogger()->error("%s:%d tablename %s, column = %s, extracting column type, expecting a string value here", __FUNCTION__, __LINE__,name.c_str(), c.column.c_str());
                                                        		}
									c.type = v["type"].GetString();
								}

								if (v.HasMember("size"))
								{
									if (!v["size"].IsInt())
                                                                        {       
                                                                                Logger::getLogger()->error("%s:%d, tableName = %s, column = %s,extracting column size, expecting an int value here", __FUNCTION__, __LINE__,name.c_str(), c.column.c_str());
                                                                        }
									c.sz = v["size"].GetInt();
								}

								if (v.HasMember("key"))
                                                		{
		                                                        if (!v["key"].IsBool())
                                                        		{
		                                                                Logger::getLogger()->error("%s:%d, tableName = %s, column = %s,extracting column key, expecting a bool value here", __FUNCTION__, __LINE__, name.c_str(), c.column.c_str());
                                                        		}
		                                                        else
                 		                                        {
                                                                		if (v["key"].GetBool())
										{
											c.key = true;
										}
                                                        		}
								}

								columnSet.insert(c);
							}
                                                }

					}
				}

				Logger::getLogger()->debug("%s:%d Extracting the indexes of tables[%d]", __FUNCTION__, __LINE__, i);

				if (!tables[i].HasMember("indexes"))
                                {
                                        Logger::getLogger()->debug("%s:%d The tables[%d] section in payload in fledge.service_schema does not have indexes field", __FUNCTION__, __LINE__, i);
                                }
				else
				{

					Value& indexes = tables[i]["indexes"];
					if (!indexes.IsArray())
                                	{
                                        	raiseError("parseDatabaseStorageSchema", "%s:%d The property indexes under tablename = %s must be an array", __FUNCTION__, __LINE__, name.c_str());
                                        	return false;
                                	}


					for (auto& v : indexes.GetArray())
                                	{
						std::vector<std::string> indexVec;
						std::string s;
                                        	if (v.IsObject())
                                        	{
                                                	if (v.HasMember("index"))
                                                	{
                                                        	if (!v["index"].IsArray())
                                                        	{
                                                                	raiseError("parseDatabaseStorageSchema", "%s:%d, tableName = %s, extracting index values, expecting an array here", __FUNCTION__, __LINE__, name.c_str());
									return false;
                                                        	}
                                                        	else
                                                        	{
									for (auto& i : v["index"].GetArray())
									{
										if (!i.IsString())
                                                                		{
                                                                        		raiseError("parseDatabaseStorageSchema", "%s:%d, tableName = %s, extracting index ,expecting a string here", __FUNCTION__, __LINE__, name.c_str());
                                                                        		return false;
                                                                		}
										indexVec.push_back(i.GetString());
									}

									std::sort(indexVec.begin(), indexVec.end());
									for ( int i = 0; i < indexVec.size(); ++i)
									{
										s.append(indexVec[i]);
										if ( i < indexVec.size() -1 ) s.append(",");
									}
                                                        	}
                                                	}
                                        	}
						indexesVec.push_back(s);
                                	}
				}

				tableColumnMap[name] = columnSet;
				tableIndexMap[name] = indexesVec;
			}
		}

	}

	return true;
}
/**
 * Create schema of tables
 *
 * @param payload   The  payload containing information about schema of 
 *                  tables to create
 * @return true if the tables can be crated successfully
 */
int Connection::create_schema(const std::string &payload)
{
	Document document;
	std::string schema;
	int version;
	const char *logSection="CreatingSchema";
	unsigned long rowsAffectedLastCommand = 0;
	std::unordered_map<std::string, std::unordered_set<columnRec, columnRecHasher, columnRecComparator> > columnMapFromDB;
        std::unordered_map<std::string, std::vector<std::string> > indexMapFromDB;
	bool schemaCreationReq = false;
	std::vector<sqlQuery> queries;

	try 
	{
                if (payload.empty())
                {
			raiseError("create_schema", "%s:%d function's input parameter payload empty", __FUNCTION__, __LINE__);
                        return -1;
                }
                else
                {
                        if (document.Parse(payload.c_str()).HasParseError())
                        {
				raiseError("create_schema", "%s:%d Failed to parse JSON payload %s:%d", __FUNCTION__, __LINE__, GetParseError_En(document.GetParseError()), document.GetErrorOffset());
                                return -1;
                        }
			if (!document.HasMember("schema"))
                        {
				raiseError("create_schema", "%s:%d schema absent from input parameter JSON payload", __FUNCTION__, __LINE__);
				return -1;
			}
			else
			{
				if (!document["schema"].IsString())
                                {
                                	raiseError("create_schema", "%s:%d The property schema in JSON payload must be a string", __FUNCTION__, __LINE__);
                                        return -1;
                                }
				schema = document["schema"].GetString();

				if (schema.empty())
				{
					raiseError("create_schema", "%s:%d schema obtained from payload is empty", __FUNCTION__, __LINE__);
                                        return -1;
				}
				Logger::getLogger()->debug("%s:%d schema obtained from payload = %s", __FUNCTION__, __LINE__, schema.c_str());

				if (!document.HasMember("service"))
				{
					raiseError("create_schema", "%s:%d service absent from payload for schema %s", __FUNCTION__, __LINE__, schema.c_str());
                                        return -1;
				}
				if (!document["service"].IsString())
                                {
                                        raiseError("create_schema", "%s:%d The property service in JSON payload must be a string", __FUNCTION__, __LINE__);
                                        return -1;
                                }

				std::string service = document["service"].GetString();	
				if (service.empty())
				{
					raiseError("create_schema", "%s:%d empty service name for schema %s", __FUNCTION__, __LINE__, schema.c_str());
                                        return -1;
				}
				Logger::getLogger()->debug("%s:%d service obtained from payload = %s", __FUNCTION__, __LINE__, service.c_str());

				if (!document.HasMember("version"))
                        	{
					raiseError("create_schema", "%s:%d version absent from payload for schema %s and service %s", __FUNCTION__, __LINE__, schema.c_str(), service.c_str());
                                	return -1;
                        	}
				else
				{
					if(!document["version"].IsInt())
                                        {
	                                        raiseError("create_schema", "%s %d version needs to be int for schema %s and service %s", __FUNCTION__, __LINE__, schema.c_str(), service.c_str());
						return -1;
                                        }

					version = document["version"].GetInt();
					Logger::getLogger()->debug("%s:%d version obtained from payload = %d", __FUNCTION__, __LINE__, version);
					std::string results;
					if (findSchemaFromDB(service, schema, results))
					{
						if (!parseDatabaseStorageSchema(version, results, columnMapFromDB, indexMapFromDB, schemaCreationReq))
						{
							raiseError("create_schema", "%s:%d error in parsing Database Storage schema %s for schema  and service %s", __FUNCTION__, __LINE__, schema.c_str(), service.c_str());
							return -1;
						}
					}
					else
					{
						raiseError("create_schema", "%s:%d findSchemaFromDB returned false, error in database query execution for service %s, schema %s", __FUNCTION__, __LINE__, service.c_str(), schema.c_str());
						return -1;
					}
							
					std::string queryToCreateSchema = "create schema if not exists " + schema + ";" ;
	                                rowsAffectedLastCommand = purgeOperation(queryToCreateSchema.c_str(), logSection, "Create Schema if not exists ", false);
					if (rowsAffectedLastCommand == -1)
					{
						raiseError("create_schema", "%s:%d Error in creating schema %s in database, query executed = %s",__FUNCTION__,__LINE__, schema.c_str(), queryToCreateSchema.c_str());
						return -1;
					}
				}
				if (!document.HasMember("tables"))
                        	{
					raiseError("create_schema", "%s:%d tables section absent from payload for schema %s and service %s", __FUNCTION__, __LINE__, schema.c_str(), service.c_str());
                                	return -1;
                        	}
				else
				{
					Logger::getLogger()->debug("%s:%d Extracting tables from payload for schema %s and service %s", __FUNCTION__, __LINE__, schema.c_str() , service.c_str());

					Value& tables = document["tables"];
					if (!tables.IsArray())
                                	{
                                        	raiseError("create_schema", "%s:%d, Schema %s, Service %s, The property tables must be an array", __FUNCTION__, __LINE__, schema.c_str(), service.c_str());
                                        	return -1;
                                	}
					else
                          		{
						std::unordered_set<std::string> unSetTablesInSchemaRequest;
						std::string sqlDropTables;

						// Iterate over all the table lists in the Schema Creation/Alter request
                                		for (rapidjson::SizeType i = 0; i < tables.Size(); i++)
						{
							if (!tables[i].HasMember("name"))
                                			{
			                                        raiseError("create_schema", "%s:%d Schema %s, Service %s : The tables[%d] section in payload does not have name field", __FUNCTION__, __LINE__,schema.c_str(), service.c_str(), i);
                       				                 return -1;
                                			}
                                			if (!tables[i]["name"].IsString())
                                			{
                                        			raiseError("create_schema", "%s:%d , Schema %s, Service %s, The property name in tables[%d] must be a string", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), i);
                                        			return -1;
                                			}
                                
							std::string name = tables[i]["name"].GetString();

							if (name.empty())
							{
								raiseError("create_schema", "%s:%d Schema %s, Service %s, The property name in tables[%d] is empty", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), i);
								return -1;	
							}
							Logger::getLogger()->debug("%s:%d Extracting columns for schema %s, service %s, table name %s ", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());

							unSetTablesInSchemaRequest.insert(name);

							if (!tables[i].HasMember("columns"))
                                                        {
                                                                raiseError("create_schema", "%s:%d The tables section does not have columns field", __FUNCTION__, __LINE__);
                                                                return -1;
                                                        }
							Value& columns = tables[i]["columns"];
							if (!columns.IsArray())
                                                        {
                                                                raiseError("create_schema", "%s:%d The property columns must be an array", __FUNCTION__, __LINE__);
                                                                return -1;
                                                        }

							std::vector<std::string> indexesMatrixFromReq;
							std::unordered_set<columnRec, columnRecHasher, columnRecComparator> colsPerTableInReq;
							bool alterTable = false;
							std::string sql, sqlIdx;

							// if this is schema creation request  or 
							// this table does not exist in db, then create it 
							// else alter the table
							if (schemaCreationReq || (columnMapFromDB.find(name) == columnMapFromDB.end()))
							{
								sql = "create table " + schema + "." + name + " (" ;
							}
							else
							{
								sql = "alter table " + schema + "." + name + " " ;
								alterTable = true;
							}
					
							// Iterate over the columns array
							// For each column, find name, type, size, primary key or not
							// and store in colsPerTableInReq
							for (auto& v : columns.GetArray())
							{
								if (v.IsObject())
				                                {
									columnRec c;
									if (v.HasMember("column"))
                                        				{
                                                				if (!v["column"].IsString())
										{
											raiseError("create_schema", "%s %d Schema: %s, Service: %s ,table name %s , extracting column name, expecting a string value here", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());
											return -1; 
										}
										else
										{
                                                                			c.column = v["column"].GetString(); 
											if (c.column.empty())
											{
												raiseError("create_schema", "%s %d Schema: %s, Service: %s ,table name %s, extracting column, found empty value for column", __FUNCTION__, __LINE__, schema.c_str(), service.c_str() , name.c_str());
												return -1;	
											}
										}
									}

									if (v.HasMember("type"))
									{
										if (!v["type"].IsString())
										{
											raiseError("create_schema", "%s:%d Schema:%s, Service:%s, tableName : %s , extracting type, expecting a string value here", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());
											return -1;
										}
										else
										{
											c.type = v["type"].GetString();
											if (c.type == "double") c.type = "real";
											if (!checkValidDataType(c.type))
											{
												raiseError("create_schema", "%s:%d Schema:%s, Service:%s, tableName : %s , type %s extracted is not a valid data type", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str(), c.type.c_str());
												return -1;
											}

										}
									}

									if (v.HasMember("size"))
									{
										if(!v["size"].IsInt())
										{
											raiseError("create_schema", "%s %d Schema:%s, Service:%s, tableName:%s ,extracting size, expecting an int value here", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());
											return -1;
										}
										else
										{
											c.sz = v["size"].GetInt();
										}
									}

									if (v.HasMember("key"))
									{
										if(!v["key"].IsBool())
                                                                                {
											raiseError("create_schema", "%s %d Schema:%s, Service:%s, tableName:%s, extracting key, expecting a bool value here", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());
											return -1;

                                                                                }
                                                                                else
                                                                                {
                                                                                         c.key = v["key"].GetBool();
                                                                                }
                                                                        }

									colsPerTableInReq.insert(c);
								}
							}

							// Iterate over all the indexes per table and store in indexesMatrixFromReq

							if (!tables[i].HasMember("indexes"))
                                                        {
								//Indexes are optional,if absent, will not trigger an exit from function
                                                                Logger::getLogger()->debug("%s:%d Schema:%s, Service:%s, tableName:%s does not have indexes field", __FUNCTION__, __LINE__ ,schema.c_str(), service.c_str(), name.c_str());
                                                        }
							else
							{

								Value& idx = tables[i]["indexes"];
								if (!idx.IsArray())
                                                        	{
									// make sure if indexes are present, their type in JSON is valid
                                                                	raiseError("create_schema", "%s:%d Schema:%s, Service:%s, tableName:%s The property indexes must be an array", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());
									return -1;
                                                        	}
								else
								{
									Logger::getLogger()->debug("%s:%d Extracting indexes for Schema:%s, Service:%s, tableName: %s", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());

                        						for (auto& v : idx.GetArray())
                        						{
                                        					std::vector<std::string> indexVec;
										std::string s;	
				                                        	if (v.IsObject())
                                        					{
				                                                	if (v.HasMember("index"))
                               					                	{
                                                        					if (!v["index"].IsArray())
                                                        					{
				                                                                	raiseError("create_schema", "%s %d Schema:%s, Service:%s, tableName:%s , extracting index values, expecting an array here", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());
                               					                                 	return -1;
                                                        					}
                                                        					else
                                                        					{
													// keep the cols in indexes as a comma separated list of sorted columns
				                                                                	for (auto& i : v["index"].GetArray())
                                                                					{
                                                                        					indexVec.push_back(i.GetString());
                                                                					}

                                                                					std::sort(indexVec.begin(), indexVec.end());
													for (auto i = 0; i < indexVec.size(); ++i)
													{
														s.append(indexVec[i]);
														if (i < indexVec.size() -1){
															s.append(",");
														}
													}
                                                        					}
                                                					}
                                        					}
										indexesMatrixFromReq.push_back(s);
									}
								}
							}

							// Traverse through the colums list found in DB for this table 
							// and create/alter/delete the colums list
							//

							unordered_set<columnRec, columnRecHasher, columnRecComparator> *dbCol = nullptr;
							if (columnMapFromDB.find(name) != columnMapFromDB.end())
							{
								dbCol = &columnMapFromDB[name];
								Logger::getLogger()->debug("%s:%d Schema:%s, Service:%s, tableName: %s found in Database ", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());

							}
							else
							{
								Logger::getLogger()->debug("%s:%d Schema:%s, Service:%s, tableName: %s could not be found in Database ", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str());
							}

							bool columnsToAlter = false;
							for ( auto& v: colsPerTableInReq)
							{
								// table creation case
								if (!alterTable)
								{
									sql += v.column + " " + v.type;
									if (v.type == "varchar")
									{
										sql += "(" + std::to_string(v.sz) + ")";	
									}

									if (v.key == true)
									{
										sql += " primary key";
									}
									sql +=",";
								}
								else
								{
									// alter table case, table already exists
									// check if column already exists in database
									// if not then add if not a key column
									if (dbCol != nullptr && (dbCol->find(v) == dbCol->end()))
									{
										// if it is not a key then add the column else log error
										if (!v.key)
										{
											sql += "add column ";
											sql += v.column + " " + v.type;
			                                                                if (v.type == "varchar")
               				                                                {
                        	                                                        	sql += "(" + std::to_string(v.sz) + ")";
											}
											sql +=",";
											columnsToAlter = true;
										}
										else
										{
											// altering a key is not allowed
											// column in req does not exist in DB
											// but is key, not allowed
											raiseError("create_schema", "%s:%d Schema:%s, Service:%s, tableName:%s, altering key request(%s) is not allowed for an existing table, dropping the schema request", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str(), v.column.c_str());
											return -1;
										}
									}
									else
									{
										// altering an existing column not alllowed
										// This condition means , column in req already present in DB
										if (dbCol != nullptr)
										{
											auto itr = dbCol->find(v);
											//Check if the column matches exactly with that present in db , if not same , the reject the request
											// We ignore size for integer columns
											if (v.type.compare("integer") == 0)
											{
											       	if (itr->type != v.type || itr->key != v.key)
												{
													raiseError("create_schema", "%s:%d Schema:%s, Service:%s, tableName:%s, altering an existing column %s is not allowed", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str(), v.column.c_str() );
													return -1;
												}
											}
											else if (itr->type != v.type || itr->sz != v.sz || itr->key != v.key)
											{
												raiseError("create_schema", "%s:%d Schema:%s, Service:%s, tableName:%s, altering an existing column %s is not allowed", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str(), v.column.c_str() );
												return -1;
											}
										}
									}
								}
							}

							// If altering the table, drop all the columns which are present
							// in DB but are not in the request, iterate over DB colums list 
							// to find out columns which are ppresent in DB, compare with the
							// incoming request list of columns colsPerTableInReq

							if(alterTable && dbCol)
							{
								for ( auto col : *dbCol)
								{
									// Make sure the column to be dropped is not a primary key
									if(colsPerTableInReq.find(col) == colsPerTableInReq.end())
									{
										if (!col.key)
										{
										// this column is in database but not in latest schema request
										// need to drop this column
											sql += "drop column " + col.column + "," ;
											columnsToAlter = true;
										}
										else
										{
											raiseError("create_schema", "%s:%d Schema:%s, Service:%s, tableName:%s, dropping th ekey column is not allowed", __FUNCTION__, __LINE__, schema.c_str(), service.c_str(), name.c_str(), col.column.c_str());
											return -1;
										}
									}
								}
							}
							
							// remove last comma
							if ( sql[sql.size() - 1] == ',')
							{
								sql.erase(sql.size()-1);
							}

							if (alterTable)
								sql += " ;";
							else
								sql += " );";

							// execute the sql here 
							// if alterTable is true and no columns to Alter , then dont fire the sqlquery
							// 
							if (!(alterTable && !columnsToAlter))
							{
								sqlQuery q;
							        q.query = sql.c_str();
								q.purgeOpArg = "CreatingSchema - phase 1, creating/altering tables";
								char msg[MSG_LEN] = {'\0'};
								snprintf(msg, MSG_LEN, "Function: %s, Schema:%s, Service:%s, tableName:%s, Error in creating/altering tables, command executed = %s",__FUNCTION__, schema.c_str(), service.c_str(), name.c_str(), sql.c_str());
								q.logMsg = msg;

								queries.push_back(q);
								
							}
                                                       	std::vector<std::string> &indexMatrixFromDB = indexMapFromDB[name];
                                                        bool indexPresent = false;

							// create the indexes in req and not in DB
							// iterate over the index creation request and search from 
							// them in DB, if does not exist create it
							for (auto &req : indexesMatrixFromReq)
							{
								indexPresent = false;
								for ( auto &row : indexMatrixFromDB)
								{
									if (req == row)
										indexPresent = true;
								}
									
								if(!indexPresent)
								{
									sqlIdx = "create index " + name + "_" + getIndexName(req) + " on " + schema + "." + name + "(";
                                                               		sqlIdx += req; 
                                                        		sqlIdx += " );";

									sqlQuery q;
									q.query = sqlIdx.c_str();
									q.purgeOpArg = "CreatingSchema - phase 2, creating index on tables";
									char msg[MSG_LEN] = {'\0'};
									snprintf(msg, MSG_LEN, "Function :%s, Schema:%s, Service:%s, tableName:%s Error in creating indexes command %s",__FUNCTION__, schema.c_str(), service.c_str(), name.c_str(), sqlIdx.c_str());
									q.logMsg = msg;

									queries.push_back(q);

								}
							}

							// delete the indexes in DB and not in req
							// iterate over the indexes list present in DB and compare with the
							// indexes in teh schema creation request,if not found, then delete them
							//
							for (auto &req : indexMatrixFromDB)
                                                       	{
                                                       		indexPresent = false;
                                                               	for ( auto &row : indexesMatrixFromReq)
                                                               	{
                                                               		if (req == row)
                                                                       		indexPresent = true;
                                                                }
                                                                if(!indexPresent)
                                                               	{
                                                               		sqlIdx = "drop index " + schema + "." + name + "_" + req + ";";

									sqlQuery q;
									q.query = sqlIdx;
									q.purgeOpArg = "CreatingSchema - phase 2, dropping index on tables";
									char msg[MSG_LEN] = {'\0'};
									snprintf(msg, MSG_LEN, "Function: %s, Schema:%s, Service:%s, tableName:%s, Error in executing drop index command %s",__FUNCTION__, schema.c_str(), service.c_str(), name.c_str(), sqlIdx.c_str());
									q.logMsg = msg;

									queries.push_back(q);
                                                                }
                                                        }
						}
							

						// Iterate over all the sqlQuery command and execute them 

						for (sqlQuery& q : queries)
						{
							if(!q.query.empty())
							{
								rowsAffectedLastCommand = purgeOperation(q.query.c_str(), logSection, q.purgeOpArg.c_str(), false);
                                                                if (rowsAffectedLastCommand == -1)
                                                                {
                                                                	raiseError("create_schema", q.logMsg.c_str());
                                                                        return -1;
                                                                }
							}
						}
						//
						// delete all the tables which are not in the new schema request
						// but present in db

						sqlDropTables += "drop table if exists ";
						bool tableToDrop = false;
						for (auto itr : columnMapFromDB)
						{
							if (unSetTablesInSchemaRequest.find(itr.first) == unSetTablesInSchemaRequest.end())
							{
								sqlDropTables += schema +"." + itr.first + ",";
								tableToDrop = true;
							}
						}
						if (sqlDropTables[sqlDropTables.size() -1 ] == ',')
                                                {
                                                	sqlDropTables.erase(sqlDropTables.size() -1);
                                                }
						sqlDropTables += ";";
						if (tableToDrop)
						{
              						rowsAffectedLastCommand = purgeOperation(sqlDropTables.c_str(), logSection, "Dropping unrequired tables", false);
							if (rowsAffectedLastCommand == -1)
                                                        {
                                                        	raiseError("create_schema", "%s:%d Error in executing drop table command %s",__FUNCTION__,__LINE__, sqlDropTables.c_str());
                                                                return -1;
                                                        }

						}
						// delete payload in fledge.service_schema if already present
						if(schemaCreationReq == false)
						{
							std::string s = "delete from fledge.service_schema where name =  '" + schema + "' and   service = '" + service + "';";
							rowsAffectedLastCommand = purgeOperation(s.c_str(), logSection, "delete from fledge.service_schema  ", false);
							if (rowsAffectedLastCommand == -1)
                                                        {
	                                                        raiseError("create_schema", "%s:%d Error in executing delete payload from service_schema command =%s",__FUNCTION__, __LINE__, s.c_str());
                                                                return -1;
                                                        }

						}

						// insert payload in the fledge.service_schema
                        			std::string s = "insert into fledge.service_schema(name, service, version, definition) values ('" + schema + "', " +"'" + service + "', " + to_string(version) + ", " + "'" + payload + "') ;" ;

                        		        rowsAffectedLastCommand = purgeOperation(s.c_str(), logSection, "insert in fledge.service_schema  ", false);
						if (rowsAffectedLastCommand == -1)
                                                {
	                                                raiseError("create_schema", "%s:%d Error in executing insert payload into service_schema, command =%s ",__FUNCTION__, __LINE__, s.c_str());
                                                        return -1;
                                                }
					}
				}
			}
	    	}
	    
	}
	catch( std::exception &e){
		raiseError("create_schema", "%s %d exception caught %s", __FUNCTION__, __LINE__, e.what() );
		return -1;
	}

	return 1;

}

/**
 * This function checks for input string for ',' and returns a string with ',' replaced with '_'
 *
 * @param[in]   string to check for ',' 
 * @return      string with , replaced with _ 
 */

std::string Connection::getIndexName(std::string s){
	std::replace_if( s.begin(),s.end(), [](char ch) {return ch ==',';},'_');	
	return s;
}

/**
 * This function checks whether the passed string represent a valid postgres column data type 
 *
 * @param[in]   string to check for ','
 * @return     	true if it is a valid data type , false otherwise 
 */

bool Connection::checkValidDataType(const std::string &s){
	return ( s == "varchar" || s ==  "integer" || s ==  "double" || s == "real" || s == "sequence");
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
SQLBuffer       sql;
unsigned int rowsAffected;

	sql.append("DELETE FROM fledge.readings");

	if (!asset.empty())
	{
		sql.append(" WHERE asset_code = '" + asset + "'");
	}
	sql.append(';');
       
	const char *query = sql.coalesce();
        logSQL("PurgeReadingsAsset", query);

	START_TIME;

	PGresult *res = PQexec(dbConnection, query);

	END_TIME;

	delete[] query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return atoi(PQcmdTuples(res));
	}
	raiseError("PurgeReadingsAsset", PQerrorMessage(dbConnection));
	PQclear(res);
	return 0;
}
