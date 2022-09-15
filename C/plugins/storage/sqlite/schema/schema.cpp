/*
 * Fledge storage service.
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <schema.h>
#include "rapidjson/error/error.h"
#include "rapidjson/error/en.h"
#include <unistd.h>
#include <connection.h>
#ifndef DB_CONFIGURATION
#define DB_CONFIGURATION "PRAGMA busy_timeout = 5000; PRAGMA cache_size = -4000; PRAGMA journal_mode = WAL; PRAGMA secure_delete = off; PRAGMA journal_size_limit = 4096000;"
#endif

using namespace std;
using namespace rapidjson;

SchemaManager *SchemaManager::instance = 0;

/**
 * Fetch the singleton instance of the SchemaManager
 *
 * @return SchemaManager*	The singleton SchemaManager instance
 */
SchemaManager *SchemaManager::getInstance()
{
	if (!instance)
		instance = new SchemaManager();
	return instance;
}

/**
 * Constructor for the singleton SchemaManager
 */
SchemaManager::SchemaManager() : m_loaded(false)
{
	m_logger = Logger::getLogger();
}

/**
 * Load the existing Schema from the table of supported schemas
 *
 * @param db	The database connection to use to load the schema information
 */
void SchemaManager::load(sqlite3 *db)
{
	const char *sql = "SELECT name, service, version, definition FROM fledge.service_schema;";
	sqlite3_stmt *stmt;
	int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);

	if (rc != SQLITE_OK)
	{
		m_logger->error("Failed to retrieve list of schemas");
		return;
	}

	if (stmt)
	{
		while ((rc = sqlite3_step(stmt)) == SQLITE_ROW)
		{
			string name = (const char *)sqlite3_column_text(stmt, 0);
			string service = (const char *)sqlite3_column_text(stmt, 1);
			int version = sqlite3_column_int(stmt, 2);
			string definition = (const char *)sqlite3_column_text(stmt, 3);

			m_schema.insert(pair<string, Schema *>(name,
						new Schema(name, service, version, definition)));
		}
		sqlite3_finalize(stmt);
	}
	m_loaded = true;
}

/**
 * Create a schema. This may create a completely new schema if it does not
 * already exist, update an existing schema if the version is different from
 * the one that already exists or no nothing if the schema exists and the version
 * of the schema is the same.
 *
 * @param db	A database connection to use for sqlite3 interactions
 * @param definition	The schema definition
 * @return bool	Returns true if the schema was created, updated or no action is required
 */
bool SchemaManager::create(sqlite3 *db, const std::string& definition)
{
Document doc;

	doc.Parse(definition.c_str());
	if (doc.HasParseError())
	{
		m_logger->error("Failed to parse extension schema definition '%s' at %d: %s",
				GetParseError_En(doc.GetParseError()), doc.GetErrorOffset(),
				definition.c_str());
		return false;
	}

	string name;
	if (doc.HasMember("schema") && doc["schema"].IsString())
	{
		name = doc["schema"].GetString();
	}
	else
	{
		m_logger->error("Extension schema is missing the schema name in the definition");
		return false;
	}
	if (!m_loaded)
	{
		load(db);
	}
	auto it = m_schema.find(name);
	if (it == m_schema.end())
	{
		Schema *schema = new Schema(db, doc);
		m_schema.insert(pair<string, Schema *>(name, schema));
	}
	else
	{
		int version;
		if (doc.HasMember("version") && doc["version"].IsInt())
		{
			version = doc["version"].GetInt();
		}
		else
		{
			m_logger->error("Extension schema %s is missing a version number", name.c_str());
			return false;
		}
		if (it->second->getVersion() != version)
		{
			return it->second->upgrade(db, doc, definition);
		}
	}
	return false;
}

/**
 * Check if a named schema exists, loading the schemas if need be. As
 * a side effect the schema will be attached to the database connection.
 *
 * @param schema	The schema to check the existance of
 * @return bool		True if the schema exists
 */
bool SchemaManager::exists(sqlite3 *db, const string& schema)
{
	if (schema.compare("fledge") == 0)	// The fledge schema always exists
		return true;

	if (!m_loaded)
	{
		load(db);
	}
	auto it = m_schema.find(schema);
	if (it == m_schema.end())
	{
		return false;
	}
	return it->second->attach(db);
}


