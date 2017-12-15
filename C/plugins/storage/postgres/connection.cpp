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
#include <logger.h>
#include <time.h>

using namespace std;
using namespace rapidjson;

static time_t connectErrorTime = 0;
#define CONNECT_ERROR_THRESHOLD		5*60	// 5 minutes

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
		if (connectErrorTime == 0 || (time(0) - connectErrorTime > CONNECT_ERROR_THRESHOLD))
		{
			Logger::getLogger()->error("Failed to connect to the database: %s",
				PQerrorMessage(dbConnection));
			connectErrorTime = time(0);
		}
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
			if (!jsonAggregates(document, document["aggregate"], sql))
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
						if (itr->HasMember("format"))
						{
							sql.append("to_char(");
							sql.append((*itr)["column"].GetString());
							sql.append(", '");
							sql.append((*itr)["format"].GetString());
							sql.append("')");
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
						if (! returnJson(json, sql))
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
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
SQLBuffer	sql;
int		col = 0;
 
	if (document.Parse(payload.c_str()).HasParseError())
	{
		raiseError("update", "Failed to parse JSON payload");
		return -1;
	}
	else
	{
		sql.append("UPDATE foglamp.");
		sql.append(table);
		sql.append(" SET ");

		if (document.HasMember("values"))
		{
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
		if (document.HasMember("expressions"))
		{
			Value& exprs = document["expressions"];
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
					raiseError("update", "expressions must be an array of objects");
					return -1;
				}
				if (!itr->HasMember("column"))
				{
					raiseError("update", "Missing column property in expressions array item");
					return -1;
				}
				if (!itr->HasMember("operator"))
				{
					raiseError("update", "Missing operator property in expressions array item");
					return -1;
				}
				if (!itr->HasMember("value"))
				{
					raiseError("update", "Missing value property in expressions array item");
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
		if (document.HasMember("json_properties"))
		{
			Value& exprs = document["json_properties"];
			if (!exprs.IsArray())
			{
				raiseError("update", "The property json_properties must be an array");
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
					raiseError("update", "json_properties must be an array of objects");
					return -1;
				}
				if (!itr->HasMember("column"))
				{
					raiseError("update", "Missing column property in json_properties array item");
					return -1;
				}
				if (!itr->HasMember("path"))
				{
					raiseError("update", "Missing path property in json_properties array item");
					return -1;
				}
				if (!itr->HasMember("value"))
				{
					raiseError("update", "Missing value property in json_properties array item");
					return -1;
				}
				sql.append((*itr)["column"].GetString());
				sql.append(" = jsonb_set(");
				sql.append((*itr)["column"].GetString());
				sql.append(", '{");
				const Value& path = (*itr)["path"];
				if (!path.IsArray())
				{
					raiseError("update", "The property path must be an array");
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
						raiseError("update", "The elements of path must all be strings");
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
					string s (str);
					regex e ("[a-zA-Z][a-zA-Z0-9_]*\\(.*\\)");
					if (regex_match (s,e))
					{
						sql.append(str);
					}
					else
					{
						sql.append("'\"");
						sql.append(str);
						sql.append("\"'");
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
				sql.append(")");
				col++;
			}
		}

		if (col == 0)
		{
			raiseError("update", "Missing values or expressions object in payload");
			return -1;
		}

		if (document.HasMember("condition"))
		{
			sql.append(" WHERE ");
			if (!jsonWhereClause(document["condition"], sql))
			{
				return false;
			}
		}
		else if (document.HasMember("where"))
		{
			sql.append(" WHERE ");
			if (!jsonWhereClause(document["where"], sql))
			{
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
		if (atoi(PQcmdTuples(res)) == 0)
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
				raiseError("delete", "JSON does not contain where clause");
				return -1;
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
		return atoi(PQcmdTuples(res));
	}
 	raiseError("delete", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
}

/**
 * Append a set of readings to the readings table
 */
int Connection::appendReadings(const char *readings)
{
Document 	doc;
SQLBuffer	sql;
int		row = 0;

	ParseResult ok = doc.Parse(readings);
	if (!ok)
	{
 		raiseError("appendReadings", GetParseError_En(doc.GetParseError()));
		return -1;
	}

	sql.append("INSERT INTO foglamp.readings ( asset_code, read_key, reading, user_ts ) VALUES ");

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
		if (row)
			sql.append(", (");
		else
			sql.append('(');
		row++;
		sql.append('\'');
		sql.append((*itr)["asset_code"].GetString());
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
			sql.append(escape(str));
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
		return atoi(PQcmdTuples(res));
	}
 	raiseError("appendReadings", PQerrorMessage(dbConnection));
	PQclear(res);
	return -1;
}

/**
 * Fetch a block of readings from the reading table
 */
bool Connection::fetchReadings(unsigned long id, unsigned int blksize, std::string& resultSet)
{
char	sqlbuffer[100];

	snprintf(sqlbuffer, sizeof(sqlbuffer),
		"SELECT * FROM foglamp.readings WHERE id >= %ld LIMIT %d;", id, blksize);
	
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

	if (age == 0)
	{
		/*
		 * An age of 0 means remove the oldest hours data.
		 * So set age based on the data we have and continue.
		 */
		SQLBuffer oldest;
		oldest.append("SELECT round(extract(epoch FROM (now() - min(user_ts)))/360) from readings;");
		const char *query = oldest.coalesce();
		PGresult *res = PQexec(dbConnection, query);
		delete[] query;
		if (PQresultStatus(res) == PGRES_TUPLES_OK)
		{
			age = (unsigned long)atol(PQgetvalue(res, 0, 0));
			PQclear(res);
		}
		else
		{
 			raiseError("purge", PQerrorMessage(dbConnection));
			PQclear(res);
			return 0;
		}
	}
	if ((flags & 0x01) == 0)
	{
		// Get number of unsent rows we are about to remove
		SQLBuffer unsentBuffer;
		unsentBuffer.append("SELECT count(*) FROM foglamp.readings WHERE  user_ts < now() - INTERVAL '");
		unsentBuffer.append(age);
		unsentBuffer.append(" hours' AND id > ");
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
	
	sql.append("DELETE FROM foglamp.readings WHERE user_ts < now() - INTERVAL '");
	sql.append(age);
	sql.append(" hours'");
	if ((flags & 0x01) == 0x01)	// Don't delete unsent rows
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
	retainedBuffer.append("SELECT count(*) FROM foglamp.readings WHERE id > ");
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

	res = PQexec(dbConnection, "SELECT count(*) FROM foglamp.readings;");
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
				int64_t intVal = atol(PQgetvalue(res, i, j));
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
			case 1184: // Timestamp
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
		sql.append(aggregates["operation"].GetString());
		sql.append('(');
		if (aggregates.HasMember("column"))
		{
			sql.append(aggregates["column"].GetString());
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
				int field = 0;
				for (Value::ConstValueIterator itr = jsonFields.Begin(); itr != jsonFields.End(); ++itr)
				{
					if (field)
					{
						sql.append("->>");
					}
					field++;
					sql.append('\'');
					sql.append(itr->GetString());
					sql.append('\'');
				}
			}
			else
			{
				sql.append('\'');
				sql.append(jsonFields.GetString());
				sql.append('\'');
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
				sql.append('(');
				sql.append(json["column"].GetString());
				sql.append("->>");
				if (!json.HasMember("properties"))
				{
					raiseError("retrieve", "The json property is missing a properties property");
					return false;
				}
				const Value& jsonFields = json["properties"];
				if (jsonFields.IsArray())
				{
					int field = 0;
					for (Value::ConstValueIterator itr = jsonFields.Begin(); itr != jsonFields.End(); ++itr)
					{
						if (field)
						{
							sql.append("->>");
						}
						field++;
						sql.append('\'');
						sql.append(itr->GetString());
						sql.append('\'');
					}
				}
				else
				{
					sql.append('\'');
					sql.append(jsonFields.GetString());
					sql.append('\'');
				}
				sql.append(")::float");
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
				sql.append("to_char(");
				sql.append(grp["column"].GetString());
				sql.append(", '");
				sql.append(grp["format"].GetString());
				sql.append("')");
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
					sql.append(", ");
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


	if (payload.HasMember("group"))
	{
		sql.append(" GROUP BY ");
		if (payload["group"].IsObject())
		{
			const Value& grp = payload["group"];
			if (grp.HasMember("format"))
			{
				sql.append("to_char(");
				sql.append(grp["column"].GetString());
				sql.append(", '");
				sql.append(grp["format"].GetString());
				sql.append("')");
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
		sql.append(')');
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
	string cond = whereClause["condition"].GetString();
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
			sql.append(whereClause["value"].GetString());
			sql.append('\'');
		}
	}
 
	if (whereClause.HasMember("and"))
	{
		sql.append(" AND ");
		if (!jsonWhereClause(whereClause["and"], sql))
		{
			return false;
		}
	}
	if (whereClause.HasMember("or"))
	{
		sql.append(" OR ");
		if (!jsonWhereClause(whereClause["or"], sql))
		{
			return false;
		}
	}

	return true;
}

bool Connection::returnJson(const Value& json, SQLBuffer& sql)
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
		int field = 0;
		for (Value::ConstValueIterator itr = jsonFields.Begin(); itr != jsonFields.End(); ++itr)
		{
			if (field)
			{
				sql.append("->");
			}
			field++;
			sql.append('\'');
			sql.append(itr->GetString());
			sql.append('\'');
		}
	}
	else
	{
		sql.append('\'');
		sql.append(jsonFields.GetString());
		sql.append('\'');
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
