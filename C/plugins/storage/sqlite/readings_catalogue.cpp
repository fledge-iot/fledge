/*
 * Fledge storage service - Readings catalogue handling
 *
 * Copyright (c) 2020 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli, Massimiliano Pinto
 */

#include <vector>
#include <algorithm>
#include <utils.h>
#include <sys/stat.h>
#include <libgen.h>

#include <string_utils.h>
#include <connection.h>
#include <connection_manager.h>
#include <sqlite_common.h>
#include "readings_catalogue.h"
#include <purge_configuration.h>

using namespace std;
using namespace rapidjson;

// Log set, clear and get of transaction boundaries
#define LOG_TX_BOUNDARIES 0

/**
 * Constructor
 *
 * This is never explicitly called as the ReadingsCatalogue is a
 * singleton class.
 */
ReadingsCatalogue::ReadingsCatalogue() : m_nextOverflow(1), m_maxOverflowUsed(0)
{
}

/**
 * Logs an error. A variable argument function that
 * uses a printf format string to log an error message with the
 * associated operation.
 *
 * @param operation	The operastion in progress
 * @param reason	A printf format string with the error message text
 */
void ReadingsCatalogue::raiseError(const char *operation, const char *reason, ...)
{
	char	tmpbuf[512];

	va_list ap;
	va_start(ap, reason);
	vsnprintf(tmpbuf, sizeof(tmpbuf), reason, ap);
	va_end(ap);
	Logger::getLogger()->error("ReadingsCatalogues: %s during operation %s", tmpbuf, operation);
}

/**
 * Retrieve the information from the persistent storage:
 *     global id
 *     last created database
 *
 * @param dbHandle Database connection to use for the operations
 *
 */
bool ReadingsCatalogue::configurationRetrieve(sqlite3 *dbHandle)
{
	string sql_cmd;
	int rc;
	int id;
	int nCols;
	sqlite3_stmt *stmt;

	// Retrieves the global_id from thd DB
	sql_cmd = " SELECT global_id, db_id_Last, n_readings_per_db, n_db_preallocate FROM " READINGS_DB ".configuration_readings ";

	if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
	{
		raiseError("configurationRetrieve", sqlite3_errmsg(dbHandle));
		return false;
	}

	if (SQLStep(stmt) != SQLITE_ROW)
	{
		m_ReadingsGlobalId = 1;
		m_dbIdLast = 0;

		m_storageConfigCurrent.nReadingsPerDb = m_storageConfigApi.nReadingsPerDb;
		m_storageConfigCurrent.nDbPreallocate = m_storageConfigApi.nDbPreallocate;

		sql_cmd = " INSERT INTO " READINGS_DB ".configuration_readings VALUES (" + to_string(m_ReadingsGlobalId) + ","
				  + to_string(m_dbIdLast)              + ","
				  + to_string(m_storageConfigCurrent.nReadingsPerDb) + ","
				  + to_string(m_storageConfigCurrent.nDbPreallocate) + ")";
		if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
		{
			raiseError("configurationRetrieve", sqlite3_errmsg(dbHandle));
			return false;
		}
	}
	else
	{
		nCols = sqlite3_column_count(stmt);
		m_ReadingsGlobalId = sqlite3_column_int64(stmt, 0);
		m_dbIdLast = sqlite3_column_int(stmt, 1);
		m_storageConfigCurrent.nReadingsPerDb = sqlite3_column_int(stmt, 2);
		m_storageConfigCurrent.nDbPreallocate = sqlite3_column_int(stmt, 3);
	}
	Logger::getLogger()->debug("configurationRetrieve: ReadingsGlobalId %lu dbIdLast %d ", m_ReadingsGlobalId.load(), m_dbIdLast);

	sqlite3_finalize(stmt);

	return true;
}

/**
 * Retrieves the global id stored in SQLite and if it is not possible
 * it calculates the value from the readings tables executing a max(id) on each table.
 *
 * Once retrieved or calculated,
 * It updates the value into SQlite to -1 to force a calculation at the next plugin init (Fledge starts)
 * in the case the proper value was not stored as the plugin shutdown (when Fledge is stopped) was not called.
 *
 */
bool ReadingsCatalogue::evaluateGlobalId ()
{
	string sql_cmd;
	int rc;
	long id;
	int nCols;
	sqlite3_stmt *stmt;
	sqlite3 *dbHandle;

	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection *connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Evaluate Global ID";
	connection->setUsage(usage);
#endif
	dbHandle = connection->getDbHandle();

	// Retrieves the global_id from thd DB
	sql_cmd = " SELECT global_id FROM " READINGS_DB ".configuration_readings ";

	if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
	{
		raiseError("evaluateGlobalId", sqlite3_errmsg(dbHandle));
		manager->release(connection);
		return false;
	}

	if (SQLStep(stmt) != SQLITE_ROW)
	{
		m_ReadingsGlobalId = 1;

		sql_cmd = " INSERT INTO " READINGS_DB ".configuration_readings VALUES (" + to_string(m_ReadingsGlobalId) + ","
				  + "0" + ","
				  + to_string(m_storageConfigApi.nReadingsPerDb) + ","
				  + to_string(m_storageConfigApi.nDbPreallocate) + ")";

		if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
		{
			raiseError("evaluateGlobalId", sqlite3_errmsg(dbHandle));
			manager->release(connection);
			return false;
		}
	}
	else
	{
		nCols = sqlite3_column_count(stmt);
		m_ReadingsGlobalId = sqlite3_column_int64(stmt, 0);
	}

	id = m_ReadingsGlobalId;
	Logger::getLogger()->debug("evaluateGlobalId - global id from the DB %lu", id);

	if (m_ReadingsGlobalId == -1)
	{
		m_ReadingsGlobalId = calculateGlobalId (dbHandle);
	}

	id = m_ReadingsGlobalId;
	Logger::getLogger()->debug("evaluateGlobalId - global id from the DB %lu", id);

	// Set the global_id in the DB to -1 to force a calculation at the restart
	// in case the shutdown is not executed and the proper value stored
	sql_cmd = " UPDATE " READINGS_DB ".configuration_readings SET global_id=-1;";

	if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
	{
		raiseError("evaluateGlobalId", sqlite3_errmsg(dbHandle));
		manager->release(connection);
		return false;
	}

	sqlite3_finalize(stmt);
	manager->release(connection);

	return true;
}

/**
 * Stores the global id into SQlite
 *
 */
bool ReadingsCatalogue::storeGlobalId ()
{
	string sql_cmd;
	int rc;
	int id;
	int nCols;
	sqlite3_stmt *stmt;
	sqlite3 *dbHandle;

	unsigned long i;
	i = m_ReadingsGlobalId;
	Logger::getLogger()->debug("storeGlobalId m_globalId %lu ", i);


	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection *connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Store Global ID";
	connection->setUsage(usage);
#endif
	dbHandle = connection->getDbHandle();

	sql_cmd = " UPDATE " READINGS_DB ".configuration_readings SET global_id=" + to_string(m_ReadingsGlobalId);

	if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
	{
		raiseError("storeGlobalId", sqlite3_errmsg(dbHandle));
		manager->release(connection);
		return false;
	}

	manager->release(connection);

	return true;
}

/**
 * Calculates the value from the readings tables executing a max(id) on each table.
 *
 * @param dbHandle Database connection to use for the operations
 *
 */
long ReadingsCatalogue::calculateGlobalId (sqlite3 *dbHandle)
{
	string sql_cmd;
	string dbReadingsName;
	string dbName;

	int rc;
	unsigned long id;
	int nCols;

	sqlite3_stmt *stmt;
	id = 1;

	// Prepare the sql command to calculate the global id from the rows in the DB
	sql_cmd = R"(
		SELECT
			max(id) id
		FROM
		(
	)";

	bool firstRow = true;
	if (m_AssetReadingCatalogue.empty())
	{
		string dbReadingsName = generateReadingsName(1, 1);

		sql_cmd += " SELECT max(id) id FROM " READINGS_DB "." + dbReadingsName + " ";
	}
	else
	{
		for (auto &item : m_AssetReadingCatalogue)
		{
			if (item.second.getTable() != 0)
			{
				if (!firstRow)
				{
					sql_cmd += " UNION ";
				}

				dbName = generateDbName(item.second.getDatabase());
				dbReadingsName = generateReadingsName(item.second.getDatabase(), item.second.getTable());

				sql_cmd += " SELECT max(id) id FROM " + dbName + "." + dbReadingsName + " ";
				firstRow = false;
			}
		}
		// Now add overflow tables
		for (int i = 1; i <= m_maxOverflowUsed; i++)
		{
			if (!firstRow)
			{
				sql_cmd += " UNION ";
			}
			dbName = generateDbName(i);
			dbReadingsName = generateReadingsName(i, 0);
			sql_cmd += " SELECT max(id) id FROM " + dbName + "." + dbReadingsName + " ";
			firstRow = false;
		}
	}
	sql_cmd += ") AS tb";


	if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
	{
		raiseError("calculateGlobalId", sqlite3_errmsg(dbHandle));
		return false;
	}

	if (SQLStep(stmt) != SQLITE_ROW)
	{
		raiseError("calculateGlobalId SQLStep", sqlite3_errmsg(dbHandle));
		id = 1;
	}
	else
	{
		nCols = sqlite3_column_count(stmt);
		id = sqlite3_column_int64(stmt, 0);
		// m_globalId stores then next value to be used
		id++;
	}

	Logger::getLogger()->debug("calculateGlobalId - global id evaluated %d", id);
	sqlite3_finalize(stmt);

	return (id);
}

/**
 *  Calculates the minimum id from the readings tables executing a min(id) on each table
 *
 * @param dbHandle Database connection to use for the operations
 *
 */
long ReadingsCatalogue::getMinGlobalId (sqlite3 *dbHandle)
{
	string sql_cmd;
	string dbReadingsName;
	string dbName;

	int rc;
	unsigned long id;
	int nCols;

	sqlite3_stmt *stmt;
	id = 1;

	// Prepare the sql command to calculate the global id from the rows in the DB
	{
		sql_cmd = R"(
			SELECT
				min(id) id
			FROM
			(
		)";

		bool firstRow = true;
		if (m_AssetReadingCatalogue.empty())
		{
			string dbReadingsName = generateReadingsName(1, 1);

			sql_cmd += " SELECT min(id) id FROM " READINGS_DB "." + dbReadingsName + " ";
		}
		else
		{
			for (auto &item : m_AssetReadingCatalogue)
			{
				if (item.second.getTable() != 0)
				{
					if (!firstRow)
					{
						sql_cmd += " UNION ";
					}

					dbName = generateDbName(item.second.getDatabase());
					dbReadingsName = generateReadingsName(item.second.getDatabase(), item.second.getTable());

					sql_cmd += " SELECT min(id) id FROM " + dbName + "." + dbReadingsName + " ";
					firstRow = false;
				}
			}
			// Now add overflow tables
			for (int i = 1; i <= m_maxOverflowUsed; i++)
			{
				if (!firstRow)
				{
					sql_cmd += " UNION ";
				}
				dbName = generateDbName(i);
				dbReadingsName = generateReadingsName(i, 0);
				sql_cmd += " SELECT min(id) id FROM " + dbName + "." + dbReadingsName + " ";
				firstRow = false;
			}
		}
		sql_cmd += ") AS tb";
	}

	if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
	{
		raiseError(__FUNCTION__, sqlite3_errmsg(dbHandle));
		return false;
	}

	if (SQLStep(stmt) != SQLITE_ROW)
	{
		id = 0;
	}
	else
	{
		nCols = sqlite3_column_count(stmt);
		id = sqlite3_column_int64(stmt, 0);
	}

	Logger::getLogger()->debug("%s - global id evaluated %lu", __FUNCTION__, id);

	sqlite3_finalize(stmt);

	return (id);
}