/**
 * Constructor for a schema. This is the case in which a schema is beign loaded from
 * the database of schemas rather than becasue a service has requested a schema to be
 * created.
 *
 * Schemas will be loaded from the database before any schema creation request is
 * made by the services and will be used to attched the schemas and also to load the
 * baseline schema such that when the service requests a schema we can see if it already
 * exists and has the same version number.
 *
 * @param name	The name of the schema to create
 * @param service	The service requesting the schema
 * @param version	The version of the schema
 * @param definition	The JSON definition of the schema
 */
Schema::Schema(const string& name, const string& service, int version, const string& definition) :
	m_name(name), m_service(service), m_version(version), m_definition(definition), m_indexNo(0)
{
	setDatabasePath();
}

/**
 * Constructor for a schema. This is the case when a service has requested a schema
 * that does not already exist. We must create a new schema from scratch.
 *
 * @param db	SQLite3 database handle
 * @param doc	JSON definition of the schema to create
 */
Schema::Schema(sqlite3 *db, const rapidjson::Document& doc) : m_indexNo(0)
{
	Logger *logger = Logger::getLogger();

	if (hasString(doc, "schema"))
	{
		m_name = doc["schema"].GetString();
	}
	else
	{
		logger->error("Schema definition is missing a schema name property");
		throw runtime_error("Schema missing a name property");
	}
	if (hasString(doc, "service"))
	{
		m_service = doc["service"].GetString();
	}
	else
	{
		logger->error("Schema definition %s is missing a service property", m_name.c_str());
		throw runtime_error("Schema missing a service property");
	}
	if (hasInt(doc, "version"))
	{
		m_version = doc["version"].GetInt();
	}
	else
	{
		logger->error("Schema definition %s for service %s is missing a version property",
				m_name.c_str(), m_service.c_str());
		throw runtime_error("Schema missing a version property");
	}

	setDatabasePath();

	// Create the Schema
	createDatabase();

	// Attach the database file to this database connection
	attach(db);
	
	// Create the tables in the schema
	if (hasArray(doc, "tables"))
	{
		const Value& tables = doc["tables"];
		for (auto& table : tables.GetArray())
		{
			createTable(db, table);
		}
	}
	SQLBuffer sql;
	sql.append("INSERT INTO fledge.service_schema ( name, service, version, definition ) VALUES (");
	sql.quote(m_name);
	sql.append(',');
	sql.quote(m_service);
	sql.append(',');
	sql.append(m_version);
	sql.append(',');
	sql.quote(m_definition);
	sql.append(");");
	if (!executeDDL(db, sql))
	{
		logger->error("Failed to add schema to dictionary");
	}
}

/**
 * Create a table within the extension schema
 *
 * @param db	SQLite3 database handle
 * @param table	JSON representation of the table definition
 */
bool Schema::createTable(sqlite3 *db, const rapidjson::Value& table)
{
	Logger *logger = Logger::getLogger();
	if (!hasString(table, "name"))
	{
		logger->error("Table in schema %s is missing a name definition", m_name.c_str());
		return false;
	}
	string name = table["name"].GetString();
	if (!hasArray(table, "columns"))
	{
		logger->error("Table %s in schema %s has no columns defined", name.c_str(), m_name.c_str());
		return false;
	}
	const Value& columns = table["columns"];

	SQLBuffer	sql;
	sql.append("CREATE TABLE ");
	sql.append(m_name);
	sql.append('.');
	sql.append(name);
	sql.append(" (");
	bool first = true;
	for (auto& column : columns.GetArray())
	{
		if (first)
			first = false;
		else
			sql.append(',');
		if (!hasString(column, "column"))
		{
			logger->error("Table %s in schema %s is missing a column name definition",
					name.c_str(),m_name.c_str());
			return false;
		}
		string col = column["column"].GetString();
		if (!hasString(column, "type"))
		{
			logger->error("Column %s in table %s in schema %s is missing a column name definition",
					col.c_str(), name.c_str(), m_name.c_str());
			return false;
		}
		string type = column["type"].GetString();
		
		sql.append(col);
		if (type.compare("integer") == 0)
		{
			sql.append(" INTEGER");
		}
		else if (type.compare("varchar") == 0)
		{
			if (!hasInt(column, "size"))
			{
			}
			int size = column["size"].GetInt();
			sql.append(" CHARACTER VARYING(");
			sql.append(size);
			sql.append(')');
		}
		else if (type.compare("double") == 0)
		{
			sql.append(" REAL");
		}
		else if (type.compare("sequence") == 0)
		{
			sql.append(" INTEGER AUTOINCREMENT");
		}
		else
		{
			logger->error("Type %s is not supported in column %s of table %s in schema %s",
					type.c_str(), col.c_str(), name.c_str(), m_name.c_str());
			return false;
		}
		if (column.HasMember("key"))
		{
			sql.append(" PRIMARY KEY");
		}
	}
	sql.append(");");

	// Execute the SQL statement
	if (!executeDDL(db, sql))
	{
		return false;
	}
	
	// Now create any indexes on the table
	if (hasArray(table, "indexes"))
	{
		const Value& indexes = table["indexes"];
		for (auto& index : indexes.GetArray())
		{
			if (!createIndex(db, name, index))
			{
				return false;
			}
		}
	}
	return true;
}

