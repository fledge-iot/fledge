/*
 * Fledge storage service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */
#include <sqlite_common.h>
#include <connection_manager.h>
#include <connection.h>
#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include "sqlite3.h"
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include <sstream>
#include <iostream>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <reading_stream.h>
#include <config_category.h>

using namespace std;
using namespace rapidjson;

/**
 * The SQLite3 plugin interface
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
		"vacuumInterval" : {
			"description" : "The interval between execution of a SQLite vacuum command",
			"type" : "integer",
			"minimum" : "1",
			"default" : "6",
			"displayName" : "Vacuum Interval",
			"order" : "2"
		},
		"purgeBlockSize" : {
                        "description" : "The number of rows to purge in each delete statement",
                        "type" : "integer",
                        "default" : "10000",
                        "displayName" : "Purge Block Size",
                        "order" : "3",
                        "minimum" : "1000",
                        "maximum" : "100000"
                }
		});

/**
 * The plugin information structure
 */
static PLUGIN_INFORMATION info = {
	"SQLiteLb",               // Name
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
 * In the case of SQLLite we also get a pool of connections
 * to use.
 */
PLUGIN_HANDLE plugin_init(ConfigCategory *category)
{
ConnectionManager *manager = ConnectionManager::getInstance();
int poolSize = 5;

	if (category->itemExists("poolSize"))
	{
		poolSize = strtol(category->getValue("poolSize").c_str(), NULL, 10);
	}
	manager->growPool(poolSize);
	if (category->itemExists("vacuumInterval"))
	{
		manager->setVacuumInterval(strtol(category->getValue("vacuumInterval").c_str(), NULL, 10));
	}
	if (category->itemExists("purgeBlockSize"))
	{
		unsigned long purgeBlockSize = strtoul(category->getValue("purgeBlockSize").c_str(), NULL, 10);
		manager->setPurgeBlockSize(purgeBlockSize);
	}
	return manager;
}

/**
 * Insert into an arbitrary table
 */
int plugin_common_insert(PLUGIN_HANDLE handle,
			char *schema,
			char *table,
			char *data)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	int result = connection->insert(std::string(schema),
					std::string(table),
					std::string(data));
	manager->release(connection);
	return result;
}

/**
 * Retrieve data from an arbitrary table
 */
const char *plugin_common_retrieve(PLUGIN_HANDLE handle,
				char *schema,
				char *table,
				char *query)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string results;

	bool rval = connection->retrieve(std::string(schema),
					std::string(table),
					std::string(query),
					results);
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
int plugin_common_update(PLUGIN_HANDLE handle,
			char *schema,
			char *table,
			char *data)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	int result = connection->update(std::string(schema),
					std::string(table),
					std::string(data));
	manager->release(connection);
	return result;
}

/**
 * Delete from an arbitrary table
 */
int plugin_common_delete(PLUGIN_HANDLE handle,
			char *schema,
			char *table,
			char *condition)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	int result = connection->deleteRows(std::string(schema),
					std::string(table),
					std::string(condition));
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

	int result = connection->appendReadings(readings);
	manager->release(connection);
	return result;;
}

/**
 * Append a stream of readings to the readings buffer
 */
int plugin_readingStream(PLUGIN_HANDLE handle, ReadingStream **readings, bool commit)
{
	int result = 0;
	ConnectionManager *manager = (ConnectionManager *)handle;
	Connection        *connection = manager->allocate();

	result = connection->readingStream(readings, commit);

	manager->release(connection);
	return result;;
}

/**
 * Fetch a block of readings from the readings buffer
 */
char *plugin_reading_fetch(PLUGIN_HANDLE handle, unsigned long id, unsigned int blksize)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string	  resultSet;

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
 * @return		List of snapshots (even empty list) or NULL for errors
 *
 */
const char* plugin_get_table_snapshots(PLUGIN_HANDLE handle,
				char *table)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string results;

	bool rval = connection->get_table_snapshots(std::string(table), results);
	manager->release(connection);

	return rval ? strdup(results.c_str()) : NULL;
}

/**
 * Update or creats a schema
 *
 * @param handle        The plugin handle
 * @param schema        The name of the schema
 * @param definition    The schema definition
 * @return              -1 on error, >= 0 on success
 *
 */
int plugin_createSchema(PLUGIN_HANDLE handle, char *definition)
{
	ConnectionManager *manager = (ConnectionManager *)handle;
	Connection        *connection = manager->allocate();

	int result = connection->createSchema(std::string(definition));
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

	unsigned int deleted = connection->purgeReadingsAsset(asset);
	manager->release(connection);
	return deleted;
}

};