/**
 * Loads the reading catalogue stored in SQLite into an in memory structure
 *
 */
bool  ReadingsCatalogue::loadAssetReadingCatalogue()
{
	int nCols;
	int tableId, dbId, maxDbID;
	char *asset_name;
	sqlite3_stmt *stmt;
	int rc;
	sqlite3		*dbHandle;

	ostringstream threadId;
	threadId << std::this_thread::get_id();

	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection        *connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Load Asset Reading Catalogue";
	connection->setUsage(usage);
#endif
	dbHandle = connection->getDbHandle();

	// loads readings catalog from the db
	const char *sql_cmd = R"(
		SELECT
			table_id,
			db_id,
			asset_code
		FROM  )" READINGS_DB R"(.asset_reading_catalogue
		ORDER BY table_id;
	)";


	maxDbID = 1;
	if (sqlite3_prepare_v2(dbHandle,sql_cmd,-1, &stmt,NULL) != SQLITE_OK)
	{
		raiseError("retrieve asset_reading_catalogue", sqlite3_errmsg(dbHandle));
		manager->release(connection);
		return false;
	}
	else
	{
		// Iterate over all the rows in the resultSet
		while ((rc = SQLStep(stmt)) == SQLITE_ROW)
		{
			nCols = sqlite3_column_count(stmt);

			tableId = sqlite3_column_int(stmt, 0);
			dbId = sqlite3_column_int(stmt, 1);
			asset_name = (char *)sqlite3_column_text(stmt, 2);

			if (dbId > maxDbID)
				maxDbID = dbId;

			Logger::getLogger()->debug("loadAssetReadingCatalogue - thread '%s' reading Id %d dbId %d asset name '%s' max db Id %d", threadId.str().c_str(), tableId, dbId,  asset_name, maxDbID);

			auto newMapValue = make_pair(asset_name,TableReference(dbId, tableId));
			m_AssetReadingCatalogue.insert(newMapValue);
			if (tableId == 0 && dbId > m_maxOverflowUsed)	// Overflow
			{
				m_maxOverflowUsed = dbId;
			}

		}

		sqlite3_finalize(stmt);
	}
	manager->release(connection);
	m_dbIdCurrent = maxDbID;

	Logger::getLogger()->debug("loadAssetReadingCatalogue maxdb %d", m_dbIdCurrent);

	return true;
}

/**
 * Add the newly create db to the list
 *
 */
void ReadingsCatalogue::setUsedDbId(int dbId)
{
	m_dbIdList.push_back(dbId);
}

/**
 * Preallocate all the required databases:
 *
 *  - Initial stage  - creates the databases requested by the preallocation
 *  - Following runs - attaches all the databases already created
 *
 */
void ReadingsCatalogue::prepareAllDbs()
{

	int dbId, dbIdStart, dbIdEnd;

	Logger::getLogger()->debug("prepareAllDbs - dbIdCurrent %d dbIdLast %d nDbPreallocate %d", m_dbIdCurrent, m_dbIdLast, m_storageConfigCurrent.nDbPreallocate);

	if (m_dbIdLast == 0)
	{
		Logger::getLogger()->debug("prepareAllDbs - initial stage ");

		// Initial stage - creates the databases requested by the preallocation
		dbIdStart = 2;
		dbIdEnd = dbIdStart + m_storageConfigCurrent.nDbPreallocate - 2;

		int created = preallocateNewDbsRange(dbIdStart, dbIdEnd);
		if (created)
		{
			m_dbIdLast = dbIdStart + created - 1;
		}
	}
	else
	{
		Logger::getLogger()->debug("prepareAllDbs - following runs");

		// Following runs - attaches all the databases
		for (dbId = 2; dbId <= m_dbIdLast ; dbId++ )
		{
			m_dbIdList.push_back(dbId);
		}
		attachDbsToAllConnections();
	}

	m_dbNAvailable = (m_dbIdLast - m_dbIdCurrent) - m_storageConfigCurrent.nDbLeftFreeBeforeAllocate;

	Logger::getLogger()->debug("prepareAllDbs - dbNAvailable %d", m_dbNAvailable);
}

/**
 * Create a set of databases
 *
 * @param    dbIdStart	Range of the database to create
 * @param    dbIdEnd    Range of the database to create
 * @return   int	The number of datbases created
 *
 */
int ReadingsCatalogue::preallocateNewDbsRange(int dbIdStart, int dbIdEnd) {

	int dbId;
	int startReadingsId;
	tyReadingsAvailable readingsAvailable;
	int created = 0;

	Logger::getLogger()->debug("preallocateNewDbsRange - Id start %d Id end %d ", dbIdStart, dbIdEnd);

	for (dbId = dbIdStart; dbId <= dbIdEnd; dbId++)
	{
		readingsAvailable = evaluateLastReadingAvailable(NULL, dbId - 1);
		startReadingsId = 1;
		if (!createNewDB(NULL,  dbId, startReadingsId, NEW_DB_ATTACH_ALL))
		{
			Logger::getLogger()->error("Failed to preallocated all databases, terminated after creating %d databases", created);
			break;
		}
		else
		{
			created++;
		}

		Logger::getLogger()->debug("preallocateNewDbsRange - db created %d startReadingsIdOnDB %d", dbId, startReadingsId);
	}
	return created;
}

/**
 * Generates a list of all the used databases. Note this list does not include
 * the first database, readings_1, onl the ohtes that have been added.
 *
 * @param    dbIdList	returned by reference, the list databases in use
 *
 */
void ReadingsCatalogue::getAllDbs(vector<int> &dbIdList)
{

	int dbId;

	Logger::getLogger()->debug("getAllDbs - used db");

	for (auto &item : m_AssetReadingCatalogue) {

		dbId = item.second.getDatabase();
		if (dbId > 1)
		{
			if (std::find(dbIdList.begin(), dbIdList.end(), dbId) ==  dbIdList.end() )
			{
				dbIdList.push_back(dbId);
				Logger::getLogger()->debug("getAllDbs  DB %d", dbId);
			}

		}
	}

	Logger::getLogger()->debug("getAllDbs - created db");

	for (auto &dbId : m_dbIdList) {

		if (std::find(dbIdList.begin(), dbIdList.end(), dbId) ==  dbIdList.end() )
		{
			dbIdList.push_back(dbId);
			Logger::getLogger()->debug("getAllDbs DB created %d", dbId);
		}
	}

	sort(dbIdList.begin(), dbIdList.end());
}

/**
 * Retrieve the list of newly created databases
 *
 * @param    dbIdList	returned by reference, the list of new databases
 *
 */
void ReadingsCatalogue::getNewDbs(vector<int> &dbIdList) {

	int dbId;

	for (auto &dbId : m_dbIdList) {

		if (std::find(dbIdList.begin(), dbIdList.end(), dbId) ==  dbIdList.end() )
		{
			dbIdList.push_back(dbId);
			Logger::getLogger()->debug("getNewDbs - dbId %d", dbId);
		}
	}

	sort(dbIdList.begin(), dbIdList.end());
}

/**
 * Enable WAL mode on the given database file. This method will open and then
 * close the database and does not use any existing connection.
 *
 * @param    dbPathReadings	Database path for which the WAL must be enabled
 *
 */
bool ReadingsCatalogue::enableWAL(string &dbPathReadings) {

	int rc;
	sqlite3 *dbHandle;

	Logger::getLogger()->debug("enableWAL on '%s'", dbPathReadings.c_str());

	rc = sqlite3_open(dbPathReadings.c_str(), &dbHandle);
	if(rc != SQLITE_OK)
	{
		raiseError("enableWAL", sqlite3_errmsg(dbHandle));
		return false;
	}
	else
	{
		// Enables the WAL feature
		rc = sqlite3_exec(dbHandle, DB_CONFIGURATION, NULL, NULL, NULL);
		if (rc != SQLITE_OK)
		{
			raiseError("enableWAL", sqlite3_errmsg(dbHandle));
			return false;
		}
	}
	sqlite3_close(dbHandle);
	return true;
}

/**
 * Attach a database to the database connection passed to the call
 *
 * @param dbHandle Database connection to use for the operations
 * @param path     path of the database to attach
 * @param alias    alias to be assigned to the attached database
 * @param id	   the database ID
 */
bool ReadingsCatalogue::attachDb(sqlite3 *dbHandle, std::string &path, std::string &alias, int id)
{
int 	rc;
string	sqlCmd;
bool	result = true;
char	*zErrMsg = NULL;

	sqlCmd = "ATTACH DATABASE '" + path + "' AS " + alias + ";";

	Logger::getLogger()->debug("attachDb  - path '%s' alias '%s' cmd '%s'" , path.c_str(), alias.c_str() , sqlCmd.c_str() );
	rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
	if (rc != SQLITE_OK)
	{
		Logger::getLogger()->error("Failed to attach the db '%s' to the connection %X, error '%s'", path.c_str(), dbHandle, zErrMsg);
		sqlite3_free(zErrMsg);
		result = false;
	}

	// See if the overflow table exists and if not create it
	// This is a workaround as the schema update mechanism can't cope
	// with multiple readings tables
	createReadingsOverflowTable(dbHandle, id);

	return result;
}

/**
 * Detach a database from a connection
 *
 * @param dbHandle Database connection to use for the operations*
 * @param alias    alias of the database to detach
 */
void ReadingsCatalogue::detachDb(sqlite3 *dbHandle, std::string &alias)
{
	int rc;
	std::string sqlCmd;
	char *zErrMsg = nullptr;

	sqlCmd = "DETACH  DATABASE " + alias + ";";

	Logger::getLogger()->debug("%s - db '%s' cmd '%s'" ,__FUNCTION__,  alias.c_str() , sqlCmd.c_str() );
	rc = SQLExec (dbHandle, sqlCmd.c_str(), &zErrMsg);
	if (rc != SQLITE_OK)
	{
		Logger::getLogger()->error("%s - It was not possible to detach the db '%s' from the connection %X, error '%s'", __FUNCTION__, alias.c_str(), dbHandle, zErrMsg);
		sqlite3_free(zErrMsg);
	}
}

/**
 * Attaches all the defined SQlite database to all the connections and enable the WAL
 *
 * @param dbHandle Database connection to use for the operations
 * @param dbIdList List of database to attach
 * @return         True of success, false on any error
 *
 */
bool ReadingsCatalogue::connectionAttachDbList(sqlite3 *dbHandle, vector<int> &dbIdList)
{
	int dbId;
	string dbPathReadings;
	string dbAlias;
	int item;

	bool result;

	result = true;

	Logger::getLogger()->debug("connectionAttachDbList - start dbHandle %X" ,dbHandle);

	while (result && !dbIdList.empty())
	{
		item = dbIdList.back();

		dbPathReadings = generateDbFilePath(item);
		dbAlias = generateDbAlias(item);

		Logger::getLogger()->debug(
				"connectionAttachDbList - dbHandle %X dbId %d path %s alias %s",
				dbHandle, item, dbPathReadings.c_str(), dbAlias.c_str());

		result = attachDb(dbHandle, dbPathReadings, dbAlias, item);
		dbIdList.pop_back();

	}

	Logger::getLogger()->debug("connectionAttachDbList - end dbHandle %X" ,dbHandle);

	return result;
}


/**
 * Attaches all the defined SQlite database to all the connections and enable the WAL
 *
 * @param dbHandle Database connection to use for the operations
 * @return         True of success, false on any error
 *
 */
