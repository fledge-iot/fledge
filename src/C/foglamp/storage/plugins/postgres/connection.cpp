/*
 * FogLAMP storage service.
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
#include <regex>
#include <stdarg.h>
#include <stdlib.h>
#include <sstream>


using namespace std;
using namespace rapidjson;

/**
 * Create a database connection
 */
Connection::Connection()
{
	const char *defaultConninfo = "dbname = foglamp";
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
		cerr << "Failed to connect" << endl;
	}
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
bool Connection::retrieve(const string& table, const string& condition, string& resultSet)
{
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
SQLBuffer	sql;

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
			if (!jsonAggregates(document, document["aggregate"], sql))
			{
				return false;
			}
			sql.append(" FROM ");
		}
		else
		{
			sql.append("SELECT * FROM ");
		}
		sql.append(table);
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
				raiseError("retrieve", "JSON does not contain where clause");
				return false;
			}
		}
		if (!jsonModifiers(document, sql))
		{
			return false;
		}
	}
	sql.append(';');

	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
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
 * Insert data into a table
 */
bool Connection::insert(const std::string& table, const std::string& data)
{
SQLBuffer	sql;
Document	document;
SQLBuffer	values;
int		col = 0;
 
	if (document.Parse(data.c_str()).HasParseError())
	{
		raiseError("insert", "Failed to parse JSON payload\n");
		return false;
	}
 	sql.append("INSERT INTO ");
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
			// Check if the string is a function
			string s (str);
  			regex e ("[a-zA-Z][a-zA-Z0-9_]*\\(.*\\)");
  			if (regex_match (s,e))
			{
				values.append(str);
			}
			else
			{
				values.append('\'');
				values.append(str);
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
			values.append(buffer.GetString());
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
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return true;
	}
 	raiseError("insert", PQerrorMessage(dbConnection));
	PQclear(res);
	return false;
}

/**
 * Perform an update against a common table
 *
 */
bool Connection::update(const string& table, const string& payload)
{
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
SQLBuffer	sql;
int		col = 0;
 
	if (document.Parse(payload.c_str()).HasParseError())
	{
		raiseError("update", "Failed to parse JSON payload");
		return false;
	}
	else
	{
		sql.append("UPDATE ");
		sql.append(table);
		sql.append(" SET ");

		if (!document.HasMember("values"))
		{
			raiseError("update", "Missing values object in payload");
			return false;
		}

		Value& values = document["values"];
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
				// Check if the string is a function
				string s (str);
				regex e ("[a-zA-Z][a-zA-Z0-9_]*\\(.*\\)");
				if (regex_match (s,e))
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
				sql.append(buffer.GetString());
				sql.append('\'');
			}
			col++;
		}

		if (document.HasMember("condition"))
		{
			sql.append(" WHERE ");
			jsonWhereClause(document["condition"], sql);
		}
	}
	sql.append(';');

	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return true;
	}
 	raiseError("update", PQerrorMessage(dbConnection));
	PQclear(res);
	return false;
}

/**
 * Perform a delete against a common table
 *
 */
bool Connection::deleteRows(const string& table, const string& condition)
{
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
SQLBuffer	sql;
 
	sql.append("DELETE from ");
	sql.append(table);
	if (! condition.empty())
	{
		sql.append(" WHERE ");
		if (document.Parse(condition.c_str()).HasParseError())
		{
			raiseError("delete", "Failed to parse JSON payload");
			return false;
		}
		else
		{
			if (document.HasMember("where"))
			{
				if (!jsonWhereClause(document["where"], sql))
				{
					return false;
				}
			}
			else
			{
				raiseError("delete", "JSON does not contain where clause");
				return false;
			}
		}
	}
	sql.append(';');

	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return true;
	}
 	raiseError("delete", PQerrorMessage(dbConnection));
	PQclear(res);
	return false;
}

