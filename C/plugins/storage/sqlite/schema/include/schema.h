#ifndef _SCHEMAS_H
#define _SCHEMAS_H
/*
 * Fledge utilities functions for handling stringa
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <sql_buffer.h>
#include <string>
#include <rapidjson/document.h>
#include <sqlite3.h>
#include <logger.h>
#include <map>

#define DDL_BACKOFF	50	// Microseconds to backoff between DDL retries

/**
 * Representation of an extension schema
 *
 * Each active schema has an instance of the class that is managed by the
 * SchemaManager class. This is either created when Fledge restarts and reads the schema
 * definition from the database or when a service requests an extension schema to be
 * created.
 *
 * The class is responsible for the creation and update of the extension schemas. The 
 * name, service, version and definition of each schema is written to a control table
 * in the Fledge schema to allow for the versions to be tracked and also to allow the
 * extension schemas to be attached.
 */
class Schema {
	public:
		Schema(const std::string& name, const std::string& service, int version,
				const std::string& definition);
		Schema(sqlite3 *db, const rapidjson::Document& doc);
		~Schema();
		int		getVersion() { return m_version; };
		std::string	getService() { return m_service; };
		bool		upgrade(sqlite3 *db, const rapidjson::Document& doc, const std::string& definition);
		bool		attach(sqlite3 *db);
	private:
		std::string	m_name;
		std::string	m_service;
		int		m_version;
		std::string	m_definition;
		int		m_indexNo;
		std::string	m_schemaPath;
		std::map<sqlite3 *, bool>
				m_attached;
	private:
		bool		createTable(sqlite3 *db, const rapidjson::Value& table);
		bool		createIndex(sqlite3 *db, const std::string& table,
						const rapidjson::Value& index);
		bool		hasTable(const rapidjson::Document& doc, const std::string& table);
		bool		hasColumn(const rapidjson::Document& doc, const std::string& table,
						const std::string& column);
		bool		addTableColumn(sqlite3 *db, const std::string& table,
						const rapidjson::Value& column);
		bool		executeDDL(sqlite3 *db, SQLBuffer& sql);

		bool		hasString(const rapidjson::Value& value, const char *key)
				{
					return (value.HasMember(key) && value[key].IsString());
				};
		bool		hasInt(const rapidjson::Value& value, const char *key)
				{
					return (value.HasMember(key) && value[key].IsInt());
				};
		bool		hasArray(const rapidjson::Value& value, const char *key)
				{
					return (value.HasMember(key) && value[key].IsArray());
				};
		bool		createDatabase();
		void		setDatabasePath();
};

/**
 * The singleton SchemaManager class used to interact with
 * the extension schemas created by various extension services.
 */
class SchemaManager {
	public:
		static SchemaManager		*getInstance();
		void				load(sqlite3 *db);
		bool				create(sqlite3 *db, const std::string& definition);
		bool				exists(sqlite3 *db, const std::string& schema);
	public:
		static SchemaManager		*instance;
	private:
		SchemaManager();
	private:
		Logger				*m_logger;
		std::map<std::string, Schema *>	m_schema;
		bool				m_loaded;
};
#endif