bool ReadingsCatalogue::connectionAttachAllDbs(sqlite3 *dbHandle)
{
	int dbId;
	string dbPathReadings;
	string dbAlias;
	vector<int> dbIdList;
	bool result;

	result = true;

	getAllDbs(dbIdList);

	for(int item : dbIdList)
	{
		dbPathReadings = generateDbFilePath(item);
		dbAlias = generateDbAlias(item);

		result = attachDb(dbHandle, dbPathReadings, dbAlias, item);
		if (! result)
		{
			Logger::getLogger()->error("Unable to attach all databases to the connection");
			break;
		}

		Logger::getLogger()->debug("connectionAttachAllDbs - dbId %d path %s alias %s", item, dbPathReadings.c_str(), dbAlias.c_str());
	}
	return result;
}


/**
 * Attaches all the defined SQlite database to all the connections and enable the WAL
 *
 * @return         True of success, false on any error
 *
 */
bool ReadingsCatalogue::attachDbsToAllConnections()
{
	int dbId;
	string dbPathReadings;
	string dbAlias;
	vector<int> dbIdList;
	bool result;

	result = true;

	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection        *connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Attach DBs to all connections";
	connection->setUsage(usage);
#endif

	getAllDbs(dbIdList);

	for (int item : dbIdList)
	{
		dbPathReadings = generateDbFilePath(item);
		dbAlias = generateDbAlias(item);

		enableWAL(dbPathReadings);
		// Attached the new db to the connections
		result = manager->attachNewDb(dbPathReadings, dbAlias);
		if (! result)
			break;

		Logger::getLogger()->debug("attachDbsToAllConnections - dbId %d path '%s' alias '%s'", item, dbPathReadings.c_str(), dbAlias.c_str());
	}

	manager->release(connection);

	return (result);
}

/**
 * Setup the multiple readings databases/tables feature
 *
 * @param storageConfig Configuration to apply
 *
 */
void ReadingsCatalogue::multipleReadingsInit(STORAGE_CONFIGURATION &storageConfig)
{
	sqlite3 *dbHandle;

	ConnectionManager *manager = ConnectionManager::getInstance();
	Connection *connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Multiple readings init";
	connection->setUsage(usage);
#endif
	if (! connection->supportsReadings())
	{
		manager->release(connection);
		return;
	}
	dbHandle = connection->getDbHandle();

	// Enquire for the attached database limit
	m_attachLimit = sqlite3_limit(dbHandle, SQLITE_LIMIT_ATTACHED, -1);
	Logger::getLogger()->info("The version of SQLite can support %d attached databases",
			m_attachLimit);
	m_compounds = sqlite3_limit(dbHandle, SQLITE_LIMIT_COMPOUND_SELECT, -1);

	if (storageConfig.nDbLeftFreeBeforeAllocate < 1)
	{
		Logger::getLogger()->warn("%s - parameter nDbLeftFreeBeforeAllocate not valid, use a value >= 1, 1 used ", __FUNCTION__);
		storageConfig.nDbLeftFreeBeforeAllocate = 1;
	}
	if (storageConfig.nDbToAllocate < 1)
	{
		Logger::getLogger()->warn("%s - parameter nDbToAllocate not valid, use a value >= 1, 1 used ", __FUNCTION__);
		storageConfig.nDbToAllocate = 1;
	}

	m_storageConfigApi.nReadingsPerDb = storageConfig.nReadingsPerDb;
	m_storageConfigApi.nDbPreallocate = storageConfig.nDbPreallocate;
	m_storageConfigApi.nDbLeftFreeBeforeAllocate = storageConfig.nDbLeftFreeBeforeAllocate;
	m_storageConfigApi.nDbToAllocate = storageConfig.nDbToAllocate;

	m_storageConfigCurrent.nDbLeftFreeBeforeAllocate = storageConfig.nDbLeftFreeBeforeAllocate;
	m_storageConfigCurrent.nDbToAllocate = storageConfig.nDbToAllocate;

	try
	{
		configurationRetrieve(dbHandle);

		loadAssetReadingCatalogue();
		preallocateReadingsTables(1);   // on the first database

		Logger::getLogger()->debug("nReadingsPerDb %d", m_storageConfigCurrent.nReadingsPerDb);
		Logger::getLogger()->debug("nDbPreallocate %d", m_storageConfigCurrent.nDbPreallocate);

		prepareAllDbs();

		applyStorageConfigChanges(dbHandle);

		Logger::getLogger()->debug("multipleReadingsInit - dbIdCurrent %d dbIdLast %d nDbPreallocate current %d requested %d",
								   m_dbIdCurrent,
								   m_dbIdLast,
								   m_storageConfigCurrent.nDbPreallocate,
								   m_storageConfigApi.nDbPreallocate);

		storeReadingsConfiguration(dbHandle);


		preallocateReadingsTables(0);   // on the last database

		evaluateGlobalId();
	}
	catch (exception& e)
	{
		Logger::getLogger()->error("It is not possible to initialize the multiple readings handling, error '%s' ", e.what());
	}

	manager->release(connection);
}


/**
 * Store on the database the configuration of the storage plugin
 *
 * @param dbHandle Database connection to use for the operations
 *
 */
void ReadingsCatalogue::storeReadingsConfiguration (sqlite3 *dbHandle)
{
	string errMsg;
	string sql_cmd;

	Logger::getLogger()->debug("storeReadingsConfiguration - nReadingsPerDb %d nDbPreallocate %d", m_storageConfigCurrent.nReadingsPerDb , m_storageConfigCurrent.nDbPreallocate);

	sql_cmd = " UPDATE " READINGS_DB ".configuration_readings SET n_readings_per_db=" + to_string(m_storageConfigCurrent.nReadingsPerDb) + "," +
			  "n_db_preallocate="  + to_string(m_storageConfigCurrent.nDbPreallocate)  + "," +
			  "db_id_Last="        + to_string(m_dbIdLast)  + ";";

	Logger::getLogger()->debug("sql_cmd '%s'", sql_cmd.c_str());

	if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
	{
		errMsg = "is not possible to store the configuration about the multiple readings handling, error :";
		errMsg += sqlite3_errmsg(dbHandle);
		raiseError("storeReadingsConfiguration", errMsg.c_str());
		throw runtime_error(errMsg.c_str());
	}
}

/**
 * Add all the required DBs in relation to the storage plugin configuration
 *
 * @param dbHandle Database connection to use for the operations
 *
 */
void ReadingsCatalogue::configChangeAddDb(sqlite3 *dbHandle)
{
	string errMsg;
	int dbId;
	int startReadingsId;
	int startId, endId;
	tyReadingsAvailable readingsAvailable;

	startId =  m_dbIdLast +1;
	endId = m_storageConfigApi.nDbPreallocate;

	Logger::getLogger()->debug("configChangeAddDb - dbIdCurrent %d dbIdLast %d nDbPreallocate current %d requested %d",
							   m_dbIdCurrent,
							   m_dbIdLast,
							   m_storageConfigCurrent.nDbPreallocate,
							   m_storageConfigApi.nDbPreallocate);

	Logger::getLogger()->debug("configChangeAddDb - Id start %d Id end %d ", startId, endId);
	int created = 0;

	try
	{
		for (dbId = startId; dbId <= endId; dbId++)
		{
			readingsAvailable = evaluateLastReadingAvailable(dbHandle, dbId - 1);
			if (readingsAvailable.lastReadings == 0)
			{
				errMsg = "Unable to determinate used readings table while adding a database";
				throw runtime_error(errMsg.c_str());
			}

			startReadingsId = readingsAvailable.lastReadings +1;
			if (! createNewDB(dbHandle,  dbId, startReadingsId, NEW_DB_ATTACH_ALL))
			{
				errMsg = "Unable to add a new database";
				throw runtime_error(errMsg.c_str());
			}
			else
			{
				created++;
			}
			Logger::getLogger()->debug("configChangeAddDb - db created %d startReadingsIdOnDB %d", dbId, startReadingsId);
		}
	}
	catch (exception& e)
	{
		Logger::getLogger()->error("It is not possible to add the requested databases, error '%s' - removing created databases", e.what());
		dbsRemove(startId , endId);
	}

	m_dbIdLast = startId + created - 1;
	m_storageConfigCurrent.nDbPreallocate = m_storageConfigApi.nDbPreallocate;
	m_dbNAvailable = (m_dbIdLast - m_dbIdCurrent) - m_storageConfigCurrent.nDbLeftFreeBeforeAllocate;
}

/**
 * Removes all the required DBs in relation to the storage plugin configuration
 *
 * @param dbHandle Database connection to use for the operations
 *
 */
void ReadingsCatalogue::configChangeRemoveDb(sqlite3 *dbHandle)
{
	string errMsg;
	int dbId;
	int startReadingsId;
	tyReadingsAvailable readingsAvailable;
	string dbAlias;
	string dbPath;

	ConnectionManager *manager = ConnectionManager::getInstance();

	Logger::getLogger()->debug("configChangeRemoveDb - dbIdCurrent %d dbIdLast %d nDbPreallocate current %d requested %d",
							   m_dbIdCurrent,
							   m_dbIdLast,
							   m_storageConfigCurrent.nDbPreallocate,
							   m_storageConfigApi.nDbPreallocate);


	Logger::getLogger()->debug("configChangeRemoveDb - Id start %d Id end %d ", m_dbIdCurrent, m_storageConfigApi.nDbPreallocate);

	dbsRemove(m_storageConfigApi.nDbPreallocate + 1, m_dbIdLast);


	m_dbIdLast = m_storageConfigApi.nDbPreallocate;
	m_storageConfigCurrent.nDbPreallocate = m_storageConfigApi.nDbPreallocate;
	m_dbNAvailable = (m_dbIdLast - m_dbIdCurrent) - m_storageConfigCurrent.nDbLeftFreeBeforeAllocate;
}


/**
 * Adds all the required readings tables in relation to the storage plugin configuration
 *
 * @param dbHandle - handle of the connection to use for the database operation
 * @param startId  - range of the readings table to create
 * @param endId    - range of the readings table to create
 *
 */
void ReadingsCatalogue::configChangeAddTables(sqlite3 *dbHandle, int startId, int endId)
{
	int dbId;
	int maxReadingUsed;
	int nTables;

	nTables = endId - startId +1;

	Logger::getLogger()->debug("%s - startId %d endId %d nTables %d",
							   __FUNCTION__,
							   startId,
							   endId,
							   nTables);

	for (dbId = 1; dbId <= m_dbIdLast ; dbId++ )
	{
		Logger::getLogger()->debug("%s - configChangeAddTables - dbId %d startId %d nTables %d",
								   __FUNCTION__,
								   dbId,
								   startId,
								   nTables);
		createReadingsTables(dbHandle, dbId, startId, nTables);
	}

	m_storageConfigCurrent.nReadingsPerDb = m_storageConfigApi.nReadingsPerDb;
	maxReadingUsed = calcMaxReadingUsed();
	m_nReadingsAvailable = m_storageConfigCurrent.nReadingsPerDb - maxReadingUsed;

	Logger::getLogger()->debug("%s - maxReadingUsed %d nReadingsPerDb %d m_nReadingsAvailable %d",
							   __FUNCTION__,
							   maxReadingUsed,
							   m_storageConfigCurrent.nReadingsPerDb,
							   m_nReadingsAvailable);
}

/**
 * Deletes all the required readings tables in relation to the storage plugin configuration
 *
 * @param dbHandle - handle of the connection to use for the database operation
 * @param startId  - range of the readings table to delete
 * @param endId    - range of the readings table to delete
 *
 */
