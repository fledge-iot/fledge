/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <config_category.h>
#include <storage_plugin.h>
#include <plugin_exception.h>

using namespace std;

#define DEFAULT_SCHEMA "fledge"

/**
 * Constructor for the class that wraps the storage plugin
 *
 * Create a set of function points that resolve to the loaded plugin and
 * enclose in the class.
 */
StoragePlugin::StoragePlugin(const string& name, PLUGIN_HANDLE handle) : Plugin(handle), m_name(name), m_config(NULL)
{
	// Call the init method of the plugin
	string version = this->getInfo()->interface;
	int major = strtol(version.c_str(), NULL, 10);
	size_t offset = version.find(".");
	int minor = 0;
	if (offset != string::npos)
	{
		minor = strtol(version.substr(offset + 1).c_str(), NULL, 10);
	}
	if (major > 1 || minor > 3)	// Configuration starts at 1.4.0 of the interface
	{
		m_config = new StoragePluginConfiguration(name, this);
		PLUGIN_HANDLE (*pluginInit)(ConfigCategory *) = (PLUGIN_HANDLE (*)(ConfigCategory *))
					manager->resolveSymbol(handle, "plugin_init");
		ConfigCategory *config = m_config->getConfiguration();
		instance = (*pluginInit)(config);
		delete config;
	}
	else
	{
		PLUGIN_HANDLE (*pluginInit)() = (PLUGIN_HANDLE (*)())
					manager->resolveSymbol(handle, "plugin_init");
		instance = (*pluginInit)();
	}

	if (major >= 1 && minor >= 5)
	{
		m_bStorageSchemaFlag = true;
	}


	// Setup the function pointers to the plugin
	
	if (!m_bStorageSchemaFlag)
	{
  		commonInsertPtr = (int (*)(PLUGIN_HANDLE, const char*, const char*))
				manager->resolveSymbol(handle, "plugin_common_insert");
	}
	else
	{
		storageSchemaInsertPtr = (int (*)(PLUGIN_HANDLE, const char*, const char*, const char*))
                                manager->resolveSymbol(handle, "plugin_common_insert");
	}

	if (!m_bStorageSchemaFlag)
	{
		commonRetrievePtr = (char * (*)(PLUGIN_HANDLE, const char*, const char*))
				manager->resolveSymbol(handle, "plugin_common_retrieve");
	}
	else
	{
		storageSchemaRetrievePtr = (char * (*)(PLUGIN_HANDLE, const char*, const char*, const char*))
                                manager->resolveSymbol(handle, "plugin_common_retrieve");
	}

	if (!m_bStorageSchemaFlag)
	{
		commonUpdatePtr = (int (*)(PLUGIN_HANDLE, const char*, const char*))
                                manager->resolveSymbol(handle, "plugin_common_update");
	}
	else
	{
		storageSchemaUpdatePtr = (int (*)(PLUGIN_HANDLE, const char*, const char*, const char*))
                                manager->resolveSymbol(handle, "plugin_common_update");
	}

	if (!m_bStorageSchemaFlag)
	{
		commonDeletePtr = (int (*)(PLUGIN_HANDLE, const char*, const char*))
				manager->resolveSymbol(handle, "plugin_common_delete");
	}
	else
	{
		storageSchemaDeletePtr = (int (*)(PLUGIN_HANDLE, const char*, const char*, const char*))
                                manager->resolveSymbol(handle, "plugin_common_delete");
	}

	readingsAppendPtr = (int (*)(PLUGIN_HANDLE, const char *))
				manager->resolveSymbol(handle, "plugin_reading_append");
	readingsFetchPtr = (char * (*)(PLUGIN_HANDLE, unsigned long id, unsigned int blksize))
				manager->resolveSymbol(handle, "plugin_reading_fetch");
	readingsRetrievePtr = (char * (*)(PLUGIN_HANDLE, const char *))
				manager->resolveSymbol(handle, "plugin_reading_retrieve");
	readingsPurgePtr = (char * (*)(PLUGIN_HANDLE, unsigned long age, unsigned int flags, unsigned long sent))
				manager->resolveSymbol(handle, "plugin_reading_purge");
	readingsPurgeAssetPtr = (unsigned int (*)(PLUGIN_HANDLE, const char *))
				manager->resolveSymbol(handle, "plugin_reading_purge_asset");
	releasePtr = (void (*)(PLUGIN_HANDLE, const char *))
				manager->resolveSymbol(handle, "plugin_release");
	lastErrorPtr = (PLUGIN_ERROR * (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_last_error");
	createTableSnapshotPtr =
			(int (*)(PLUGIN_HANDLE, const char*, const char*))
			      manager->resolveSymbol(handle, "plugin_create_table_snapshot");
	loadTableSnapshotPtr =
			(int (*)(PLUGIN_HANDLE, const char*, const char*))
			      manager->resolveSymbol(handle, "plugin_load_table_snapshot");
	deleteTableSnapshotPtr =
			(int (*)(PLUGIN_HANDLE, const char*, const char*))
			      manager->resolveSymbol(handle, "plugin_delete_table_snapshot");
	getTableSnapshotsPtr =
			(char * (*)(PLUGIN_HANDLE, const char*))
			      manager->resolveSymbol(handle, "plugin_get_table_snapshots");
	readingStreamPtr =
			(int (*)(PLUGIN_HANDLE, ReadingStream **, bool))
			      manager->resolveSymbol(handle, "plugin_readingStream");
	pluginShutdownPtr = (bool (*)(PLUGIN_HANDLE))manager->resolveSymbol(handle, "plugin_shutdown");

	createSchemaPtr = 
              		(int (*)(PLUGIN_HANDLE, const char*))
                              manager->resolveSymbol(handle, "plugin_createSchema");
}

/**
 * Call the insert method in the plugin
 */
int StoragePlugin::commonInsert(const string& table, const string& payload, const char *schema)
{
	if(!m_bStorageSchemaFlag && this->commonInsertPtr)
	{
		return this->commonInsertPtr(instance, table.c_str(), payload.c_str());
	}
	else
	{
		if (this->storageSchemaInsertPtr)
			return this->storageSchemaInsertPtr(instance, schema ? schema : DEFAULT_SCHEMA, table.c_str(), payload.c_str());
	}
	return 0;
}

/**
 * Call the retrieve method in the plugin
 */
char *StoragePlugin::commonRetrieve(const string& table, const string& payload, const char *schema)
{
	if (!m_bStorageSchemaFlag && this->commonRetrievePtr)
	{
		return this->commonRetrievePtr(instance, table.c_str(), payload.c_str());
	}
	else
	{
		if (this->storageSchemaRetrievePtr)
	                return this->storageSchemaRetrievePtr(instance, schema ? schema : DEFAULT_SCHEMA, table.c_str(), payload.c_str());
        }
	return NULL;
}

/**
 * Call the update method in the plugin
 */
int StoragePlugin::commonUpdate(const string& table, const string& payload, const char *schema)
{
	if (!m_bStorageSchemaFlag && this->commonUpdatePtr)
        {
		return this->commonUpdatePtr(instance, table.c_str(), payload.c_str());
	}
	else
	{
		if (this->storageSchemaUpdatePtr)
                	return this->storageSchemaUpdatePtr(instance, schema ? schema : DEFAULT_SCHEMA, table.c_str(), payload.c_str());
        }
	return 0;
}

/**
 * Call the delete method in the plugin
 */
int StoragePlugin::commonDelete(const string& table, const string& payload, const char *schema)
{
	if (!m_bStorageSchemaFlag && this->commonDeletePtr)
        {
		return this->commonDeletePtr(instance, table.c_str(), payload.c_str());
	}
	else
	{
		if (this->storageSchemaDeletePtr)
			return this->storageSchemaDeletePtr(instance, schema ? schema : DEFAULT_SCHEMA, table.c_str(), payload.c_str());
	}
	return 0;
}

/**
 * Call the readings append method in the plugin
 */
int StoragePlugin::readingsAppend(const string& payload)
{
	return this->readingsAppendPtr(instance, payload.c_str());
}

/**
 * Call the readings fetch method in the plugin
 */
char * StoragePlugin::readingsFetch(unsigned long id, unsigned int blksize)
{
	return this->readingsFetchPtr(instance, id, blksize);
}

/**
 * Call the readings retrieve method in the plugin
 */
char *StoragePlugin::readingsRetrieve(const string& payload)
{
	return this->readingsRetrievePtr(instance, payload.c_str());
}

/**
 * Call the readings purge method in the plugin
 */
char *StoragePlugin::readingsPurge(unsigned long age, unsigned int flags, unsigned long sent)
{
	return this->readingsPurgePtr(instance, age, flags, sent);
}

/**
 * Call the readings purge asset method in the plugin
 */
char *StoragePlugin::readingsPurgeAsset(const string& asset)
{
	if (this->readingsPurgeAssetPtr)
	{
		unsigned int purged = this->readingsPurgeAssetPtr(instance, asset.c_str());
		char *json = (char *)malloc(80);
		if (json)
		{
			snprintf(json, 80, "{ \"purged\" : %u }", purged);
			return json;
		}
		else
		{
			throw runtime_error("Out of memory");
		}
	}
	throw PluginNotImplementedException("Purge by asset name not implemented in the storage plugin");
}

/**
 * Release a result from a retrieve
 */
void StoragePlugin::release(const char *results)
{
	this->releasePtr(instance, results);
}

/**
 * Get the last error from the plugin
 */
PLUGIN_ERROR *StoragePlugin::lastError()
{
	return this->lastErrorPtr(instance);
}

/**
 * Call the create table snaphot method in the plugin
 */
int StoragePlugin::createTableSnapshot(const string& table, const string& id)
{
        return this->createTableSnapshotPtr(instance, table.c_str(), id.c_str());
}

/**
 * Call the load table snaphot method in the plugin
 */
int StoragePlugin::loadTableSnapshot(const string& table, const string& id)
{
        return this->loadTableSnapshotPtr(instance, table.c_str(), id.c_str());
}

/**
 * Call the delete table snaphot method in the plugin
 */
int StoragePlugin::deleteTableSnapshot(const string& table, const string& id)
{
        return this->deleteTableSnapshotPtr(instance, table.c_str(), id.c_str());
}

/**
 * Call the get table snaphot method in the plugin
 */
char *StoragePlugin::getTableSnapshots(const string& table)
{
        return this->getTableSnapshotsPtr(instance, table.c_str());
}

/**
 * Call the reading stream method in the plugin
 */
int StoragePlugin::readingStream(ReadingStream **stream, bool commit)
{
        return this->readingStreamPtr(instance, stream, commit);
}

/**
 * Call the shutdown entry point of the plugin
 */
bool StoragePlugin::pluginShutdown()
{
	if (this->pluginShutdownPtr)
		return this->pluginShutdownPtr(instance);
	return true;
}

/**
 * Call the schema create method in the plugin
 */
int StoragePlugin::createSchema(const string& payload)
{
	if (this->createSchemaPtr)
        	return this->createSchemaPtr(instance, payload.c_str());
	return 0;
}
