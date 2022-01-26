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

/*
 * - poolSize                  Number of connections to allocate
 * - nReadingsPerDb            Number of readings tables per database
 * - nDbPreallocate            Number of databases to allocate in advance
 * - nDbLeftFreeBeforeAllocate Number of free databases before a new allocation is executed
 * - nDbToAllocate             Number of database to allocate each time
 *
 */
typedef struct
{
	int poolSize = 5;
	int nReadingsPerDb = 14;
	int nDbPreallocate = 3;
	int nDbLeftFreeBeforeAllocate = 1;
	int nDbToAllocate = 2;

} STORAGE_CONFIGURATION;

/*
 * Implements the handling of multiples readings tables spreaded among multiple SQLite databases.
 *
 * The databases are named using the format readings_<dbid>, like for example readings_1.db
 * and each database contains multiples readings named as readings_<dbid>_<id> like readings_1_1
 *
 * The table asset_reading_catalogue is used as a catalogue in order map a particular asset_code
 * to a table that holds readings for that asset_code.
 *
 * The first reading table readings_1_1 is created by the script init_readings.sql executed during the storage init
 * all the other readings tables are created by the code when Fledge starts.
 *
 * The table configuration_readings created by the script init_readings.sql keeps track of the information:
 *
 * - global_id         -- Stores the last global Id used +1, Updated at -1 when Fledge starts, Updated at the proper value when Fledge stops
 * - db_id_Last        -- Latest database available
 * - n_readings_per_db -- Number of readings table per database
 * - n_db_preallocate  -- Number of databases to allocate in advance
 *
 * The readings tables are allocated in sequence starting from the readings_1_1 and proceeding with the other tables available in the first database.
 * The tables in the 2nd database (readings_2.db) will be used when all the tables in the first db are allocated.
 *
 */
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