void ReadingsCatalogue::configChangeRemoveTables(sqlite3 *dbHandle, int startId, int endId)
{
	int dbId;
	int maxReadingUsed;

	Logger::getLogger()->debug("%s - startId %d endId %d",
							   __FUNCTION__,
							   startId,
							   endId);

	for (dbId = 1; dbId <= m_dbIdLast ; dbId++ )
	{
		Logger::getLogger()->debug("%s - configChangeRemoveTables - dbId %d startId %d endId %d",
								   __FUNCTION__,
								   dbId,
								   startId,
								   endId);
		dropReadingsTables(dbHandle, dbId, startId, endId);
	}

	m_storageConfigCurrent.nReadingsPerDb = m_storageConfigApi.nReadingsPerDb;
	maxReadingUsed = calcMaxReadingUsed();
	m_nReadingsAvailable = m_storageConfigCurrent.nReadingsPerDb - maxReadingUsed;

	Logger::getLogger()->debug("%s - maxReadingUsed %d nReadingsPerDb %d m_nReadingsAvailable %d",
							   __FUNCTION__,
							   maxReadingUsed,
							   m_storageConfigCurrent.nReadingsPerDb,
							   m_nReadingsAvailable);
}

/**
 * Drops a set of readings
 *
 * @param dbHandle - handle of the connection to use for the database operation
 * @param dbId     - database id on which the tables should be dropped
 * @param startId  - range of the readings table to delete
 * @param endId    - range of the readings table to delete
 *
 */
void  ReadingsCatalogue::dropReadingsTables(sqlite3 *dbHandle, int dbId, int idStart, int idEnd)
{
	string errMsg;
	string dropReadings, dropIdx;
	string dbName;
	string tableName;
	int tableId;
	int rc;
	int idx;
	bool newConnection;

	Logger::getLogger()->debug("%s - dropping tales on database id %dform id %d to %d", __FUNCTION__, dbId, idStart, idEnd);

	dbName = generateDbName(dbId);

	for (idx = idStart ; idx <= idEnd; ++idx)
	{
		tableName = generateReadingsName(dbId, idx);

		dropReadings = "DROP TABLE " + dbName + "." + tableName + ";";
		dropIdx      = "DROP INDEX " + tableName + "_ix3;";


		rc = SQLExec(dbHandle, dropIdx.c_str());
		if (rc != SQLITE_OK)
		{
			errMsg = sqlite3_errmsg(dbHandle);
			raiseError(__FUNCTION__, sqlite3_errmsg(dbHandle));
			throw runtime_error(errMsg.c_str());
		}

		rc = SQLExec(dbHandle, dropReadings.c_str());
		if (rc != SQLITE_OK)
		{
			errMsg = sqlite3_errmsg(dbHandle);
			raiseError(__FUNCTION__, sqlite3_errmsg(dbHandle));
			throw runtime_error(errMsg.c_str());
		}

	}
}

/**
 * Deletes a range of database, detach and delete the file
 *
 * @param startId  - range of the databases to delete
 * @param endId    - range of the databases to delete
 *
 */
void ReadingsCatalogue::dbsRemove(int startId, int endId)
{
	string errMsg;
	int dbId;
	int startReadingsId;
	tyReadingsAvailable readingsAvailable;
	string dbAlias;
	string dbPath;

	ConnectionManager *manager = ConnectionManager::getInstance();

	Logger::getLogger()->debug("dbsRemove - startId %d endId %d", startId, endId);

	for (dbId = startId; dbId <= endId; dbId++)
	{
		dbAlias = generateDbAlias(dbId);
		dbPath  = generateDbFilePath(dbId);

		Logger::getLogger()->debug("dbsRemove - db alias '%s' db path '%s'", dbAlias.c_str(), dbPath.c_str());

		manager->detachNewDb(dbAlias);
		dbFileDelete(dbPath);
	}
}

/**
 * Delete a file
 *
 * @param dbPath  - Full path of the file to delete
 *
 */
void  ReadingsCatalogue::dbFileDelete(string dbPath)
{
	string errMsg;
	bool success;

	Logger::getLogger()->debug("dbFileDelete - db path '%s'", dbPath.c_str());

	if (remove (dbPath.c_str()) !=0)
	{
		errMsg = "Unable to remove database :" + dbPath + ":";
		throw runtime_error(errMsg.c_str());
	}
}

/**
 * Evaluates and applies the storage plugin configuration
 *
 * @param dbHandle handle of the connection to use for the database operations
 *
 */
bool ReadingsCatalogue::applyStorageConfigChanges(sqlite3 *dbHandle)
{
	bool configChanged;
	ACTION operation;
	int maxReadingUsed;

	configChanged = false;

	Logger::getLogger()->debug("applyStorageConfigChanges - dbIdCurrent %d dbIdLast %d nDbPreallocate current %d requested %d nDbLeftFreeBeforeAllocate %d",
							   m_dbIdCurrent,
							   m_dbIdLast,
							   m_storageConfigCurrent.nDbPreallocate,
							   m_storageConfigApi.nDbPreallocate,
							   m_storageConfigCurrent.nDbLeftFreeBeforeAllocate);
	try{

		if (m_storageConfigApi.nDbPreallocate <= 2)
		{
			Logger::getLogger()->warn("applyStorageConfigChanges: parameter nDbPreallocate changed, but it is not possible to apply the change, use a larger value >= 3");
		} else {

			operation = changesLogicDBs(m_dbIdCurrent,
										m_dbIdLast,
										m_storageConfigCurrent.nDbPreallocate,
										m_storageConfigApi.nDbPreallocate,
										m_storageConfigCurrent.nDbLeftFreeBeforeAllocate);

			// Database operation
			{
				if (operation == ACTION_DB_ADD)
				{
					Logger::getLogger()->debug("applyStorageConfigChanges - parameters nDbPreallocate changed, adding more databases from %d to %d", m_dbIdLast, m_storageConfigApi.nDbPreallocate);
					configChanged = true;
					configChangeAddDb(dbHandle);

				} else if (operation == ACTION_INVALID)
				{
					Logger::getLogger()->warn("applyStorageConfigChanges: parameter nDbPreallocate changed, but it is not possible to apply the change as there are already data stored in the database id %d, use a larger value", m_dbIdCurrent);

				} else if (operation == ACTION_DB_REMOVE)
				{
					Logger::getLogger()->debug("applyStorageConfigChanges - parameters nDbPreallocate changed, removing databases from %d to %d", m_storageConfigApi.nDbPreallocate, m_dbIdLast);
					configChanged = true;
					configChangeRemoveDb(dbHandle);
				} else
				{
					Logger::getLogger()->debug("applyStorageConfigChanges - not changes");
				}
			}
		}

		if (m_storageConfigApi.nReadingsPerDb <= 2)
		{
			Logger::getLogger()->warn("applyStorageConfigChanges: parameter nReadingsPerDb changed, but it is not possible to apply the change, use a larger value >= 3");
		} else {

			maxReadingUsed = calcMaxReadingUsed();
			operation = changesLogicTables(maxReadingUsed,
										   m_storageConfigCurrent.nReadingsPerDb,
										   m_storageConfigApi.nReadingsPerDb);

			Logger::getLogger()->debug("%s - maxReadingUsed %d Current %d Requested %d",
									   __FUNCTION__,
									   maxReadingUsed,
									   m_storageConfigCurrent.nReadingsPerDb,
									   m_storageConfigApi.nReadingsPerDb);

			// Table  operation
			{
				if (operation == ACTION_TB_ADD)
				{
					int startId, endId;

					startId = m_storageConfigCurrent.nReadingsPerDb +1;
					endId =  m_storageConfigApi.nReadingsPerDb;

					Logger::getLogger()->debug("applyStorageConfigChanges - parameters nReadingsPerDb changed, adding more tables from %d to %d", startId, endId);
					configChanged = true;
					configChangeAddTables(dbHandle, startId, endId);

				} else if (operation == ACTION_INVALID)
				{
					Logger::getLogger()->warn("applyStorageConfigChanges: parameter nReadingsPerDb changed, but it is not possible to apply the change as there are already data stored in the table id %d, use a larger value", maxReadingUsed);

				} else if (operation == ACTION_TB_REMOVE)
				{
					int startId, endId;

					startId =  m_storageConfigApi.nReadingsPerDb +1;
					endId =  m_storageConfigCurrent.nReadingsPerDb;

					Logger::getLogger()->debug("applyStorageConfigChanges - parameters nReadingsPerDb changed, removing tables from %d to %d", m_storageConfigApi.nReadingsPerDb +1, m_storageConfigCurrent.nReadingsPerDb);
					configChanged = true;
					configChangeRemoveTables(dbHandle, startId, endId);
				} else
				{
					Logger::getLogger()->debug("applyStorageConfigChanges - not changes");
				}
			}
		}


		if ( !configChanged)
			Logger::getLogger()->debug("applyStorageConfigChanges - storage parameters not changed");

	}
	catch (exception& e)
	{
		Logger::getLogger()->error("It is not possible to apply the chnages to the multi readings handling, error '%s' ", e.what());
	}

	return configChanged;
}

/**
 * Calculates the maximum readings id used
 *
 * @return maximum readings id used
 *
 */
int  ReadingsCatalogue::calcMaxReadingUsed()
{
	int maxReading = 0;

	for (auto &item : m_AssetReadingCatalogue)
	{
		if (item.second.getTable() > maxReading)
			maxReading = item.second.getTable();
	}

	return (maxReading);
}

/**
 * Evaluates the operations to be executed in relation to the input parameters on the readings tables
 *
 * @param maxUsed Maximum table id used
 * @param Current Current table id configured
 * @param Request Requested configuration id

 * @return        Operation to execute : ACTION_TB_NONE / ACTION_TB_ADD /ACTION_TB_REMOVE / ACTION_INVALID
 *
 */
ReadingsCatalogue::ACTION  ReadingsCatalogue::changesLogicTables(int maxUsed ,int Current, int Request)
{
	ACTION operation;

	Logger::getLogger()->debug("%s - maxUsed %d Request %d Request current %d",
							   __FUNCTION__,
							   maxUsed,
							   Current,
							   Request);

	operation = ACTION_TB_NONE;

	if (Current != Request)
	{
		if (Request > Current)
		{
			operation = ACTION_TB_ADD;

		}
		else if ((Request < Current) && (maxUsed >= Request))
		{
			operation = ACTION_INVALID;

		} else if ((Request < Current) && (maxUsed < Request))
		{
			operation = ACTION_TB_REMOVE;
		}
	}
	return operation;
}

/**
 * Evaluates the operations to be executed in relation to the input parameters on the databases
 *
 * @param dbIdCurrent               - Current database id in use
 * @param dbIdLast                  - Latest database id created, but necessary in use
 * @param nDbPreallocateCurrent     - Current table id configured
 * @param nDbPreallocateRequest     - Requested configuration id
 * @param nDbLeftFreeBeforeAllocate - Number of database to maintain free

 * @return - Operation to execute : ACTION_DB_NONE / ACTION_DB_ADD / ACTION_DB_REMOVE / ACTION_INVALID
 *
 */
ReadingsCatalogue::ACTION ReadingsCatalogue::changesLogicDBs(int dbIdCurrent , int dbIdLast, int nDbPreallocateCurrent, int nDbPreallocateRequest, int nDbLeftFreeBeforeAllocate)
{
	ACTION operation;

	operation = ACTION_DB_NONE;

	if ( nDbPreallocateCurrent != nDbPreallocateRequest)
	{
		if (nDbPreallocateRequest > dbIdLast)
		{
			operation = ACTION_DB_ADD;

		} else if (nDbPreallocateRequest < (dbIdCurrent + nDbLeftFreeBeforeAllocate) )
		{
			operation = ACTION_INVALID;

		} else if ( (nDbPreallocateRequest >= (dbIdCurrent + nDbLeftFreeBeforeAllocate)) && (nDbPreallocateRequest < dbIdLast))
		{
			operation = ACTION_DB_REMOVE;
		}
	}
	return operation;
}


