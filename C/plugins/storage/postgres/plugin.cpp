/*
 * Fledge storage service.
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <connection_manager.h>
#include <connection.h>
#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include "libpq-fe.h"
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include <sstream>
#include <iostream>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <config_category.h>

using namespace std;
using namespace rapidjson;

#define DEFAULT_SCHEMA "fledge"

#define OR_DEFAULT_SCHEMA(x)	((x) ? (x) : DEFAULT_SCHEMA)

/**
 * The Postgres plugin interface
 */
extern "C" {


const char *default_config = QUOTE({
                "poolSize" : {
                        "description" : "Connection pool size",
                        "type" : "integer",
                        "default" : "5",
                        "displayName" : "Pool Size",
                        "order" : "1"
                        },
                "maxReadingRows" : {
                        "description" : "The maximum numebnr of readings to insert in a single statement",
                        "type" : "integer",
                        "default" : "5000",
                        "displayName" : "Max. Insert Rows",
                        "order" : "2"
                        }
                });

/**
 * The plugin information structure
 */
static PLUGIN_INFORMATION info = {
	"PostgresSQL",            // Name
	"1.2.0",                  // Version
	SP_COMMON|SP_READINGS,    // Flags
	PLUGIN_TYPE_STORAGE,      // Type
	"1.6.0",                  // Interface version
	default_config
};

/**
 * Return the information about this plugin
 */
PLUGIN_INFORMATION *plugin_info()
{
	return &info;
}

/**
 * Initialise the plugin, called to get the plugin handle
 * In the case of Postgres we also get a pool of connections
 * to use.
 */
PLUGIN_HANDLE plugin_init(ConfigCategory *category)
{
ConnectionManager *manager = ConnectionManager::getInstance();
long poolSize = 5, maxReadingRows = 5000;

	if (category->itemExists("poolSize"))
	{
		poolSize = strtol(category->getValue("poolSize").c_str(), NULL, 10);
	}
	if (category->itemExists("maxReadingRows"))
	{
		long val = strtol(category->getValue("maxReadingRows").c_str(), NULL, 10);
		if (val > 0)
			maxReadingRows = val;
	}
	manager->setMaxReadingRows(maxReadingRows);
	manager->growPool(poolSize);
	return manager;
}

/**
 * Insert into an arbitrary table
 */
int plugin_common_insert(PLUGIN_HANDLE handle, char *schema, char *table, char *data)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return 0;
	}


	int result = connection->insert(std::string(OR_DEFAULT_SCHEMA(schema)) + "." + std::string(table), std::string(data));
	manager->release(connection);
	return result;
}

/**
 * Retrieve data from an arbitrary table
 */
const char *plugin_common_retrieve(PLUGIN_HANDLE handle, char *schema, char *table, char *query)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string results;

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return NULL;
	}

	bool rval = connection->retrieve(schema, std::string(OR_DEFAULT_SCHEMA(schema)) + "." + std::string(table), std::string(query), results);
	manager->release(connection);
	if (rval)
	{
		return strdup(results.c_str());
	}
	return NULL;
}

/**
 * Update an arbitary table
 */
int plugin_common_update(PLUGIN_HANDLE handle, char *schema, char *table, char *data)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return 0;
	}

	int result = connection->update(std::string(OR_DEFAULT_SCHEMA(schema)) + "." + std::string(table), std::string(data));
	manager->release(connection);
	return result;
}

/**
 * Delete from an arbitrary table
 */
int plugin_common_delete(PLUGIN_HANDLE handle, char *schema , char *table, char *condition)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return 0;
	}

	int result = connection->deleteRows(std::string(OR_DEFAULT_SCHEMA(schema)) + "." + std::string(table), std::string(condition));
	manager->release(connection);
	return result;
}

/**
 * Append a sequence of readings to the readings buffer
 */
int plugin_reading_append(PLUGIN_HANDLE handle, char *readings)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return 0;
	}

	int result = connection->appendReadings(readings);
	manager->release(connection);
	return result;
}

/**
 * Fetch a block of readings from the readings buffer
 */
char *plugin_reading_fetch(PLUGIN_HANDLE handle, unsigned long id, unsigned int blksize)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string	  resultSet;

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return NULL;
	}

	connection->fetchReadings(id, blksize, resultSet);
	manager->release(connection);
	return strdup(resultSet.c_str());
}

/**
 * Retrieve some readings from the readings buffer
 */