bool Connection::appendReadings(const char *readings)
{
Document 	doc;
SQLBuffer	sql;
int		row = 0;

	ParseResult ok = doc.Parse(readings);
	if (!ok)
	{
 		raiseError("appendReadings", GetParseError_En(doc.GetParseError()));
		return false;
	}

	sql.append("INSERT INTO readings ( asset_code, read_key, reading, user_ts ) VALUES ");

	Value &rdings = doc["readings"];
	if (!rdings.IsArray())
	{
		raiseError("appendReadings", "Payload is missing the readings array");
		return false;
	}
	for (Value::ConstValueIterator itr = rdings.Begin(); itr != rdings.End(); ++itr)
	{
		if (!itr->IsObject())
		{
			raiseError("appendReadings",
					"Each reading in the readings array must be an object");
			return false;
		}
		if (row)
			sql.append(", (");
		else
			sql.append('(');
		row++;
		sql.append('\'');
		sql.append((*itr)["asset_code"].GetString());
		sql.append("', \'");
		sql.append((*itr)["read_key"].GetString());
		sql.append("', \'");
		StringBuffer buffer;
		Writer<StringBuffer> writer(buffer);
		(*itr)["reading"].Accept(writer);
		sql.append(buffer.GetString());
		sql.append("\', ");
		const char *str = (*itr)["user_ts"].GetString();
		// Check if the string is a function
		string s (str);
		regex e ("[a-zA-Z][a-zA-Z0-9_]*\\(.*\\)");
		if (regex_match (s,e))
		{
			sql.append(str);
		}
		else
		{
			sql.append('\'');
			sql.append(str);
			sql.append('\'');
		}

		sql.append(')');
	}
	sql.append(';');

	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		PQclear(res);
		return true;
	}
 	raiseError("appendReadings", PQerrorMessage(dbConnection));
	PQclear(res);
	return false;
}

/**
 * Fetch a block of readings from the reading table
 */