/**
 * Creates all the required readings tables considering the tables already defined in the database
 * and the number of tables to have on each database.
 *
 * @param dbId Database Id in which the table must be created
 *
 */
void ReadingsCatalogue::preallocateReadingsTables(int dbId)
{
	int readingsToAllocate;
	int readingsToCreate;
	int startId;

	if (dbId == 0 )
		dbId = m_dbIdCurrent;

	tyReadingsAvailable readingsAvailable;

	string dbName;

	readingsAvailable.lastReadings = 0;
	readingsAvailable.tableCount = 0;

	// Identifies last readings available
	readingsAvailable = evaluateLastReadingAvailable(NULL, dbId);
	readingsToAllocate = getNReadingsAllocate();

	if (readingsAvailable.tableCount < readingsToAllocate)
	{
		readingsToCreate = readingsToAllocate - readingsAvailable.tableCount;
		if (dbId == 1)
			startId = 2;
		else
			startId = 1;
		createReadingsTables(NULL, dbId, startId, readingsToCreate);
	}

	m_nReadingsAvailable = readingsToAllocate - getUsedTablesDbId(dbId);

	Logger::getLogger()->debug("preallocateReadingsTables - dbId %d nReadingsAvailable %d lastReadingsCreated %d tableCount %d", m_dbIdCurrent, m_nReadingsAvailable, readingsAvailable.lastReadings, readingsAvailable.tableCount);
}

/**
 * Generates the full path of the SQLite database from the given the id
 *
 * @param dbId Database Id for which the full path must be generated
 * @return     Generated the full path
 *
 */
string ReadingsCatalogue::generateDbFilePath(int dbId)
{
	string dbPathReadings;

	char *defaultReadingsConnection;
	char defaultReadingsConnectionTmp[1000];

	defaultReadingsConnection = getenv("DEFAULT_SQLITE_DB_READINGS_FILE");

	if (defaultReadingsConnection == NULL)
	{
		dbPathReadings = getDataDir();
	}
	else
	{
		// dirname modify the content of the parameter
		strncpy ( defaultReadingsConnectionTmp, defaultReadingsConnection, sizeof(defaultReadingsConnectionTmp) );
		dbPathReadings  = dirname(defaultReadingsConnectionTmp);
	}

	if (dbPathReadings.back() != '/')
		dbPathReadings += "/";

	dbPathReadings += generateDbFileName(dbId);

	return  (dbPathReadings);
}

/**
 * Stores on the persistent storage the id of the last created database
 *
 * @param dbHandle Database connection to use for the operations
 * @param newDbId  Id of the created database
 * @return         True of success, false on any error
 *
 */
bool ReadingsCatalogue::latestDbUpdate(sqlite3 *dbHandle, int newDbId)
{
	string sql_cmd;

	Logger::getLogger()->debug("latestDbUpdate - dbHandle %X newDbId %d", dbHandle, newDbId);

	{
		sql_cmd = " UPDATE " READINGS_DB ".configuration_readings SET db_id_Last=" + to_string(newDbId) + ";";

		if (SQLExec(dbHandle, sql_cmd.c_str()) != SQLITE_OK)
		{
			raiseError("latestDbUpdate", sqlite3_errmsg(dbHandle));
			return false;
		}
	}
	return true;
}


/**
 * Creates a new database
 *
 * @param dbHandle     Database connection to use for the operations
 * @param newDbId      If of the created database to create
 * @param startId      Starting id for the creation of the reading tables
 * @param attachAllDb  Type of attache operation to apply on the newly created database
 * @return             True of success, false on any error
 *
 */
bool  ReadingsCatalogue::createNewDB(sqlite3 *dbHandle, int newDbId, int startId, NEW_DB_OPERATION attachAllDb)
{
	int rc;
	int nTables;

	int readingsToAllocate;
	int readingsToCreate;

	string sqlCmd;
	string dbPathReadings;
	string dbAlias;

	struct stat st;
	bool dbAlreadyPresent=false;
	bool result;
	bool connAllocated;
	Connection *connection;

	connAllocated = false;
	result = true;

	ConnectionManager *manager = ConnectionManager::getInstance();

	// Are there enough descriptors available to create another database
	if (!manager->allowMoreDatabases())
	{
		return false;
	}

	if (dbHandle == NULL)
	{
		connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Create New database";
	connection->setUsage(usage);
#endif
		dbHandle = connection->getDbHandle();
		connAllocated = true;
	}

	// Creates the DB data file
	dbPathReadings = generateDbFilePath(newDbId);

	dbAlreadyPresent = false;
	if(stat(dbPathReadings.c_str(),&st) == 0)
	{
		Logger::getLogger()->info("createNewDB - database file '%s' already present, creation skipped " , dbPathReadings.c_str() );
		dbAlreadyPresent = true;
	}
	else
	{
		Logger::getLogger()->debug("createNewDB - new database created '%s'", dbPathReadings.c_str());
	}
	enableWAL(dbPathReadings);

	latestDbUpdate(dbHandle, newDbId);

	readingsToAllocate = getNReadingsAllocate();
	readingsToCreate = readingsToAllocate;

	// Attached the new db to the connections
	dbAlias = generateDbAlias(newDbId);

	if (attachAllDb == NEW_DB_ATTACH_ALL)
	{
		Logger::getLogger()->debug("createNewDB - attach all the databases");
		result = manager->attachNewDb(dbPathReadings, dbAlias);

	} else  if (attachAllDb == NEW_DB_ATTACH_REQUEST)
	{
		Logger::getLogger()->debug("createNewDB - attach single");

		result = attachDb(dbHandle, dbPathReadings, dbAlias, newDbId);
		result = manager->attachRequestNewDb(newDbId, dbHandle);

	} else  if (attachAllDb == NEW_DB_DETACH)
	{
		Logger::getLogger()->debug("createNewDB - attach");
		result = attachDb(dbHandle, dbPathReadings, dbAlias, newDbId);
	}

	if (result)
	{
		setUsedDbId(newDbId);

		if (dbAlreadyPresent)
		{
			tyReadingsAvailable readingsAvailable = evaluateLastReadingAvailable(dbHandle, newDbId);

			if (readingsAvailable.lastReadings == -1)
			{
				Logger::getLogger()->error("createNewDB - database file '%s' is already present but it is not possible to evaluate the readings table already present" , dbPathReadings.c_str() );
				result = false;
			}
			else
			{
				readingsToCreate = readingsToAllocate - readingsAvailable.tableCount;
				startId = readingsAvailable.lastReadings +1;
				Logger::getLogger()->info("createNewDB - database file '%s' is already present, creating readings tables - from id %d n %d " , dbPathReadings.c_str(), startId, readingsToCreate);
			}
		}

		if (readingsToCreate > 0)
		{
			startId = 1;
			createReadingsTables(dbHandle, newDbId ,startId, readingsToCreate);

			Logger::getLogger()->info("createNewDB - database file '%s' created readings table - from id %d n %d " , dbPathReadings.c_str(), startId, readingsToCreate);
		}
		m_nReadingsAvailable = readingsToAllocate;
	}

	// Create the overflow table in the new database if it was not previosuly created
	createReadingsOverflowTable(dbHandle, newDbId);

	if (attachAllDb == NEW_DB_DETACH)
	{
		Logger::getLogger()->debug("createNewDB - deattach");
		detachDb(dbHandle, dbAlias);
	}

	if (connAllocated)
	{
		manager->release(connection);
	}

	return (result);
}

/**
 * Creates a set of reading tables in the given database id
 *
 * @param dbHandle    Database connection to use for the operations
 * @param dbId        Database id on which the tables should be created
 * @param idStartFrom Id from with to start to create the tables
 * @param nTables     Number of table to create
 *
 */
bool  ReadingsCatalogue::createReadingsTables(sqlite3 *dbHandle, int dbId, int idStartFrom, int nTables)
{
	string createReadings, createReadingsIdx;
	string dbName;
	string dbReadingsName;
	int tableId;
	int rc;
	int readingsIdx;
	bool newConnection;
	Connection        *connection;

	Logger *logger = Logger::getLogger();
	newConnection = false;

	ConnectionManager *manager = ConnectionManager::getInstance();

	if (dbHandle == NULL)
	{
		connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Create Readings Tables";
	connection->setUsage(usage);
#endif
		dbHandle = connection->getDbHandle();
		newConnection = true;
	}

	logger->info("Creating %d readings table in advance starting id %d", nTables, idStartFrom);

	dbName = generateDbName(dbId);

	for (readingsIdx = 0 ;  readingsIdx < nTables; ++readingsIdx)
	{
		tableId = idStartFrom + readingsIdx;
		dbReadingsName = generateReadingsName(dbId, tableId);

		createReadings = R"(
			CREATE TABLE IF NOT EXISTS )" + dbName + "." + dbReadingsName + R"( (
				id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
				reading    JSON                        NOT NULL DEFAULT '{}',
				user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),
				ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))
			);
		)";

		createReadingsIdx = R"(
			CREATE INDEX IF NOT EXISTS )" + dbName + "." + dbReadingsName + R"(_ix3 ON )" + dbReadingsName + R"( (user_ts);
		)";

		logger->info(" Creating table '%s' sql cmd '%s'", dbReadingsName.c_str(), createReadings.c_str());

		rc = SQLExec(dbHandle, createReadings.c_str());
		if (rc != SQLITE_OK)
		{
			raiseError("createReadingsTables", sqlite3_errmsg(dbHandle));
			if (newConnection)
			{
				manager->release(connection);
			}
			return false;
		}

		rc = SQLExec(dbHandle, createReadingsIdx.c_str());
		if (rc != SQLITE_OK)
		{
			raiseError("createReadingsTables", sqlite3_errmsg(dbHandle));
			if (newConnection)
			{
				manager->release(connection);
			}
			return false;
		}
	}
	if (newConnection)
	{
		manager->release(connection);
	}

	return true;
}

/**
 * Create the overflow reading tables in the given database id
 *
 * We should only do this once when we upgrade to the version with an
 * overflow table. Although this should ideally be done in the schema
 * update script we can't do this as we can not loop over all the
 * databases in that script.
 *
 * @param dbHandle    Database connection to use for the operation
 *
 */
