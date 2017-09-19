#include <storage_plugin.h>

using namespace std;

StoragePlugin::StoragePlugin(PLUGIN_HANDLE handle) : Plugin(handle)
{
  // Call the init method of the plugin
  PLUGIN_HANDLE (*pluginInit)() = (PLUGIN_HANDLE (*)())manager->resolveSymbol(handle, "plugin_init");
  instance = (*pluginInit)();


  // Setup the function pointers to the plugin
  commonInsertPtr = (bool (*)(PLUGIN_HANDLE, const char*, const char*))manager->resolveSymbol(handle, "plugin_common_insert");
  commonRetrievePtr = (string (*)(PLUGIN_HANDLE, const char*, const char*))manager->resolveSymbol(handle, "plugin_common_retrieve");
  commonUpdatePtr = (string (*)(PLUGIN_HANDLE, const char*, const char*))manager->resolveSymbol(handle, "plugin_common_update");
  commonDeletePtr = (bool (*)(PLUGIN_HANDLE, const char*, const char*))manager->resolveSymbol(handle, "plugin_common_delete");
  readingsAppendPtr = (bool (*)(PLUGIN_HANDLE, const char *))manager->resolveSymbol(handle, "plugin_reading_append");
  readingsFetchPtr = (string (*)(PLUGIN_HANDLE, unsigned long id, unsigned int blksize))manager->resolveSymbol(handle, "plugin_reading_fetch");
  readingsRetrievePtr = (string (*)(PLUGIN_HANDLE, const char *))manager->resolveSymbol(handle, "plugin_reading_retrieve");
  readingsPurgePtr = (unsigned int (*)(PLUGIN_HANDLE, unsigned long age, unsigned int flags, unsigned long sent))manager->resolveSymbol(handle, "plugin_reading_purge");
  releasePtr = (void (*)(PLUGIN_HANDLE, const char *))manager->resolveSymbol(handle, "plugin_release");
}

/**
 * Call the insert method in the plugin
 */
bool StoragePlugin::commonInsert(const string& table, const string& payload)
{
  return this->commonInsertPtr(instance, table.c_str(), payload.c_str());
}

/**
 * Call the retrieve method in the plugin
 */
string StoragePlugin::commonRetrieve(const string& table, const string& payload)
{
  return this->commonRetrievePtr(instance, table.c_str(), payload.c_str());
}

/**
 * Call the update method in the plugin
 */
string StoragePlugin::commonUpdate(const string& table, const string& payload)
{
  return this->commonUpdatePtr(instance, table.c_str(), payload.c_str());
}

/**
 * Call the delete method in the plugin
 */
bool StoragePlugin::commonDelete(const string& table, const string& payload)
{
  return this->commonDeletePtr(instance, table.c_str(), payload.c_str());
}
