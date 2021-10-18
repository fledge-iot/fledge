#ifndef _READINGS_CATALOGUE_H
#define _READINGS_CATALOGUE_H
/*
 * Fledge storage service - Readings catalogue handling
 *
 * Copyright (c) 2020 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include "connection.h"

using namespace std;
using namespace rapidjson;


typedef struct
{
	int poolSize = 5;                           // Number of connections to allocate
	int nReadingsPerDb = 14;                    // Number of readings tables per database
	int nDbPreallocate = 3;                     // Number of databases to allocate in advance
	int nDbLeftFreeBeforeAllocate = 1;          // Number of free databases before a new allocation is executed
	int nDbToAllocate = 2;                      // Number of database to allocate each time

} STORAGE_CONFIGURATION;


class ReadingsCatalogue {

public:
	typedef struct ReadingReference {
		int dbId;
		int tableId;

	} tyReadingReference;

	static ReadingsCatalogue *getInstance()
	{
		static ReadingsCatalogue *instance = 0;

		if (!instance)
		{
			instance = new ReadingsCatalogue;
		}
		return instance;
	}

	void          multipleReadingsInit(STORAGE_CONFIGURATION &storageConfig);
	std::string   generateDbAlias(int dbId);
	std::string   generateDbName(int tableId);
	std::string   generateDbFileName(int dbId);
	std::string   generateDbNameFromTableId(int tableId);
	std::string   generateReadingsName(int  dbId, int tableId);
	void          getAllDbs(std::vector<int> &dbIdList);
	void          getNewDbs(std::vector<int> &dbIdList);
	int           getMaxReadingsId(int dbId);
	int           getReadingsCount();
	int           getReadingPosition(int dbId, int tableId);
	int           getNReadingsAvailable() const      {return m_nReadingsAvailable;}
	int           getIncGlobalId() {return m_ReadingsGlobalId++;};
	int           getMinGlobalId (sqlite3 *dbHandle);
	int           getGlobalId() {return m_ReadingsGlobalId;};
	bool          evaluateGlobalId();
	bool          storeGlobalId ();

	void          preallocateReadingsTables(int dbId);
	bool          loadAssetReadingCatalogue();

	bool          latestDbUpdate(sqlite3 *dbHandle, int newDbId);
	void          preallocateNewDbsRange(int dbIdStart, int dbIdEnd);
	tyReadingReference getReadingReference(Connection *connection, const char *asset_code);
	bool          attachDbsToAllConnections();
	std::string   sqlConstructMultiDb(std::string &sqlCmdBase, std::vector<std::string>  &assetCodes, bool considerExclusion=false);
	int           purgeAllReadings(sqlite3 *dbHandle, const char *sqlCmdBase, char **errMsg = NULL, unsigned long *rowsAffected = NULL);

	bool          connectionAttachAllDbs(sqlite3 *dbHandle);
	bool          connectionAttachDbList(sqlite3 *dbHandle, std::vector<int> &dbIdList);
	bool          attachDb(sqlite3 *dbHandle, std::string &path, std::string &alias);
	void          detachDb(sqlite3 *dbHandle, std::string &alias);

	void          setUsedDbId(int dbId);
	int           extractReadingsIdFromName(std::string tableName);
	int           extractDbIdFromName(std::string tableName);



private:
	STORAGE_CONFIGURATION m_storageConfigCurrent;                           // The current configuration of the multiple readings
	STORAGE_CONFIGURATION m_storageConfigApi;                               // The parameters retrieved from the API

	enum NEW_DB_OPERATION {
		NEW_DB_ATTACH_ALL,
		NEW_DB_ATTACH_REQUEST,
		NEW_DB_DETACH
	};

	enum ACTION  {
		ACTION_DB_ADD,
		ACTION_DB_REMOVE,
		ACTION_DB_NONE,
		ACTION_TB_ADD,
		ACTION_TB_REMOVE,
		ACTION_TB_NONE,
		ACTION_INVALID
	};

	typedef struct ReadingAvailable {
		int lastReadings;
		int tableCount;

	} tyReadingsAvailable;

	ReadingsCatalogue(){};

	bool          createNewDB(sqlite3 *dbHandle, int newDbId,  int startId, NEW_DB_OPERATION attachAllDb);
	int           getUsedTablesDbId(int dbId);
	int           getNReadingsAllocate() const {return m_storageConfigCurrent.nReadingsPerDb;}
	bool          createReadingsTables(sqlite3 *dbHandle, int dbId, int idStartFrom, int nTables);
	bool          isReadingAvailable() const;
	void          allocateReadingAvailable();
	tyReadingsAvailable   evaluateLastReadingAvailable(sqlite3 *dbHandle, int dbId);
	int           calculateGlobalId (sqlite3 *dbHandle);
	std::string   generateDbFilePah(int dbId);

	void		  raiseError(const char *operation, const char *reason,...);
	int			  SQLStep(sqlite3_stmt *statement);
	int           SQLExec(sqlite3 *dbHandle, const char *sqlCmd,  char **errMsg = NULL);
	bool          enableWAL(std::string &dbPathReadings);

	bool          configurationRetrieve(sqlite3 *dbHandle);
	void          prepareAllDbs();
	bool          applyStorageConfigChanges(sqlite3 *dbHandle);
	void          dbFileDelete(std::string dbPath);
	void          dbsRemove(int startId, int endId);
	void          storeReadingsConfiguration (sqlite3 *dbHandle);
	ACTION        changesLogicDBs(int dbIdCurrent , int dbIdLast, int nDbPreallocateCurrent, int nDbPreallocateRequest, int nDbLeftFreeBeforeAllocate);
	ACTION           changesLogicTables(int maxUsed ,int Current, int Request);
	int           retrieveDbIdFromTableId(int tableId);

	void          configChangeAddDb(sqlite3 *dbHandle);
	void          configChangeRemoveDb(sqlite3 *dbHandle);
	void          configChangeAddTables(sqlite3 *dbHandle , int startId, int endId);
	void          configChangeRemoveTables(sqlite3 *dbHandle , int startId, int endId);

	int           calcMaxReadingUsed();
	void          dropReadingsTables(sqlite3 *dbHandle, int dbId, int idStart, int idEnd);


	int                                           m_dbIdCurrent;            // Current database in use
	int                                           m_dbIdLast;               // Last database available not already in use
	int                                           m_dbNAvailable;           // Number of databases available
	std::vector<int>                              m_dbIdList;               // Databases already created but not in use

	std::atomic<int>                              m_ReadingsGlobalId;       // Global row id shared among all the readings table
	int                                           m_nReadingsAvailable = 0; // Number of readings tables available
	std::map <std::string, std::pair<int, int>>   m_AssetReadingCatalogue={ // In memory structure to identify in which database/table an asset is stored

		// asset_code  - reading Table Id, Db Id
		// {"",         ,{1               ,1 }}
	};

};

// Used to synchronize the attach database operation
class AttachDbSync {

public:
	static AttachDbSync *getInstance()
	{
		static AttachDbSync instance;
		return &instance;
	}

	void   lock()    {m_dbLock.lock();}
	void   unlock()  {m_dbLock.unlock();}

private:
	AttachDbSync(){};

	std::mutex m_dbLock;
};

#endif