/**
 * Create an index on a table
 *
 * @param db	SQLite database connection
 * @param table	The name of the table the index is created on
 * @param index	JSON defintion of the index
 */
bool Schema::createIndex(sqlite3 *db, const std::string& table, const rapidjson::Value& index)
{
	if (!index.IsArray())
	{
		Logger::getLogger()->error("Malformed index for table %s in schema %s",
				table.c_str(), m_name.c_str());
		return false;
	}
	SQLBuffer sql;
	sql.append("CREATE INDEX ");
	sql.append(m_name);
	sql.append(".");
	sql.append(table);
	sql.append("_idx");
	sql.append(m_indexNo++);
	sql.append(" ON ");
	sql.append(table);
	sql.append('(');
	bool first = true;
	for (auto& col : index.GetArray())
	{
		if (col.IsString())
		{
			if (first)
				first = false;
			else
				sql.append(',');
			sql.append(col.GetString());
		}
	}
	sql.append(");");

	// Execute the SQL statement
	return executeDDL(db, sql);
}

/**
 * Upgrade an existing schema. The upgrade process is limited and will only do the
 * following operations; add a new table, drop a table, add a new column to a table,
 * drop a column from a table, add a new index or drop an index.
 *
 * @param db	The SQLite3 database connection
 * @param doc	The pre-parsed version of the schema definition
 * @param definition	The schema defintion for the new version of the schema as JSON
 * @param bool	True if the upgrade suceeded.
 */
