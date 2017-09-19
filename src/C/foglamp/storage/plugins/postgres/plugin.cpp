#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include "libpq-fe.h"

extern "C" {

static PLUGIN_INFORMATION info = {
  "PostgresSQL",            // Name
  "1.0.0",                  // Version
  SP_COMMON|SP_READINGS,    // Flags
  PLUGIN_TYPE_STORAGE,      // Type
  "1.0.0"                   // Interface version
};

PLUGIN_INFORMATION *plugin_info()
{
  return &info;
}

PLUGIN_HANDLE plugin_init()
{
const char *conninfo;
PGconn     *conn;

    conninfo = "dbname = postgres";

    /* Make a connection to the database */
    conn = PQconnectdb(conninfo);

    /* Check to see that the backend connection was successfully made */
    if (PQstatus(conn) != CONNECTION_OK)
    {
        fprintf(stderr, "Connection to database failed: %s",
                PQerrorMessage(conn));
        return NULL;
    }
    return conn;
}

bool plugin_common_insert(PLUGIN_HANDLE handle, char *table, char *data)
{
PGconn     *conn = (PGconn *)handle;

  return false;
}

char *plugin_common_retrieve(PLUGIN_HANDLE handle, char *table, char *query)
{
  return NULL;
}

bool plugin_common_update(PLUGIN_HANDLE handle, char *table, char *data)
{
  return false;
}

bool plugin_common_delete(PLUGIN_HANDLE handle, char *table, char *condition)
{
  return false;
}

bool plugin_reading_append(PLUGIN_HANDLE handle, char *reading)
{
  return false;
}

char *plugin_reading_fetch(PLUGIN_HANDLE handle, unsigned long id, unsigned int blksize)
{
  return NULL;
}

char *plugin_reading_retrieve(PLUGIN_HANDLE handle, char *condition)
{
  return NULL;
}

unsigned int plugin_reading_purge(PLUGIN_HANDLE handle, unsigned long age, unsigned int flags, unsigned long sent)
{
  return 0;
}

void plugin_release(PLUGIN_HANDLE handle, char *results)
{
}

PLUGIN_ERROR *plugin_last_error(PLUGIN_HANDLE)
{
  return NULL;
}

bool plugin_shutdown(PLUGIN_HANDLE handle)
{
PGconn     *conn = (PGconn *)handle;

  PQfinish(conn);
  return true;
}

};

