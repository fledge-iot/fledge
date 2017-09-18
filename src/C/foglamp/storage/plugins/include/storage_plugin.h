#ifndef _STORAGE_PLUGIN
#define _STORAGE_PLUGIN

#include <plugin.h>

/**
 * Class that represents a storage plugin.
 */
class StoragePlugins : public Plugin {

public:
	StoragePlugin(PLUGIN_HANDLE handle);
	~StoragePlugin();

	boolean commonInsert(string table, string payload);
	string commonRetrieve(string table, string payload);
	string commonUpdate(string table, string payload);
	boolean commonDelete(string table, string payload);
	boolean readingsAppend(string payload);
	string readingsFetch(unsigned long id, unsinged int blksize);
	string readingsRetrieve(string payload);
	unsigned int readingsPurge(unsigned long age, unsigned int flags, unsigned long sent);
	void PluginRelease(string payload);
}

#endif