bool Schema::upgrade(sqlite3 *db, const Document& doc, const string& definition)
{
	Logger *logger = Logger::getLogger();

	Document onDisk;
	onDisk.Parse(m_definition.c_str());

	logger->debug("Schema update: %s: Phase 1 - adding any new tables", m_name.c_str());
	// Iterate over the new schema tables and find any not in the existing schema
	if (hasArray(doc, "tables"))
	{
		const Value& newTables = doc["tables"];
		for (auto& newTable : newTables.GetArray())
		{
			if (hasString(newTable, "name"))
			{
				string name = newTable["name"].GetString();
				if (!hasTable(onDisk, name))
				{
					logger->debug("Schema Upgrade of %s create table %s", m_name.c_str(), name.c_str());
					if (!createTable(db, newTable))
					{
						logger->error("Unable to create new table during schema upgrade for schema %s", m_name.c_str());
						return false;
					}
				}
			}
		}
	}

	// Now look for tables that need to be dropped
	logger->debug("Schema update: %s: Phase 2 - deleting any obsolete tables", m_name.c_str());
	if (hasArray(onDisk, "tables"))
	{
		const Value& oldTables = onDisk["tables"];
		for (auto& oldTable : oldTables.GetArray())
		{
			if (hasString(oldTable, "name"))
			{
				string name = oldTable["name"].GetString();
				if (!hasTable(doc, name))
				{
					logger->debug("Schema Upgrade of %s drop table %s", m_name.c_str(), name.c_str());
					SQLBuffer sql;
					sql.append("DROP TABLE IF EXISTS ");
					sql.append(m_name);
					sql.append('.');
					sql.append(name);
					sql.append(';');
					if (!executeDDL(db, sql))
					{
						return false;
					}
				}
			}
		}
	}

	logger->debug("Schema update: %s: Phase 3 - add any new columns to tables", m_name.c_str());
	// Iterate over the new schema tables in both and then check for new columns
	if (hasArray(doc, "tables"))
	{
		const Value& newTables = doc["tables"];
		for (auto& newTable : newTables.GetArray())
		{
			if (hasString(newTable, "name"))
			{
				string name = newTable["name"].GetString();
				if (hasTable(onDisk, name))
				{
					if (hasArray(newTable, "columns"))
					{
						const Value& columns = newTable["columns"];
						for (auto& column : columns.GetArray())
						{
							if (hasString(column, "column"))
							{
								string col = column["column"].GetString();
								if (!hasColumn(onDisk, name, col))
								{
									if (!addTableColumn(db, name, column))
									{
										return false;
									}
								}
							}
						}
					}
				}
			}
		}
	}

	logger->debug("Schema update: %s: Phase 4 - remove any obsolete columns from tables", m_name.c_str());
	// Iterate over the on disk tables looking for tables that exist in the new schema
	// and then look for columns that are on disk but not in the new schema
	if (hasArray(onDisk, "tables"))
	{
		const Value& oldTables = onDisk["tables"];
		for (auto& oldTable : oldTables.GetArray())
		{
			if (hasString(oldTable, "name"))
			{
				string name = oldTable["name"].GetString();
				if (hasTable(doc, name))
				{
					if (hasArray(oldTable, "columns"))
					{
						const Value& columns = oldTable["columns"];
						for (auto& column : columns.GetArray())
						{
							if (hasString(column, "column"))
							{
								string col = column["column"].GetString();
								if (!hasColumn(doc, name, col))
								{
									logger->debug("Schema Upgrade of %s drop column %s from table %s", m_name.c_str(), col.c_str(), name.c_str());
									SQLBuffer sql;
									sql.append("ALTER TABLE ");
									sql.append(m_name);
									sql.append('.');
									sql.append(name);
									sql.append(" DROP COLUMN ");
									sql.append(col);
									sql.append(';');
									if (!executeDDL(db, sql))
									{
										return false;
									}
								}
							}
						}
					}
				}
			}
		}
	}

	logger->debug("Schema update: %s: Phase 5 - add any new indexes", m_name.c_str());
	// Iterate over the new schema tables in both and then check for new columns
	if (hasArray(doc, "tables"))
	{
		const Value& newTables = doc["tables"];
		for (auto& newTable : newTables.GetArray())
		{
			if (hasString(newTable, "name"))
			{
				string name = newTable["name"].GetString();
				if (hasTable(onDisk, name))
				{
					if (hasArray(newTable, "indexes"))
					{
						const Value& indexes = newTable["indexes"];
						for (auto& index : indexes.GetArray())
						{
							if (hasArray(index, "index"))
							{
								// TODO Compare indexes
							}
						}
					}
				}
			}
		}
	}

	logger->debug("Schema update: %s: Phase 6 - remove any obsolete indexes", m_name.c_str());


	m_version = doc["version"].GetInt();	// Safe as we would not get here if version was missing
	m_definition = definition;

	logger->debug("Schema update: %s: Phase 7 - update schema table", m_name.c_str());
	SQLBuffer sql;
	sql.append("UPDATE fledge.service_schema SET version = ");
	sql.append(m_version);
	sql.append(", definition = ");
	sql.quote(m_definition);
	sql.append(" WHERE name = ");
	sql.quote(m_name);
	sql.append(" AND service = ");
	sql.quote(m_service);
	sql.append(';');
	if (!executeDDL(db, sql))
		return false;

	return true;
}

/**
 * Add a new column to an existing table within the schema
 *
 * @param db	The SQLite database handle
 * @param table	The name of the table we are adding the column to
 * @param column	The JSON definition of the column
 * @return bool	True if the column was added to the table
 */
bool Schema::addTableColumn(sqlite3 *db, const string& table, const Value& column)
{
	Logger *logger = Logger::getLogger();
	SQLBuffer sql;
	sql.append("ALTER TABLE ");
	sql.append(m_name);
	sql.append('.');
	sql.append(table);
	sql.append(" ADD COLUMN ");
	if (!hasString(column, "column"))
	{
		logger->error("Schema update %s, missing name for column in table %s",
				m_name.c_str(), table.c_str());
		return false;
	}
	string colName = column["colummn"].GetString();
	sql.append(colName);
	if (!hasString(column, "type"))
	{
		logger->error("Schema update %s, missing type for column %s in table %s",
				m_name.c_str(), colName.c_str(), table.c_str());
		return false;
	}
	string type = column["type"].GetString();
	if (type.compare("integer") == 0)
	{
		sql.append(" INTEGER");
	}
	else if (type.compare("varchar") == 0)
	{
		sql.append(" CHARACTER VARYING(");
		sql.append(')');
	}
	else if (type.compare("double") == 0)
	{
		sql.append(" REAL");
	}
	else if (type.compare("sequence") == 0)
	{
		sql.append(" INTEGER AUTOINCREMENT");
	}
	else
	{
		logger->error("Update schema type %s is not supported for column %s of table %s in schema %s",
				type.c_str(), colName.c_str(), table.c_str(), m_name.c_str());
		return false;
	}
	sql.append(';');
	return executeDDL(db, sql);
}

