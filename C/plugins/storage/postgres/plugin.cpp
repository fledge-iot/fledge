/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
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

using namespace std;
using namespace rapidjson;

/**
 * The Postgres plugin interface
 */
extern "C" {

/**
 * The plugin information structure
 */
static PLUGIN_INFORMATION info = {
	"PostgresSQL",            // Name
	"1.0.0",                  // Version
	SP_COMMON|SP_READINGS,    // Flags
	PLUGIN_TYPE_STORAGE,      // Type
	"1.0.0"                   // Interface version
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
PLUGIN_HANDLE plugin_init()
{
ConnectionManager *manager = ConnectionManager::getInstance();

	manager->growPool(5);
	return manager;
}

/**
 * Insert into an arbitrary table
 */
int plugin_common_insert(PLUGIN_HANDLE handle, char *table, char *data)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	int result = connection->insert(std::string(table), std::string(data));
	manager->release(connection);
	return result;
}

/**
 * Retrieve data from an arbitrary table
 */
const char *plugin_common_retrieve(PLUGIN_HANDLE handle, char *table, char *query)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string results;

	bool rval = connection->retrieve(std::string(table), std::string(query), results);
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
int plugin_common_update(PLUGIN_HANDLE handle, char *table, char *data)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	int result = connection->update(std::string(table), std::string(data));
	manager->release(connection);
	return result;
}

/**
 * Delete from an arbitrary table
 */
int plugin_common_delete(PLUGIN_HANDLE handle, char *table, char *condition)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();

	int result = connection->deleteRows(std::string(table), std::string(condition));
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

	connection->retrieve(std::string("readings"), std::string(condition), results);
	manager->release(connection);
	return strdup(results.c_str());
	manager->release(connection);
	return NULL;
}

/**
 * Purge readings from the buffer
 */
char *plugin_reading_purge(PLUGIN_HANDLE handle, unsigned long age, unsigned int flags, unsigned long sent)
{
ConnectionManager *manager = (ConnectionManager *)handle;
Connection        *connection = manager->allocate();
std::string 	  results;

	// TODO put flags in common header file
	if (flags & 0x0002)	// Purge by size
	{
		unsigned long deletedRows = 0;
		unsigned long unsentPurged = 0;
		unsigned long unsentRetained = 0;
		unsigned long readings = 0;
		/*
		 * Remove readings an hour at a time until we get below
		 * the required size or we no longer remove readings
		 */
		long tableSize = connection->tableSize(std::string("readings"));
		while (tableSize > age)
		{
			(void)connection->purgeReadings(0, flags, sent, results);

			// Parse the JSON response and track number for succesive calls
			Document doc;
			doc.Parse(results.c_str());
			if (doc.HasMember("removed"))
				deletedRows += doc["removed"].GetInt();
			if (doc.HasMember("unsentPurged"))
				unsentPurged += doc["unsentPurged"].GetInt();
			if (doc.HasMember("unsentRetained"))
				unsentRetained += doc["unsentRetained"].GetInt();
			if (doc.HasMember("readings"))
				readings = doc["readings"].GetInt();
			long newTableSize = connection->tableSize(std::string("readings"));
			if (newTableSize == tableSize)
			{
				// We didn't remove any readings, so stop here
				Logger::getLogger()->error("Failed to reach target readings size %ld during purge operation",
					age);
				break;
			}
			tableSize = newTableSize;
		}

		// Create the aggregate JSON response
	        ostringstream convert;

		convert << "{ \"removed\" : " << deletedRows << ", ";
        	convert << " \"unsentPurged\" : " << unsentPurged << ", ";
		convert << " \"unsentRetained\" : " << unsentRetained << ", ";
		convert << " \"readings\" : " << readings << " }";

		results = convert.str();
	}
	else
	{
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

};

