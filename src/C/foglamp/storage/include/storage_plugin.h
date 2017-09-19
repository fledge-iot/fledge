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
  bool    (*commonInsertPtr)(const char *, const char *);
  std::string (*commonRetrievePtr)(const char *, const char *);
  std::string (*commonUpdatePtr)(const char *, const char *);
  bool (*commonDeletePtr)(const char *, const char *);
  bool  (*readingsAppendPtr)(const char *);
	std::string (*readingsFetchPtr)(unsigned long id, unsigned int blksize);
	std::string (*readingsRetrievePtr)(const char *payload);
	unsigned int (*readingsPurgePtr)(unsigned long age, unsigned int flags, unsigned long sent);
	void (*releasePtr)(const char *payload);
};

#endif
