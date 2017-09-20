#include <connection.h>
#include <iostream>
#include <libpq-fe.h>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include <string>


using namespace std;
using namespace rapidjson;

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


Connection::~Connection()
{
   cerr << "Disconnect from Postgres" << endl;
}

string Connection::retrieve(const string& table, const string& condition)
{
Document document;  // Default template parameter uses UTF8 and MemoryPoolAllocator.
string  whereClause;
 
      if (document.Parse(condition.c_str()).HasParseError())
      {
        printf("Failed to parse JSON: %s\n", condition.c_str());
      }
      else
      {
        assert(document.IsObject());
 
        if (document.HasMember("where"))
        {
              whereClause = jsonWhereClause(document["where"]);
        }
        else
        {
          printf("JSON does not contain where clause: %s\n", condition.c_str());
        }
      }

    string query = "SELECT * from " + table + " WHERE " + whereClause + ";";
    PGresult *res = PQexec(dbConnection, query.c_str());
    if (PQresultStatus(res) == PGRES_TUPLES_OK)
      return mapResultSet(res);
  return string(PQerrorMessage(dbConnection));
}

string Connection::mapResultSet(PGresult *res)
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
            Oid oid = PQftype(res, j);
            if (oid == 3802)  // JSON type hard coded in this example
            {
                Document d;
                if (d.Parse(PQgetvalue(res, i, j)).HasParseError())
                  printf("Failed to parse: %s\n", PQgetvalue(res, i, j));
                Value value(d, allocator);
                Value name(PQfname(res, j), allocator);
                row.AddMember(name, value, allocator);
            }
            else
            {
                char *str = PQgetvalue(res, i, j);
                if (oid == 1042) // char(x) rather than varchar so trim white space
                    str = trim(str);
                Value value(str, allocator);
                Value name(PQfname(res, j), allocator);
                row.AddMember(name, value, allocator);
            }
        }
        rows.PushBack(row, allocator);  // Add the row
    }
    doc.AddMember("rows", rows, allocator); // Add the rows to the JSON
    /* Write out the JSON document we created */
    StringBuffer buffer;
    Writer<StringBuffer> writer(buffer);
    doc.Accept(writer);

  return string(buffer.GetString());
}

string Connection::jsonWhereClause(const Value& whereClause)
{
char *buf = (char *)malloc(1000); // Crude but ignoring memory management for now
 
  assert(whereClause.IsObject());
  assert(whereClause.HasMember("column"));
  assert(whereClause.HasMember("condition"));
  assert(whereClause.HasMember("value"));
 
  if (whereClause["value"].IsInt())
    sprintf(buf, "\"%s\" %s %d", whereClause["column"].GetString(),
        whereClause["condition"].GetString(), whereClause["value"].GetInt());
  if (whereClause["value"].IsString())
    sprintf(buf, "\"%s\" %s '%s'", whereClause["column"].GetString(),
        whereClause["condition"].GetString(), whereClause["value"].GetString());
 
  if (whereClause.HasMember("and"))
  {
    string andClause = jsonWhereClause(whereClause["and"]);
    strcat(buf, " AND ");
    strcat(buf, andClause.c_str());
  }
  if (whereClause.HasMember("or"))
  {
    string orClause = jsonWhereClause(whereClause["or"]);
    strcat(buf, " OR ");
    strcat(buf, orClause.c_str());
  }
 
  return string(buf);
}

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

