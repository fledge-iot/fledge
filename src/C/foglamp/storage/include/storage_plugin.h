#ifndef _STORAGE_PLUGIN
#define _STORAGE_PLUGIN
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

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

	bool		commonInsert(const std::string& table, const std::string& payload);
	char		*commonRetrieve(const std::string& table, const std::string& payload);
	char		*commonUpdate(const std::string& table, const std::string& payload);
	bool		commonDelete(const std::string& table, const std::string& payload);
	bool		readingsAppend(const std::string& payload);
	char		*readingsFetch(unsigned long id, unsigned int blksize);
	char		*readingsRetrieve(const std::string& payload);
	unsigned int	readingsPurge(unsigned long age, unsigned int flags, unsigned long sent);
	void		release(const char *response);
	PLUGIN_ERROR	*lastError();

private:
	PLUGIN_HANDLE	instance;
	bool		(*commonInsertPtr)(PLUGIN_HANDLE, const char *, const char *);
	char		*(*commonRetrievePtr)(PLUGIN_HANDLE, const char *, const char *);
	char		*(*commonUpdatePtr)(PLUGIN_HANDLE, const char *, const char *);
	bool		(*commonDeletePtr)(PLUGIN_HANDLE, const char *, const char *);
	bool		(*readingsAppendPtr)(PLUGIN_HANDLE, const char *);
	char		*(*readingsFetchPtr)(PLUGIN_HANDLE, unsigned long id, unsigned int blksize);
	char		*(*readingsRetrievePtr)(PLUGIN_HANDLE, const char *payload);
	unsigned int	(*readingsPurgePtr)(PLUGIN_HANDLE, unsigned long age, unsigned int flags, unsigned long sent);
	void		(*releasePtr)(PLUGIN_HANDLE, const char *payload);
	PLUGIN_ERROR	*(*lastErrorPtr)(PLUGIN_HANDLE);
};

#endif
