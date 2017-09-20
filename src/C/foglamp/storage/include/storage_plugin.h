#ifndef _STORAGE_PLUGIN
#define _STORAGE_PLUGIN

#include <plugin.h>
#include <plugin_manager.h>
#include <string>

/**
 * Class that represents a storage plugin.
 *
 * The purpose of this class is to hide the use of the pointers into the
 * dynamically loaded plugin and wrap the interface into a class that
 * can be used directly in the storage subsystem.
 *
 * This is achieved by having a set of private member variables which are
 * the pointers to the functions in the plugin, and a set of public methods
 * that will call these functions via the function pointers.
 */
class StoragePlugin : public Plugin {

public:
	StoragePlugin(PLUGIN_HANDLE handle);
	~StoragePlugin();

	bool commonInsert(const std::string& table, const std::string& payload);
	std::string commonRetrieve(const std::string& table, const std::string& payload);
	std::string commonUpdate(const std::string& table, const std::string& payload);
	bool commonDelete(const std::string& table, const std::string& payload);
	bool readingsAppend(const std::string& payload);
	std::string readingsFetch(unsigned long id, unsigned int blksize);
	std::string readingsRetrieve(const std::string& payload);
	unsigned int readingsPurge(unsigned long age, unsigned int flags, unsigned long sent);
	void PluginRelease(const std::string& payload);

private:
  PLUGIN_HANDLE instance;
  bool    (*commonInsertPtr)(PLUGIN_HANDLE, const char *, const char *);
  std::string (*commonRetrievePtr)(PLUGIN_HANDLE, const char *, const char *);
  std::string (*commonUpdatePtr)(PLUGIN_HANDLE, const char *, const char *);
  bool (*commonDeletePtr)(PLUGIN_HANDLE, const char *, const char *);
  bool  (*readingsAppendPtr)(PLUGIN_HANDLE, const char *);
	std::string (*readingsFetchPtr)(PLUGIN_HANDLE, unsigned long id, unsigned int blksize);
	std::string (*readingsRetrievePtr)(PLUGIN_HANDLE, const char *payload);
	unsigned int (*readingsPurgePtr)(PLUGIN_HANDLE, unsigned long age, unsigned int flags, unsigned long sent);
	void (*releasePtr)(PLUGIN_HANDLE, const char *payload);
};

#endif