bool  ReadingsCatalogue::createReadingsOverflowTable(sqlite3 *dbHandle, int dbId)
{
	string dbReadingsName;

	Logger *logger = Logger::getLogger();

	ConnectionManager *manager = ConnectionManager::getInstance();

	string dbName = generateDbName(dbId);
	logger->info("Creating reading overflow table for database '%s'", dbName.c_str());

	dbReadingsName = string(READINGS_TABLE) + "_" + to_string(dbId);
       	dbReadingsName.append("_overflow");

	string sqlCmd = "select count(*) from " + dbName + "." + dbReadingsName + ";";
	char *errMsg;
	int rc = SQLExec(dbHandle, sqlCmd.c_str(), &errMsg);
	if (rc == SQLITE_OK)
	{
		logger->debug("Overflow table %s already exists, not attempting creation", dbReadingsName.c_str());
		return true;
	}

	string createReadings = R"(
		CREATE TABLE IF NOT EXISTS )" + dbName + "." + dbReadingsName + R"( (
			id         INTEGER                     PRIMARY KEY AUTOINCREMENT,
			asset_code CHARACTER varying(50)       NOT NULL,
			reading    JSON                        NOT NULL DEFAULT '{}',
			user_ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),
			ts         DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW'))
		);
	)";

	string createReadingsIdx1 = R"(
		CREATE INDEX IF NOT EXISTS )" + dbName + "." + dbReadingsName + R"(_ix1 ON )" + dbReadingsName + R"( (asset_code, user_ts desc);
	)";
	string createReadingsIdx2 = R"(
		CREATE INDEX IF NOT EXISTS )" + dbName + "." + dbReadingsName + R"(_ix2 ON )" + dbReadingsName + R"( (asset_code);
	)";
	string createReadingsIdx3 = R"(
		CREATE INDEX IF NOT EXISTS )" + dbName + "." + dbReadingsName + R"(_ix3 ON )" + dbReadingsName + R"( (user_ts);
	)";

	logger->info(" Creating table '%s' sql cmd '%s'", dbReadingsName.c_str(), createReadings.c_str());

	rc = SQLExec(dbHandle, createReadings.c_str());
	if (rc != SQLITE_OK)
	{
		raiseError("creating overflow table", sqlite3_errmsg(dbHandle));
		return false;
	}

	rc = SQLExec(dbHandle, createReadingsIdx1.c_str());
	if (rc != SQLITE_OK)
	{
		raiseError("creating overflow table index 1", sqlite3_errmsg(dbHandle));
		return false;
	}
	rc = SQLExec(dbHandle, createReadingsIdx2.c_str());
	if (rc != SQLITE_OK)
	{
		raiseError("creating overflow table index 2", sqlite3_errmsg(dbHandle));
		return false;
	}
	rc = SQLExec(dbHandle, createReadingsIdx3.c_str());
	if (rc != SQLITE_OK)
	{
		raiseError("creating overflow table index 3", sqlite3_errmsg(dbHandle));
		return false;
	}

	return true;
}

/**
 * Evaluates the latest reading table defined in the provided database id looking at sqlite_master, the SQLite repository
 *
 * @param dbHandle Database connection to use for the operations
 * @param dbId     Database id for which the operation must be executed
 *
 * @return - a struct containing
 *             lastReadings = the id of the latest reading table defined in the  given database id
 *             tableCount   = Number of tables  given database id in the given database id
 */
ReadingsCatalogue::tyReadingsAvailable  ReadingsCatalogue::evaluateLastReadingAvailable(sqlite3 *dbHandle, int dbId)
{
	string dbName;
	int nCols;
	int id;
	char *asset_name;
	sqlite3_stmt *stmt;
	int rc;
	string tableName;
	tyReadingsAvailable readingsAvailable;

	Connection        *connection;
	bool connAllocated = false;

	vector<int> readingsId(getNReadingsAvailable(), 0);

	ConnectionManager *manager = ConnectionManager::getInstance();

	if (dbHandle == NULL)
	{
		connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Evaluate last reading available";
	connection->setUsage(usage);
#endif
		dbHandle = connection->getDbHandle();
		connAllocated = true;
	}

	dbName = generateDbName(dbId);

	string sql_cmd = R"(
		SELECT name
		FROM  )" + dbName +  R"(.sqlite_master
		WHERE type='table' and name like 'readings_%';
	)";

	if (sqlite3_prepare_v2(dbHandle,sql_cmd.c_str(),-1, &stmt,NULL) != SQLITE_OK)
	{
		raiseError("evaluateLastReadingAvailable", sqlite3_errmsg(dbHandle));
		readingsAvailable.lastReadings = -1;
		readingsAvailable.tableCount = 0;
	}
	else
	{
		// Iterate over all the rows in the resultSet
		readingsAvailable.lastReadings = 0;
		readingsAvailable.tableCount = 0;
		while ((rc = SQLStep(stmt)) == SQLITE_ROW)
		{
			nCols = sqlite3_column_count(stmt);

			tableName = (char *)sqlite3_column_text(stmt, 0);
			if (tableName.find_first_of("overflow") == string::npos)
			{
				id = extractReadingsIdFromName(tableName);

				if (id > readingsAvailable.lastReadings)
					readingsAvailable.lastReadings = id;

				readingsAvailable.tableCount++;
			}
		}
		Logger::getLogger()->debug("evaluateLastReadingAvailable - tableName '%s' lastReadings %d", tableName.c_str(), readingsAvailable.lastReadings);

		sqlite3_finalize(stmt);
	}

	if (connAllocated)
	{
		manager->release(connection);
	}

	return (readingsAvailable);
}

/**
 * Checks if there is a reading table still available to be used
 */
bool  ReadingsCatalogue::isReadingAvailable() const
{
	if (m_nReadingsAvailable <= 0)
		return false;
	else
		return true;

}

/**
 * Tracks the allocation of a reading table
 *
 */
void  ReadingsCatalogue::allocateReadingAvailable()
{
	m_nReadingsAvailable--;
}

/**
 * Allocates a reading table to the given asset_code
 *
 * @param    connection	Db connection to be used for the operations
 * @param    asset_code for which the referenced readings table should be idenfied
 * @return              the reading id associated to the provided asset_code
 */
ReadingsCatalogue::tyReadingReference  ReadingsCatalogue::getReadingReference(Connection *connection, const char *asset_code)
{
	tyReadingReference ref;

	sqlite3_stmt *stmt;
	string sql_cmd;
	int rc;
	sqlite3		*dbHandle;

	string msg;
	bool success;

	int startReadingsId;
	tyReadingsAvailable readingsAvailable;

	ostringstream threadId;
	threadId << std::this_thread::get_id();

	success = true;

	dbHandle = connection->getDbHandle();

	Logger *logger = Logger::getLogger();

	auto item = m_AssetReadingCatalogue.find(asset_code);
	if (item != m_AssetReadingCatalogue.end())
	{
		//# The asset is already allocated to a table
		ref.tableId = item->second.getTable();
		ref.dbId = item->second.getDatabase();
		item->second.issue();
	}
	else
	{
		Logger::getLogger()->debug("getReadingReference - before lock dbHandle %X threadId '%s'", dbHandle, threadId.str().c_str() );

		AttachDbSync *attachSync = AttachDbSync::getInstance();
		attachSync->lock();
		
		ReadingsCatalogue::tyReadingReference emptyTableReference = {-1, -1};
		std::string emptyAsset = {};
		auto item = m_AssetReadingCatalogue.find(asset_code);
		if (item != m_AssetReadingCatalogue.end())
		{
			ref.tableId = item->second.getTable();
			ref.dbId = item->second.getDatabase();
			item->second.issue();
		}
		else
		{
			
			if (! isReadingAvailable ())
			{
				// No Reading table available... Get empty reading table 
				emptyTableReference = getEmptyReadingTableReference(emptyAsset);
				if ( !emptyAsset.empty() )
				{
					ref = emptyTableReference;
				}
				else 
				{
					//# Allocate a new block of readings table
					Logger::getLogger()->debug("Allocating a new db form the preallocated tables.  %d preallocated tables available.", m_dbNAvailable);

					if (m_dbNAvailable > 0)
					{
						// DBs already pre-allocated are available
						m_dbIdCurrent++;
						m_dbNAvailable--;
						m_nReadingsAvailable = getNReadingsAllocate();

						Logger::getLogger()->debug("Allocate dbIdCurrent %d dbIdLast %d dbNAvailable  %d nReadingsAvailable %d  ", m_dbIdCurrent, m_dbIdLast, m_dbNAvailable, m_nReadingsAvailable);
					}
					else
					{
						// There are no pre-allocated databases available
						// Allocates new DBs
						int dbId, dbIdStart, dbIdEnd, allocated = 0;

						dbIdStart = m_dbIdLast +1;
						dbIdEnd = m_dbIdLast + m_storageConfigCurrent.nDbToAllocate;

						Logger::getLogger()->debug("getReadingReference - allocate a new db - create new db - dbIdCurrent %d dbIdStart %d dbIdEnd %d", m_dbIdCurrent, dbIdStart, dbIdEnd);

						for (dbId = dbIdStart; dbId <= dbIdEnd; dbId++)
						{
							readingsAvailable = evaluateLastReadingAvailable(dbHandle, dbId - 1);

							startReadingsId = 1;

							success = createNewDB(dbHandle,  dbId, startReadingsId, NEW_DB_ATTACH_REQUEST);
							if (success)
							{
								Logger::getLogger()->debug("getReadingReference - allocate a new db - create new dbs - dbId %d startReadingsIdOnDB %d", dbId, startReadingsId);
								allocated++;
							}
							else
							{
								break;
							}
						}
						if (allocated)
						{
							m_dbIdLast += allocated;
							m_dbIdCurrent++;
							m_dbNAvailable += (allocated - 1);
						}
					}

					ref.tableId = -1;
					ref.dbId = -1;
				}
				
			}

			if (success)
			// Associate a reading table to the asset
			{
				// Associate the asset to the reading_id
				if (emptyAsset.empty())
				{
					ref.tableId = getMaxReadingsId(m_dbIdCurrent) + 1;
					ref.dbId = m_dbIdCurrent;
				}

				{
					m_EmptyAssetReadingCatalogue.erase(emptyAsset);
					m_AssetReadingCatalogue.erase(emptyAsset);
					auto newMapValue = make_pair(asset_code, TableReference(ref.dbId, ref.tableId));
					m_AssetReadingCatalogue.insert(newMapValue);
				}

				// Allocate the table in the reading catalogue
				if (emptyAsset.empty())
				{
					sql_cmd =
						"INSERT INTO  " READINGS_DB ".asset_reading_catalogue (table_id, db_id, asset_code) VALUES  ("
						+ to_string(ref.tableId) + ","
						+ to_string(ref.dbId) + ","
						+ "\"" + asset_code + "\")";
					
						Logger::getLogger()->debug("getReadingReference - allocate a new reading table for the asset '%s' db Id %d readings Id %d ", asset_code, ref.dbId, ref.tableId);

				}
				else
				{
					sql_cmd = 	" UPDATE " READINGS_DB ".asset_reading_catalogue SET asset_code ='" + string(asset_code) + "'" +
									" WHERE db_id = " + to_string(ref.dbId) + " AND table_id = " + to_string(ref.tableId) + ";";

					Logger::getLogger()->debug("getReadingReference - Use empty table %readings_%d_%d: ",ref.dbId,ref.tableId);
				}
				
				{
					rc = SQLExec(dbHandle, sql_cmd.c_str());
					if (rc != SQLITE_OK)
					{
						msg = string(sqlite3_errmsg(dbHandle)) + " asset :" + asset_code + ":";
						raiseError("asset_reading_catalogue update", msg.c_str());
					}

					if (emptyAsset.empty())
					{
						allocateReadingAvailable();
					}
					
				}

			}
			else
			{
				// Assign to overflow
				Logger::getLogger()->info("Assign asset %s to the overflow table", asset_code);
				auto newMapValue = make_pair(asset_code, TableReference(m_nextOverflow, 0));
				m_AssetReadingCatalogue.insert(newMapValue);
				sql_cmd =
					"INSERT INTO  " READINGS_DB ".asset_reading_catalogue (table_id, db_id, asset_code) VALUES  ( 0,"
					+ to_string(m_nextOverflow) + ","
					+ "\"" + asset_code + "\")";
				rc = SQLExec(dbHandle, sql_cmd.c_str());
				if (rc != SQLITE_OK)
				{
					msg = string(sqlite3_errmsg(dbHandle)) + " asset :" + asset_code + ":";
					raiseError("asset_reading_catalogue update", msg.c_str());
				}
				ref.tableId = 0;
				ref.dbId = m_nextOverflow;
				if (m_nextOverflow > m_maxOverflowUsed)
				{
					m_maxOverflowUsed = m_nextOverflow;
				}
				m_nextOverflow++;
				if (m_nextOverflow > m_dbIdLast)
					m_nextOverflow = 1;

			}
			Logger::getLogger()->debug("Assign: '%s' to %d, %d", asset_code, ref.dbId, ref.tableId);
		}
		attachSync->unlock();
	}

	return (ref);

}

