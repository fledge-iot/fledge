#include <storage_plugin.h>

using namespace std;

StoragePlugin::StoragePlugin(PLUGIN_HANDLE handle) : Plugin(handle)
{
  commonInsertPtr = (bool (*)(const char*, const char*))manager->resolveSymbol(handle, "plugin_common_insert");
  commonRetrievePtr = (string (*)(const char*, const char*))manager->resolveSymbol(handle, "plugin_common_retrieve");
  commonUpdatePtr = (string (*)(const char*, const char*))manager->resolveSymbol(handle, "plugin_common_update");
  commonDeletePtr = (bool (*)(const char*, const char*))manager->resolveSymbol(handle, "plugin_common_delete");
  readingsAppendPtr = (bool (*)(const char *))manager->resolveSymbol(handle, "plugin_reading_append");
  readingsFetchPtr = (string (*)(unsigned long id, unsigned int blksize))manager->resolveSymbol(handle, "plugin_reading_fetch");
  readingsRetrievePtr = (string (*)(const char *))manager->resolveSymbol(handle, "plugin_reading_retrieve");
  readingsPurgePtr = (unsigned int (*)(unsigned long age, unsigned int flags, unsigned long sent))manager->resolveSymbol(handle, "plugin_reading_purge");
  releasePtr = (void (*)(const char *))manager->resolveSymbol(handle, "plugin_release");
}

/**
 * Call the insert method in the plugin
 */
bool StoragePlugin::commonInsert(const string& table, const string& payload)
{
  return this->commonInsertPtr(table.c_str(), payload.c_str());
}

/**
 * Call the retrieve method in the plugin
 */
string StoragePlugin::commonRetrieve(const string& table, const string& payload)
{
  return this->commonRetrievePtr(table.c_str(), payload.c_str());
}

/**
 * Call the update method in the plugin
 */
string StoragePlugin::commonUpdate(const string& table, const string& payload)
{
  return this->commonUpdatePtr(table.c_str(), payload.c_str());
}

/**
 * Call the delete method in the plugin
 */
bool StoragePlugin::commonDelete(const string& table, const string& payload)
{
  return this->commonDeletePtr(table.c_str(), payload.c_str());
}