/**
 * Execute a DDL statement against the SQLite database
 *
 * @param db	The SQLite database handle
 * @param sql	The SQLBuffer to execute
 * @return bool	True if the statement succeeded
 */
bool Schema::executeDDL(sqlite3 *db, SQLBuffer& sql)
{
	const char *ddl = sql.coalesce();
	Logger *logger = Logger::getLogger();
	logger->debug("Schema %s: Execute DDL %s", m_name.c_str(), ddl);

	char *errMsg = NULL;
	int rc, retries = 0;
	if (((rc = sqlite3_exec(db, ddl, NULL, NULL, &errMsg)) == SQLITE_BUSY || rc == SQLITE_LOCKED)
			&& ++retries < 10)
	{
		int interval = retries * DDL_BACKOFF;
		usleep(interval);
	}
	if (rc != SQLITE_OK)
	{
		logger->error("Schema %s, failed to execute DDL %s, %s", m_name.c_str(), ddl,
				errMsg ? errMsg : "no reason available");
		if (errMsg)
		{
			sqlite3_free(errMsg);
		}
		return false;
	}

	return true;
}

/**
 * Look in the JSON definition of a schema and check for the existance of a table
 *
 * @param doc		The JSON document that defines the schema
 * @param table		The name of the table name to look for
 * @return bool		True if the table exists in the schema
 */
bool Schema::hasTable(const Document& doc, const string& tableName)
{
	if (!hasArray(doc, "tables"))
	{
		return false;
	}
	const Value& tables = doc["tables"];
	for (auto& table : tables.GetArray())
	{
		if (hasString(table, "name"))
		{
			string name = table["name"].GetString();
			if (name.compare(tableName) == 0)
			{
				return true;
			}
		}
	}
	return false;
}

/**
 * Look in the JSON definition of a schema and check for the existance of a column within a table
 *
 * @param doc		The JSON document that defines the schema
 * @param tableName	The name of the table name to look for
 * @param columnName	The name of the column name to look for
 * @return bool		True if the table exists in the schema
 */
bool Schema::hasColumn(const Document& doc, const string& tableName, const string& columnName)
{
	if (!hasArray(doc, "tables"))
	{
		return false;
	}
	const Value& tables = doc["tables"];
	for (auto& table : tables.GetArray())
	{
		if (hasString(table, "name"))
		{
			string name = table["name"].GetString();
			if (name.compare(tableName) == 0)
			{
				if (hasArray(table, "columns"))
				{
					const Value& columns = table["columns"];
					for (auto& column : columns.GetArray())
					{
						if (hasString(column, "column"))
						{
							string col = column["column"].GetString();
							if (col.compare(columnName) == 0)
							{
								return true;
							}
						}
					}
				}
			}
		}
	}
	return false;
}

/**
 * Setup the path of the schema database file
 */
void Schema::setDatabasePath()
{
	char *data = getenv("FLEDGE_DATA");
	if (!data)
	{
	       	m_schemaPath = getenv("FLEDGE_ROOT");
		m_schemaPath +="/data";
	}
	else
	{
		m_schemaPath = data;
	}
	m_schemaPath += "/";
	m_schemaPath += m_name;
	m_schemaPath += ".db";
}

/**
 * Create the SQLite database and enable the WAL mode for the database
 *
 * @return bool	Returns true on success
 */
bool Schema::createDatabase()
{

	sqlite3	*dbHandle;

	int rc = sqlite3_open(m_schemaPath.c_str(), &dbHandle);
	if (rc != SQLITE_OK)
	{
		Logger::getLogger()->error("Failed to create database for schema %s", m_name.c_str());
		return false;
	}
	if ((rc = sqlite3_exec(dbHandle, DB_CONFIGURATION, NULL, NULL, NULL)) != SQLITE_OK)
	{
		Logger::getLogger()->error("Unable to set database configuration for schema %s", m_name.c_str());
		return false;
	}
	sqlite3_close(dbHandle);
	return true;
}

/**
 * Attach the schema to the database handle if not already attached
 *
 * @param db	The database handle to attach the schema to
 * @return bool	True if the schema was attached
 */
bool Schema::attach(sqlite3 *db)
{
	if (m_attached.find(db) != m_attached.end())
	{
		// Already attached
		return true;
	}
	SQLBuffer sql;
	sql.append("ATTACH DATABASE '");
	sql.append(m_schemaPath);
	sql.append("' AS ");
	sql.append(m_name);
	sql.append(';');

	if (!executeDDL(db, sql))
	{
		return false;
	}
	m_attached[db] = true;
	return true;
}