/**
 * Loads the empty reading table catalogue
 *
 */
bool ReadingsCatalogue::loadEmptyAssetReadingCatalogue(bool clean)
{
	std::lock_guard<std::mutex> guard(m_emptyReadingTableMutex);
	sqlite3 *dbHandle;
	string sql_cmd;
	sqlite3_stmt *stmt;
	ConnectionManager *manager = ConnectionManager::getInstance();
	
	if (clean)
	{
		m_EmptyAssetReadingCatalogue.clear();
	}

	// Do not populate m_EmptyAssetReadingCatalogue if data is already there
	if (m_EmptyAssetReadingCatalogue.size())	
	{
		return true;
	}

	Connection *connection = manager->allocate();
#if TRACK_CONNECTION_USER
	string usage = "Load empty sset reading catalogue";
	connection->setUsage(usage);
#endif
	dbHandle = connection->getDbHandle();
	time_t issueThreshold = time(0) - 600;		// More than 10 minutes since it was last ussed
	for (auto &item : m_AssetReadingCatalogue)
	{
		string asset_name = item.first; // Asset
		int tableId = item.second.getTable(); // tableId;
		int dbId = item.second.getDatabase(); // dbId;

		if (tableId > 0 && item.second.lastIssued() < issueThreshold)
		{
			
			sql_cmd = "SELECT COUNT(*) FROM readings_" + to_string(dbId) + ".readings_" + to_string(dbId) + "_" + to_string(tableId) + " ;";
			if (sqlite3_prepare_v2(dbHandle, sql_cmd.c_str(), -1, &stmt, NULL) != SQLITE_OK)
			{
				sqlite3_finalize(stmt);	
				continue;
			}

			if (SQLStep(stmt) == SQLITE_ROW)
			{
				if (sqlite3_column_int(stmt, 0) == 0)
				{
					auto newItem = make_pair(tableId,dbId);
					auto newMapValue = make_pair(asset_name,newItem);
					m_EmptyAssetReadingCatalogue.insert(newMapValue);
					
				}
			}
			sqlite3_finalize(stmt);
		}
		
	}
	manager->release(connection);
	return true;
}

/**
 *  Get Empty Reading Table
 *
 * @param    asset emptyAsset, copies value of asset for which empty table is found
 * @return         the reading id associated to the provided empty table
 */
ReadingsCatalogue::tyReadingReference ReadingsCatalogue::getEmptyReadingTableReference(std::string& asset)
{
	ReadingsCatalogue::tyReadingReference emptyTableReference = {-1, -1};
	if (m_EmptyAssetReadingCatalogue.size() == 0)
	{
		loadEmptyAssetReadingCatalogue();
	}

	auto it = m_EmptyAssetReadingCatalogue.begin();
	if (it != m_EmptyAssetReadingCatalogue.end())
	{
		asset = it->first;
		emptyTableReference.tableId = it->second.first;
		emptyTableReference.dbId = it->second.second;
	}

	return emptyTableReference;
}

/**
 * Retrieve the maximum table id for the provided database id
 *
 * @param dbId Database id for which the maximum reading id must be retrieved
 * @return     Maximum readings for the requested database id
 *
 */
int ReadingsCatalogue::getMaxReadingsId(int dbId)
{
	int maxId = 0;

	for (auto &item : m_AssetReadingCatalogue)
	{
		if (item.second.getDatabase() == dbId && item.second.getTable() > maxId)
			maxId = item.second.getTable();
	}

	return (maxId);
}


/**
 * Returns the number of readings in use
 *
 * @return number of readings in use
 *
 */
int ReadingsCatalogue::getReadingsCount()
{
	return (m_AssetReadingCatalogue.size());
}

/**
 * Returns the position in the array of the specific readings Id considering the database id and the table id
 *
 * @param dbId    Database id for which calculation must be evaluated
 * @param tableId table  id for which calculation must be evaluated
 * @return        Position in the array of the specific readings Id
 *
 */
int ReadingsCatalogue::getReadingPosition(int dbId, int tableId)
{
	int position;

	if ((dbId == 0) && (tableId == 0))
	{
		dbId = m_dbIdCurrent;
		getMaxReadingsId(dbId);
	}

	position = ((dbId - 1) * m_storageConfigCurrent.nReadingsPerDb) + tableId;

	return (position);
}


/**
 * Calculate the number of reading tables associated to the given database id
 *
 * @param dbId    Database id for which calculation must be evaluated
 * @return        Number of reading tables associated to the given database id
 *
 */
int ReadingsCatalogue::getUsedTablesDbId(int dbId)
{
	int count = 0;

	for (auto &item : m_AssetReadingCatalogue)
	{
		if (item.second.getTable() != 0 && item.second.getDatabase() == dbId)
			count++;
	}

	return (count);
}

/**
 * Delete the content of all the active readings tables using the provided sql command sqlCmdBase
 *
 * @param dbHandle     Database connection to use for the operations
 * @param sqlCmdBase   Sql command to execute
 * @param zErrMsg      value returned by reference, Error message
 * @param rowsAffected value returned by reference if != 0, Number of affected rows
 * @return             returns SQLITE_OK if all the sql commands are properly executed
 *
 */
int  ReadingsCatalogue::purgeAllReadings(sqlite3 *dbHandle, const char *sqlCmdBase, char **zErrMsg, unsigned long *rowsAffected)
{
	string dbReadingsName;
	string dbName;
	string sqlCmdTmp;
	string sqlCmd;
	bool firstRow;
	int rc;

	if (m_AssetReadingCatalogue.empty())
	{
		Logger::getLogger()->debug("purgeAllReadings: no tables defined");
		rc = SQLITE_OK;
	}
	else
	{
		Logger::getLogger()->debug("purgeAllReadings tables defined");

		PurgeConfiguration *purgeConfig = PurgeConfiguration::getInstance();
		bool exclusions = purgeConfig->hasExclusions();

		firstRow = true;
		if  (rowsAffected != nullptr)
			*rowsAffected = 0;

		for (auto &item : m_AssetReadingCatalogue)
		{
			if (exclusions && purgeConfig->isExcluded(item.first))
			{
				Logger::getLogger()->info("Asset %s excluded from purge", item.first.c_str());
				continue;
			}
			sqlCmdTmp = sqlCmdBase;

			dbName = generateDbName(item.second.getDatabase());
			dbReadingsName = generateReadingsName(item.second.getDatabase(), item.second.getTable());

			StringReplaceAll (sqlCmdTmp, "_assetcode_", item.first);
			StringReplaceAll (sqlCmdTmp, "_dbname_", dbName);
			StringReplaceAll (sqlCmdTmp, "_tablename_", dbReadingsName);
			sqlCmd += sqlCmdTmp;
			firstRow = false;

			rc = SQLExec(dbHandle, sqlCmdTmp.c_str(), zErrMsg);

			Logger::getLogger()->debug("purgeAllReadings:  rc:%d, errorMsg:'%s', cmd:'%s'", rc , (*zErrMsg) ? (*zErrMsg) : "", sqlCmdTmp.c_str() );

			if (rc != SQLITE_OK)
			{
				// sqlite3_free(*zErrMsg); // needed by calling method
				break;
			}
			if  (rowsAffected != nullptr) {

				*rowsAffected += (unsigned long ) sqlite3_changes(dbHandle);
			}

		}
	}

	return(rc);

}

/**
 * Constructs a sql command from the given one consisting of a set of UNION ALL commands
 * considering all the readings tables in use
 *
 * @param sqlCmdBase        Base Sql command
 * @param assetCodes        Asset codes to evaluate for the operation
 * @param considerExclusion If True the asset code in the excluded list must not be considered
 * @return                  Full sql command
 *
 */
string  ReadingsCatalogue::sqlConstructMultiDb(string &sqlCmdBase, vector<string>  &assetCodes, bool considerExclusion)
{
	string dbReadingsName;
	string dbName;
	string sqlCmdTmp;
	string sqlCmd;

	string assetCode;
	bool addTable;
	bool addedOne;

	if (m_AssetReadingCatalogue.empty())
	{
		Logger::getLogger()->debug("sqlConstructMultiDb: no tables defined");
		sqlCmd = sqlCmdBase;

		dbReadingsName = generateReadingsName(1, 1);

		StringReplaceAll (sqlCmd, "_assetcode_", "dummy_asset_code");
		StringReplaceAll (sqlCmd, ".assetcode.", "asset_code");
		StringReplaceAll (sqlCmd, "_dbname_", READINGS_DB);
		StringReplaceAll (sqlCmd, "_tablename_", dbReadingsName);
	}
	else
	{
		Logger::getLogger()->debug("sqlConstructMultiDb: tables defined");

		bool firstRow = true;
		addedOne = false;

		PurgeConfiguration *purgeConfig = PurgeConfiguration::getInstance();
		bool exclusions = purgeConfig->hasExclusions();

		for (auto &item : m_AssetReadingCatalogue)
		{
			assetCode=item.first;
			addTable = false;

			if (considerExclusion && exclusions && purgeConfig->isExcluded(item.first))
			{
				Logger::getLogger()->info("Asset %s excluded from the query on the multiple readings", item.first.c_str());
				continue;
			}

			// Exclude the overflow table
			if (item.second.getTable() == 0)
			{
				continue;
			}

			// Evaluates which tables should be referenced
			if (assetCodes.empty())
				addTable = true;
			else
			{
				if (std::find(assetCodes.begin(), assetCodes.end(), assetCode) != assetCodes.end())
					addTable = true;
			}

			if (addTable)
			{
				addedOne = true;

				sqlCmdTmp = sqlCmdBase;

				if (!firstRow)
				{
					sqlCmd += " UNION ALL ";
				}

				dbName = generateDbName(item.second.getDatabase());
				dbReadingsName = generateReadingsName(item.second.getDatabase(), item.second.getTable());

				StringReplaceAll(sqlCmdTmp, "_assetcode_", assetCode);
				StringReplaceAll (sqlCmdTmp, ".assetcode.", "asset_code");
				StringReplaceAll(sqlCmdTmp, "_dbname_", dbName);
				StringReplaceAll(sqlCmdTmp, "_tablename_", dbReadingsName);
				sqlCmd += sqlCmdTmp;
				firstRow = false;
			}
		}
		// Add at least one table eventually a dummy one
		if (! addedOne)
		{
			dbReadingsName = generateReadingsName(1, 1);

			sqlCmd = sqlCmdBase;
			StringReplaceAll (sqlCmd, "_assetcode_", "dummy_asset_code");
			StringReplaceAll (sqlCmd, "_dbname_", READINGS_DB);
			StringReplaceAll (sqlCmd, "_tablename_", dbReadingsName);
		}
	}

	return sqlCmd;
}

/**
 * Add union all clauses for all the overflow tables based on tempalted SQL that is passed
 * in and a set of assets codes
 *
 * @param sqlCmdBase        Base Sql command
 * @param assetCodes        Asset codes to evaluate for the operation
 * @param considerExclusion If True the asset code in the excluded list must not be considered
 * @param groupBy	    Include a group by asset_code in each sub query
 * @return                  Full sql command
 *
 */
