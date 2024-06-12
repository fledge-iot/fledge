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
#include <config_category.h>
#include <sstream>
#include <iostream>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <reading_stream.h>

using namespace std;
using namespace rapidjson;

/**
 * The SQLite3 plugin interface
 */
extern "C" {

const char *default_config = QUOTE({
		"poolSize" : {
			"description" : "The number of connections to create in the intial pool of connections",
			"type" : "integer",
			"default" : "5",
			"displayName" : "Pool Size",
			"order" : "1"
		},
		"filename" : {
			"description" : "The name of the file to which the in-memory database should be persisted",
			"type" : "string",
			"default" : "inmemory",
			"displayName" : "Persist File",
			"order" : "3",
			"validity": "persist == \"true\""
		},
		"persist" : {
			"description" : "Enable the persistence of the in-memory database between executions",
			"type" : "boolean",
			"default" : "false",
			"displayName" : "Persist Data",
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
	"SQLite3",		// Name
	"1.1.0",		// Version
	SP_READINGS,		// Flags
	PLUGIN_TYPE_STORAGE,	// Type
	"1.6.0",		// Interface version
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
 *
 * @param category	The plugin configuration category
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
	if (category->itemExists("persist"))
	{
		string p = category->getValue("persist");
		if (p.compare("true") == 0 && category->itemExists("filename"))
		{
			manager->setPersist(true, category->getValue("filename"));
		}
		else
		{
			manager->setPersist(false);
		}
	}
	else
	{
		manager->setPersist(false);
	}
	if (manager->persist())
	{
		Connection        *connection = manager->allocate();
		connection->loadDatabase(manager->filename());
	}
	if (category->itemExists("purgeBlockSize"))
	{
		unsigned long purgeBlockSize = strtoul(category->getValue("purgeBlockSize").c_str(), NULL, 10);
		manager->setPurgeBlockSize(purgeBlockSize);
	}
	return manager;
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

	if (flags & STORAGE_PURGE_SIZE)	// Purge by size
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
  
	if (manager->persist())
	{
		Connection        *connection = manager->allocate();
		connection->saveDatabase(manager->filename());
	}
	manager->shutdown();
	return true;
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

