#ifndef _STORAGE_PLUGIN
#define _STORAGE_PLUGIN
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <plugin.h>
#include <plugin_manager.h>
#include <string>
#include <reading_stream.h>
#include <plugin_configuration.h>

#define	STORAGE_PURGE_RETAIN_ANY 0x0001U
#define	STORAGE_PURGE_RETAIN_ALL 0x0002U
#define STORAGE_PURGE_SIZE	     0x0004U

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
	StoragePlugin(const std::string& name, PLUGIN_HANDLE handle);
	~StoragePlugin();

	int		commonInsert(const std::string& table, const std::string& payload, const char *schema = nullptr);
	char		*commonRetrieve(const std::string& table, const std::string& payload, const char *schema = nullptr);
	int		commonUpdate(const std::string& table, const std::string& payload, const char *schema = nullptr);
	int		commonDelete(const std::string& table, const std::string& payload, const char *schema = nullptr);
	int		readingsAppend(const std::string& payload);
	char		*readingsFetch(unsigned long id, unsigned int blksize);
	char		*readingsRetrieve(const std::string& payload);
	char		*readingsPurge(unsigned long age, unsigned int flags, unsigned long sent);
	long		*readingsPurge();
	char		*readingsPurgeAsset(const std::string& asset);
	void		release(const char *response);
	int		createTableSnapshot(const std::string& table, const std::string& id);
	int		loadTableSnapshot(const std::string& table, const std::string& id);
	int		deleteTableSnapshot(const std::string& table, const std::string& id);
	char		*getTableSnapshots(const std::string& table);
	PLUGIN_ERROR	*lastError();
	bool		hasStreamSupport() { return readingStreamPtr != NULL; };
	int		readingStream(ReadingStream **stream, bool commit);
	bool		pluginShutdown();
	int 		createSchema(const std::string& payload);
	StoragePluginConfiguration
			*getConfig() { return m_config; };
	const std::string
			&getName() { return m_name; };

private:
	PLUGIN_HANDLE	instance;
	int		(*commonInsertPtr)(PLUGIN_HANDLE, const char *, const char *) = nullptr;
	char		*(*commonRetrievePtr)(PLUGIN_HANDLE, const char *, const char *) = nullptr;
	int		(*commonUpdatePtr)(PLUGIN_HANDLE, const char *, const char *) = nullptr;
	int		(*commonDeletePtr)(PLUGIN_HANDLE, const char *, const char *) = nullptr;
	int             (*storageSchemaInsertPtr)(PLUGIN_HANDLE, const char *, const char *, const char*) = nullptr;
	char            *(*storageSchemaRetrievePtr)(PLUGIN_HANDLE, const char *, const char *, const char*) = nullptr;
        int             (*storageSchemaUpdatePtr)(PLUGIN_HANDLE, const char *, const char *, const char*) = nullptr;
        int             (*storageSchemaDeletePtr)(PLUGIN_HANDLE, const char *, const char *, const char*) = nullptr;
	int		(*readingsAppendPtr)(PLUGIN_HANDLE, const char *);
	char		*(*readingsFetchPtr)(PLUGIN_HANDLE, unsigned long id, unsigned int blksize);
	char		*(*readingsRetrievePtr)(PLUGIN_HANDLE, const char *payload);
	char		*(*readingsPurgePtr)(PLUGIN_HANDLE, unsigned long age, unsigned int flags, unsigned long sent);
	unsigned int	(*readingsPurgeAssetPtr)(PLUGIN_HANDLE, const char *asset);
	void		(*releasePtr)(PLUGIN_HANDLE, const char *payload);
	int		(*createTableSnapshotPtr)(PLUGIN_HANDLE, const char *, const char *);
	int		(*loadTableSnapshotPtr)(PLUGIN_HANDLE, const char *, const char *);
	int		(*deleteTableSnapshotPtr)(PLUGIN_HANDLE, const char *, const char *);
	char		*(*getTableSnapshotsPtr)(PLUGIN_HANDLE, const char *);
	int		(*readingStreamPtr)(PLUGIN_HANDLE, ReadingStream **, bool);
	PLUGIN_ERROR	*(*lastErrorPtr)(PLUGIN_HANDLE);
	bool		(*pluginShutdownPtr)(PLUGIN_HANDLE);
        int 		(*createSchemaPtr)(PLUGIN_HANDLE, const char*);
	std::string	m_name;
	StoragePluginConfiguration
			*m_config;
	bool 		m_bStorageSchemaFlag = false;
};

#endif