string  ReadingsCatalogue::sqlConstructOverflow(string &sqlCmdBase, vector<string>  &assetCodes, bool considerExclusion, bool groupBy)
{
	string dbReadingsName;
	string dbName;
	string sqlCmdTmp;
	string sqlCmd;

	string assetCode;
	bool addTable;
	bool addedOne;

	for (int dbId = 1; dbId <= m_maxOverflowUsed; dbId++)
	{
		dbReadingsName = generateReadingsName(dbId, 0);
		sqlCmdTmp = sqlCmdBase;

		sqlCmd += " UNION ALL ";

		dbName = generateDbName(dbId);

		StringReplaceAll (sqlCmdTmp, ".assetcode.", "asset_code");
		StringReplaceAll(sqlCmdTmp, "_dbname_", dbName);
		StringReplaceAll(sqlCmdTmp, "_tablename_", dbReadingsName);
		sqlCmd += sqlCmdTmp;
		if (! assetCodes.empty())
		{
			sqlCmd += " WHERE ";
			bool first = true;
			for (auto& code : assetCodes)
			{
				if (!first)
				{
					sqlCmd += " or ";
					first = false;
				}
				sqlCmd += "asset_code = \'";
				sqlCmd += code;
				sqlCmd += "\'";
			}
		}

		if (groupBy)
		{
			sqlCmd += " GROUP By asset_code";
		}
	}

	return sqlCmd;
}


/**
 * Generates a SQLite db alias from the database id
 *
 * @param dbId Database id for which the alias must be generated
 * @return     Generated alias
 *
 */
string ReadingsCatalogue::generateDbAlias(int dbId)
{

	return (READINGS_DB_NAME_BASE "_" + to_string(dbId));
}

/**
 * Generates a SQLIte database name from the database id
 *
 * @param dbId Database id for which the database name must be generated
 * @return     Generated database name
 *
 */
string ReadingsCatalogue::generateDbName(int dbId)
{
	return (READINGS_DB_NAME_BASE "_" + to_string(dbId));
}

/**
 * Generates a SQLITE database file name from the database id
 *
 * @param dbId Database id for which the database file name must be generated
 * @return     Generated database file name
 *
 */
string ReadingsCatalogue::generateDbFileName(int dbId)
{
	return (READINGS_DB_NAME_BASE "_" + to_string (dbId) + ".db");
}

/**
 * Extracts the readings id from the table name
 *
 * @param tableName Table name from which the id must be extracted
 * @return          Extracted reading id or -1 on error
 *
 */
int ReadingsCatalogue::extractReadingsIdFromName(string tableName)
{
	int dbId;
	int tableId = -1;
	string dbIdTableId;

	try {
		dbIdTableId = tableName.substr (tableName.find('_') + 1);

		tableId = stoi(dbIdTableId.substr (dbIdTableId.find('_') + 1));

		dbId = stoi(dbIdTableId.substr (0, dbIdTableId.find('_') ));
	} catch (exception &e) {
		Logger::getLogger()->fatal("extractReadingsIdFromName: exception on table %s, %s",
				tableName.c_str(), e.what());
	}


	return tableId;
}

/**
 * Extract the database id from the table name
 *
 * @param tableName Table name from which the database id must be extracted
 * @return          Extracted database id or -1 on error
 *
 */
int ReadingsCatalogue::extractDbIdFromName(string tableName)
{
	int dbId = -1;
	int tableId;
	string dbIdTableId;

	try {
		dbIdTableId = tableName.substr (tableName.find('_') + 1);

		tableId = stoi(dbIdTableId.substr (dbIdTableId.find('_') + 1));

		dbId = stoi(dbIdTableId.substr (0, dbIdTableId.find('_') ));
	} catch (exception &e) {
		Logger::getLogger()->fatal("extractReadingsIdFromName: exception on table %s, %s",
				tableName.c_str(), e.what());
	}

	return dbId;
}
/**
 * Generates the name of the reading table from the given table id as:
 * Prefix + db Id + reading Id. If the tableId is 0 then this is a 
 * reference to the overflow table
 *
 * @param dbId    Database id to use for the generation of the table name
 * @param tableId Table id to use for the generation of the table name
 * @return        Generated reading table name
 *
 */
string ReadingsCatalogue::generateReadingsName(int  dbId, int tableId)
{
	string tableName;

	if (dbId == -1)
		dbId = retrieveDbIdFromTableId(tableId);

	if (tableId == 0)	// Overflow table
	{
		tableName = READINGS_TABLE "_" + to_string(dbId) + "_overflow";
	}
	else
	{
		tableName = READINGS_TABLE "_" + to_string(dbId) + "_" + to_string(tableId);
	}
	Logger::getLogger()->debug("%s -  dbId %d tableId %d table name '%s' ", __FUNCTION__, dbId, tableId, tableName.c_str());

	return tableName;
}

/**
 * Retrieves the database id from the table id
 *
 * @param tableId Table id for which the database id must be retrieved
 * @return        Retrieved database id for the requested reading id
 *
 */
int ReadingsCatalogue::retrieveDbIdFromTableId(int tableId)
{
	int dbId;

	dbId = -1;
	for (auto &item : m_AssetReadingCatalogue)
	{

		if (item.second.getTable() == tableId)
		{
			dbId = item.second.getDatabase();
			break;
		}
	}
	return (dbId);
}

/**
 * Identifies SQLIte database name from the given table id
 *
 * @param tableId Table id for which the database name must be retrieved
 * @return        Retrieved database name for the requested reading id
 *
 */
string ReadingsCatalogue::generateDbNameFromTableId(int tableId)
{
	string dbName;

	for (auto &item : m_AssetReadingCatalogue)
	{

		if (item.second.getTable() == tableId)
		{
			dbName = READINGS_DB_NAME_BASE "_" + to_string(item.second.getDatabase());
			break;
		}
	}
	if (dbName == "")
		dbName = READINGS_DB_NAME_BASE "_1";

	return (dbName);
}

/**
 * SQLIte wrapper to retry statements when the database is locked
 *
 * @param dbHandle  Database connection to use for the operations
 * @param sqlCmdsql The SQL to execute
 * @param errmsg	Returned by reference, error message
 * @return          SQLite constant indicating the outcome of the requested operation, like for example SQLITE_LOCKED, SQLITE_BUSY...
 *
 */
int ReadingsCatalogue::SQLExec(sqlite3 *dbHandle, const char *sqlCmd, char **errMsg)
{
	int retries = 0, rc;

	if (errMsg)
	{
		*errMsg = NULL;
	}
	Logger::getLogger()->debug("SQLExec: cmd '%s' ", sqlCmd);

	do {
		if (errMsg && *errMsg)
		{
			sqlite3_free(*errMsg);
			*errMsg = NULL;
		}
		rc = sqlite3_exec(dbHandle, sqlCmd, NULL, NULL, errMsg);
		Logger::getLogger()->debug("SQLExec: rc %d ", rc);

		retries++;
		if (rc == SQLITE_LOCKED || rc == SQLITE_BUSY)
		{
			int interval = (retries * RETRY_BACKOFF);
			usleep(interval);	// sleep retries milliseconds
			if (retries > 5) Logger::getLogger()->info("SQLExec - error '%s' retry %d of %d, rc=%s, DB connection @ %p, slept for %d msecs",
													   sqlite3_errmsg(dbHandle), retries, MAX_RETRIES, (rc==SQLITE_LOCKED)?"SQLITE_LOCKED":"SQLITE_BUSY", this, interval);
		}
	} while (retries < MAX_RETRIES && (rc == SQLITE_LOCKED || rc == SQLITE_BUSY));

	if (rc == SQLITE_LOCKED)
	{
		Logger::getLogger()->error("SQLExec - Database still locked after maximum retries");
	}
	if (rc == SQLITE_BUSY)
	{
		Logger::getLogger()->error("SQLExec - Database still busy after maximum retries");
	}

	return rc;
}

/**
 * SQLIte wrapper to retry statements when the database error occurs
 *
 * @param statement	SQLIte statement to execute
 * @return          SQLite constant indicating the outcome of the requested operation, like for example SQLITE_LOCKED, SQLITE_BUSY...
 *
 */
int ReadingsCatalogue::SQLStep(sqlite3_stmt *statement)
{
	int retries = 0, rc;

	do {
		rc = sqlite3_step(statement);
		retries++;
		if (rc == SQLITE_LOCKED || rc == SQLITE_BUSY)
		{
			int interval = (retries * RETRY_BACKOFF);
			usleep(interval);	// sleep retries milliseconds
			if (retries > 5) Logger::getLogger()->info("SQLStep: retry %d of %d, rc=%s, DB connection @ %p, slept for %d msecs",
													   retries, MAX_RETRIES, (rc==SQLITE_LOCKED)?"SQLITE_LOCKED":"SQLITE_BUSY", this, interval);
		}
	} while (retries < MAX_RETRIES && (rc == SQLITE_LOCKED || rc == SQLITE_BUSY));

	if (rc == SQLITE_LOCKED)
	{
		Logger::getLogger()->error("Database still locked after maximum retries");
	}
	if (rc == SQLITE_BUSY)
	{
		Logger::getLogger()->error("Database still busy after maximum retries");
	}

	return rc;
}

/**
 * Remove committed TRANSACTION for the given thread
 *
 * @param    tid	The thread id
 * 			that just committed a transaction
 */
void TransactionBoundary::ClearThreadTransaction(std::thread::id tid)
{
	// Lock m_boundaries map
	std::lock_guard<std::mutex> lck(m_boundaryLock);

	// Find thread id
	auto itr = m_boundaries.find(tid);
	if (itr != m_boundaries.end())
	{
		// Remove element
		m_boundaries.erase(itr);
#if LOG_TX_BOUNDARIES
		Logger::getLogger()->debug("ClearThreadTransaction: thread [%ld] cleared TX start %ld",
					tid, itr->second);
#endif
	}
	else
	{
		Logger::getLogger()->error("ClearThreadTransaction: thread [%ld] not found", tid);
	}
}

/**
 * Set BEGIN of a transaction for a given thread, reading id
 *
 * @param    tid	The thread id
 * 			that just started a transaction
 * @param    id		The global reading id that starts the transaction
 */
void TransactionBoundary::SetThreadTransactionStart(std::thread::id tid, unsigned long id)
{
	// Lock m_boundaries map
	std::lock_guard<std::mutex> lck(m_boundaryLock);

	// Set id per thread
	m_boundaries[tid] = id;

#if LOG_TX_BOUNDARIES
	Logger::getLogger()->debug("SetThreadTransactionStart: thread [%ld] set TX start at %ld",
				tid,
				id);
#endif
}

/**
 * Fetch the minimum safe global reading id
 * among all UNCOMMITTED per thread transactions
 *
 * @return		The safe global reading id to use in
 *			UNION ALL queries as boundary limit
 */
unsigned long TransactionBoundary::GetMinReadingId()
{
	// Lock m_boundaries map
	std::lock_guard<std::mutex> lck(m_boundaryLock);

	unsigned long id = 0;

	// Get minimum reading id
	auto it = std::min_element(std::begin(m_boundaries),
				std::end(m_boundaries),
				// Lambda compare function
				[](std::pair<std::thread::id ,unsigned long> i,
					std::pair<std::thread::id ,unsigned long> j)
					{
						return i.second < j.second;
					});

	// Found, set id
	if (it != m_boundaries.end())
	{
		id = it->second;
	}

#ifdef LOG_TX_BOUNDARIES
	std::thread::id tid = std::this_thread::get_id();
	Logger::getLogger()->debug("GetMinReadingId: thread [%ld] TX min id is %ld",
				   tid,
				   id);
#endif

	return id;
}