bool Connection::fetchReadings(unsigned long id, unsigned int blksize, std::string& resultSet)
{
char	sqlbuffer[100];

	snprintf(sqlbuffer, sizeof(sqlbuffer),
		"SELECT * FROM readings WHERE id >= %ld LIMIT %d;", id, blksize);
	
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
SQLBuffer sql;
long unsentPurged = 0;
long unsentRetained = 0;
long numReadings = 0;

	if (~flags)
	{
		// Get number of unsent rows we are about to remove
		SQLBuffer unsentBuffer;
		unsentBuffer.append("SELECT count(*) FROM readings WHERE  user_ts < now() - INTERVAL '");
		unsentBuffer.append(age);
		unsentBuffer.append(" seconds' AND id < ");
		unsentBuffer.append(sent);
		unsentBuffer.append(';');
		const char *query = unsentBuffer.coalesce();
		PGresult *res = PQexec(dbConnection, query);
		delete[] query;
		if (PQresultStatus(res) == PGRES_TUPLES_OK)
		{
			unsentPurged = atol(PQgetvalue(res, 0, 0));
			PQclear(res);
		}
		else
		{
 			raiseError("retrieve", PQerrorMessage(dbConnection));
			PQclear(res);
		}
	}
	
	sql.append("DELETE FROM readings WHERE user_ts < now() - INTERVAL '");
	sql.append(age);
	sql.append(" seconds'");
	if (flags)	// Don't delete unsent rows
	{
		sql.append(" AND id < ");
		sql.append(sent);
	}
	sql.append(';');
	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete[] query;
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		PQclear(res);
 		raiseError("retrieve", PQerrorMessage(dbConnection));
		return 0;
	}
	unsigned int deletedRows = (unsigned int)atoi(PQcmdTuples(res));
	PQclear(res);

	SQLBuffer retainedBuffer;
	retainedBuffer.append("SELECT count(*) FROM readings WHERE id > ");
	retainedBuffer.append(sent);
	retainedBuffer.append(';');
	const char *query1 = retainedBuffer.coalesce();
	res = PQexec(dbConnection, query1);
	delete[] query1;
	if (PQresultStatus(res) == PGRES_TUPLES_OK)
	{
		unsentRetained = atol(PQgetvalue(res, 0, 0));
	}
	else
	{
 		raiseError("retrieve", PQerrorMessage(dbConnection));
	}
	PQclear(res);

	res = PQexec(dbConnection, "SELECT count(*) FROM readings;");
	if (PQresultStatus(res) == PGRES_TUPLES_OK)
	{
		numReadings = atol(PQgetvalue(res, 0, 0));
	}
	else
	{
 		raiseError("retrieve", PQerrorMessage(dbConnection));
	}
	PQclear(res);

	ostringstream convert;

	convert << "{ \"removed\" : " << deletedRows << ", ";
	convert << " \"unsentPurged\" : " << unsentPurged << ", ";
	convert << " \"unsentRetained\" : " << unsentRetained << ", ";
    	convert << " \"readings\" : " << numReadings << " }";

	result = convert.str();

	return deletedRows;
}


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
			/* TODO Improve handling of Oid's */
			Oid oid = PQftype(res, j);
			switch (oid) {

			case 3802: // JSON type hard coded in this example
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
			case 20:
			{
				long intVal = atol(PQgetvalue(res, i, j));
				Value name(PQfname(res, j), allocator);
				row.AddMember(name, intVal, allocator);
				break;
			}
			case 710:
			{
				double dblVal = atof(PQgetvalue(res, i, j));
				Value name(PQfname(res, j), allocator);
				row.AddMember(name, dblVal, allocator);
				break;
			}
			default:
			{
				char *str = PQgetvalue(res, i, j);
				if (oid == 1042) // char(x) rather than varchar so trim white space
					str = trim(str);
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
 */
bool Connection::jsonAggregates(const Value& payload, const Value& aggregates, SQLBuffer& sql)
{
	if (! aggregates.HasMember("operation"))
	{
		raiseError("Select aggregation", "Missing property \"operation\"");
		return false;
	}
	if (! aggregates.HasMember("column"))
	{
		raiseError("Select aggregation", "Missing property \"column\"");
		return false;
	}
	sql.append(aggregates["operation"].GetString());
	sql.append('(');
	sql.append(aggregates["column"].GetString());
	sql.append(')');
	if (payload.HasMember("group"))
	{
		sql.append(", ");
		sql.append(payload["group"].GetString());
	}
	return true;
}

/**
 * Process the modifers for limit, skip, sort and group
 */
bool Connection::jsonModifiers(const Value& payload, SQLBuffer& sql)
{
	if (payload.HasMember("sort"))
	{
		sql.append(" ORDER BY ");
		const Value& sortBy = payload["sort"];
		if (! sortBy.HasMember("column"))
		{
			raiseError("Select sort", "Missing property \"column\"");
			return false;
		}
		if (! sortBy.HasMember("direction"))
		{
			raiseError("Select sort", "Missing property \"direction\"");
			return false;
		}
		sql.append(sortBy["column"].GetString());
		sql.append(' ');
		sql.append(sortBy["direction"].GetString());
	}

	if (payload.HasMember("group"))
	{
		sql.append(" GROUP BY ");
		sql.append(payload["group"].GetString());
	}

	if (payload.HasMember("skip"))
	{
		sql.append(" OFFSET ");
		sql.append(payload["skip"].GetInt());
	}

	if (payload.HasMember("limit"))
	{
		sql.append(" LIMIT ");
		sql.append(payload["limit"].GetInt());
	}
	return true;
}

/**
 * Convert a JSON where clause into a PostresSQL where clause
 *
 */
bool Connection::jsonWhereClause(const Value& whereClause, SQLBuffer& sql)
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
		raiseError("where clause", "The \"where\" object is missing a \"value\" property");
		return false;
	}

	sql.append(whereClause["column"].GetString());
	sql.append(' ');
	sql.append(whereClause["condition"].GetString()); 
	sql.append(' ');
	if (whereClause["value"].IsInt())
	{
		sql.append(whereClause["value"].GetInt());
	} else if (whereClause["value"].IsString())
	{
		sql.append('\'');
		sql.append(whereClause["value"].GetString());
		sql.append('\'');
	}
 
	if (whereClause.HasMember("and"))
	{
		sql.append(" AND ");
		jsonWhereClause(whereClause["and"], sql);
	}
	if (whereClause.HasMember("or"))
	{
		sql.append(" OR ");
		jsonWhereClause(whereClause["or"], sql);
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
	manager->setError(operation, tmpbuf, false);
}
