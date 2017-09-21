#include <connection.h>
#include <sql_buffer.h>
#include <iostream>
#include <libpq-fe.h>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include <string>


using namespace std;
using namespace rapidjson;

/**
 * Create a database connection
 */
Connection::Connection()
{
	const char *conninfo = "dbname = foglamp";
 
	/* Make a connection to the database */
	dbConnection = PQconnectdb(conninfo);

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
 * TODO Improve error handling
 */
bool Connection::retrieve(const string& table, const string& condition, string& resultSet)
{
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
SQLBuffer	sql;
 
	sql.append("SELECT * from ");
	sql.append(table);
	if (! condition.empty())
	{
		sql.append(" WHERE ");
		if (document.Parse(condition.c_str()).HasParseError())
		{
			printf("Failed to parse JSON: %s\n", condition.c_str());
		}
		else
		{
			assert(document.IsObject());
	 
			if (document.HasMember("where"))
			{
				jsonWhereClause(document["where"], sql);
			}
			else
			{
				printf("JSON does not contain where clause: %s\n", condition.c_str());
			}
		}
	}
	sql.append(';');

	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete query;
	if (PQresultStatus(res) == PGRES_TUPLES_OK)
	{
		mapResultSet(res, resultSet);
		return true;
	}
 	resultSet = PQerrorMessage(dbConnection);
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
int		col;
 
	if (document.Parse(data.c_str()).HasParseError())
	{
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
			values.append('\'');
			values.append(itr->value.GetString());
			values.append('\'');
		}
		else if (itr->value.IsDouble())
			values.append(itr->value.GetDouble());
		else if (itr->value.IsNumber())
			values.append(itr->value.GetInt());
		col++;
	}
	sql.append(") values (");
	const char *vals = values.coalesce();
	sql.append(vals);
	delete vals;
	sql.append(");");

	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		return true;
	}
	return false;
}

/**
 * Perform an update against a common table
 *
 * TODO Improve error handling
 * TODO Handle JSON
 */
bool Connection::update(const string& table, const string& payload)
{
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
SQLBuffer	sql;
int		col = 0;
 
	if (document.Parse(payload.c_str()).HasParseError())
	{
		printf("Failed to parse JSON: %s\n", payload.c_str());
		return false;
	}
	else
	{
		sql.append("UPDATE ");
		sql.append(table);
		sql.append(" SET ");

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
				sql.append('"');
				sql.append(itr->value.GetString());
				sql.append('"');
			}
			else if (itr->value.IsDouble())
				sql.append(itr->value.GetDouble());
			else if (itr->value.IsNumber())
				sql.append(itr->value.GetInt());
		}

		if (document.HasMember("condition"))
		{
			sql.append(" WHERE ");
			assert(document.IsObject());
	 
			if (document.HasMember("where"))
			{
				jsonWhereClause(document["where"], sql);
			}
		}
	}
	sql.append(';');

	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		return true;
	}
	return false;
}

/**
 * Perform a delete against a common table
 *
 * TODO Improve error handling
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
			printf("Failed to parse JSON: %s\n", condition.c_str());
		}
		else
		{
			assert(document.IsObject());
	 
			if (document.HasMember("where"))
			{
				jsonWhereClause(document["where"], sql);
			}
			else
			{
				printf("JSON does not contain where clause: %s\n", condition.c_str());
			}
		}
	}
	sql.append(';');

	const char *query = sql.coalesce();
	PGresult *res = PQexec(dbConnection, query);
	delete query;
	if (PQresultStatus(res) == PGRES_COMMAND_OK)
	{
		return true;
	}
	return false;
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
					printf("Failed to parse: %s\n", PQgetvalue(res, i, j));
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
 * Convert a JSON where clause into a PostresSQL where clause
 *
 * TODO Improve error handling
 * TODO Add aggregates
 */
bool Connection::jsonWhereClause(const Value& whereClause, SQLBuffer& sql)
{
	assert(whereClause.IsObject());
	assert(whereClause.HasMember("column"));
	assert(whereClause.HasMember("condition"));
	assert(whereClause.HasMember("value"));

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

