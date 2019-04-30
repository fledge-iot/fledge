/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <storage_plugin.h>

using namespace std;

/**
 * Constructor for the class that wraps the storage plugin
 *
 * Create a set of function points that resolve to the loaded plugin and
 * enclose in the class.
 *
 * TODO Add support for multiple plugins
 */
StoragePlugin::StoragePlugin(PLUGIN_HANDLE handle) : Plugin(handle)
{
	// Call the init method of the plugin
	PLUGIN_HANDLE (*pluginInit)() = (PLUGIN_HANDLE (*)())
					manager->resolveSymbol(handle, "plugin_init");
	instance = (*pluginInit)();


	// Setup the function pointers to the plugin
  	commonInsertPtr = (int (*)(PLUGIN_HANDLE, const char*, const char*))
				manager->resolveSymbol(handle, "plugin_common_insert");
	commonRetrievePtr = (char * (*)(PLUGIN_HANDLE, const char*, const char*))
				manager->resolveSymbol(handle, "plugin_common_retrieve");
	commonUpdatePtr = (int (*)(PLUGIN_HANDLE, const char*, const char*))
				manager->resolveSymbol(handle, "plugin_common_update");
	commonDeletePtr = (int (*)(PLUGIN_HANDLE, const char*, const char*))
				manager->resolveSymbol(handle, "plugin_common_delete");
	readingsAppendPtr = (int (*)(PLUGIN_HANDLE, const char *))
				manager->resolveSymbol(handle, "plugin_reading_append");
	readingsFetchPtr = (char * (*)(PLUGIN_HANDLE, unsigned long id, unsigned int blksize))
				manager->resolveSymbol(handle, "plugin_reading_fetch");
	readingsRetrievePtr = (char * (*)(PLUGIN_HANDLE, const char *))
				manager->resolveSymbol(handle, "plugin_reading_retrieve");
	readingsPurgePtr = (char * (*)(PLUGIN_HANDLE, unsigned long age, unsigned int flags, unsigned long sent))
				manager->resolveSymbol(handle, "plugin_reading_purge");
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
}

/**
 * Call the insert method in the plugin
 */
int StoragePlugin::commonInsert(const string& table, const string& payload)
{
	return this->commonInsertPtr(instance, table.c_str(), payload.c_str());
}

/**
 * Call the retrieve method in the plugin
 */
char *StoragePlugin::commonRetrieve(const string& table, const string& payload)
{
	return this->commonRetrievePtr(instance, table.c_str(), payload.c_str());
}

/**
 * Call the update method in the plugin
 */
int StoragePlugin::commonUpdate(const string& table, const string& payload)
{
	return this->commonUpdatePtr(instance, table.c_str(), payload.c_str());
}

/**
 * Call the delete method in the plugin
 */
int StoragePlugin::commonDelete(const string& table, const string& payload)
{
	return this->commonDeletePtr(instance, table.c_str(), payload.c_str());
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