char *plugin_reading_retrieve(PLUGIN_HANDLE handle, char *condition)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string results;

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return NULL;
	}

	connection->retrieveReadings(std::string(condition), results);
	manager->release(connection);
	return strdup(results.c_str());
}

/**
 * Purge readings from the buffer
 */
char *plugin_reading_purge(PLUGIN_HANDLE handle, unsigned long param, unsigned int flags, unsigned long sent)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string 	  results;
unsigned long	  age, size;

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return NULL;
	}

	if (flags & STORAGE_PURGE_SIZE)
	{
		(void)connection->purgeReadingsByRows(param, flags, sent, results);
	}
	else
	{
		age = param;
		(void)connection->purgeReadings(age, flags, sent, results);
	}
	manager->release(connection);
	return strdup(results.c_str());
}

/**
 * Release a previously returned result set
 */
void plugin_release(PLUGIN_HANDLE handle, char *results)
{
	(void)handle;
	free(results);
}

/**
 * Return details on the last error that occured.
 */
PLUGIN_ERROR *plugin_last_error(PLUGIN_HANDLE handle)
{
ConnectionManager *manager = (ConnectionManager *)handle;
  
	return manager->getError();
}

/**
 * Shutdown the plugin
 */
bool plugin_shutdown(PLUGIN_HANDLE handle)
{
ConnectionManager *manager = (ConnectionManager *)handle;
  
	manager->shutdown();
	return true;
}


/**
 * Create snapshot of a common table
 *
 * @param handle	The plugin handle
 * @param table		The table to shapshot
 * @param id		The snapshot id
 * @return		-1 on error, >= o on success
 *
 * The new created table has the following name:
 * table_id
 */
int plugin_create_table_snapshot(PLUGIN_HANDLE handle,
				 char *table,
				 char *id)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return -1;
	}

        int result = connection->create_table_snapshot(std::string(table),
							std::string(id));
        manager->release(connection);
        return result;
}

/**
 * Load a snapshot of a common table
 *
 * @param handle	The plugin handle
 * @param table		The table to fill from a given snapshot
 * @param id		The table snapshot id
 * @return		-1 on error, >= o on success
 */
int plugin_load_table_snapshot(PLUGIN_HANDLE handle,
				char *table,
				char *id)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return -1;
	}

        int result = connection->load_table_snapshot(std::string(table),
						     std::string(id));
        manager->release(connection);
        return result;
}

/**
 * Delete a snapshot of a common table
 *
 * @param handle	The plugin handle
 * @param table		The table which shapshot will be removed
 * @param id		The snapshot id
 * @return		-1 on error, >= o on success
 *
 */
int plugin_delete_table_snapshot(PLUGIN_HANDLE handle,
				 char *table,
				 char *id)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return -1;
	}

        int result = connection->delete_table_snapshot(std::string(table),
							std::string(id));
        manager->release(connection);
        return result;
}
/**
 * Get all snapshots of a given common table
 *
 * @param handle	The plugin handle
 * @param table		The table name 
 * @return 		List of snapshots (even empty list) or NULL for errors
 *
 */
const char* plugin_get_table_snapshots(PLUGIN_HANDLE handle,
					char *table)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string results;

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return NULL;
	}

	bool rval = connection->get_table_snapshots(std::string(table), results);
	manager->release(connection);

	return rval ? strdup(results.c_str()) : NULL;
}

/**
 * Create schema of a common table
 *
 * @param handle        The plugin handle
 * @param payload       The payload to shapshot
 * @return              -1 on error, >= o on success
 *
 */
int plugin_createSchema(PLUGIN_HANDLE handle,
                                 char *payload)
{
	ConnectionManager *manager = (ConnectionManager *)handle;
	Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return -1;
	}

	int result = connection->create_schema(std::string(payload));
        manager->release(connection);
        return result;
}

int plugin_schema_update(PLUGIN_HANDLE handle, 
		                  char *schema, char *payload)
{
	ConnectionManager *manager = (ConnectionManager *)handle;
        Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return 0;
	}

	// create_schema handles both create and update schema
	// schema value gets parsed from the payload
        int result = connection->create_schema(std::string(payload));
        manager->release(connection);
        return result;

}

/**
 * Purge given readings asset or all readings from the buffer
 */
unsigned int plugin_reading_purge_asset(PLUGIN_HANDLE handle, char *asset)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	if (connection == NULL)
	{
		Logger::getLogger()->fatal("No database connections available");
		return 0;
	}

	unsigned int deleted = connection->purgeReadingsAsset(asset);
	manager->release(connection);
	return deleted;
}

};
