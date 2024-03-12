#ifndef _CONNECTION_H
#define _CONNECTION_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <sql_buffer.h>
#include <string>
#include <rapidjson/document.h>
#include <sqlite3.h>

WARNING: THIS FILE IS NOT USED

#define	READINGS_TABLE		"readings"
#define	READINGS_TABLE_MEM	READINGS_TABLE "_1"

class Connection {
	public:
		Connection();
		~Connection();
		bool		retrieveReadings(const std::string& condition,
					std::string& resultSet);
		int		appendReadings(const char *readings);
		bool		fetchReadings(unsigned long id, unsigned int blksize,
						std::string& resultSet);
		unsigned int	purgeReadings(unsigned long age, unsigned int flags,
						unsigned long sent, std::string& results);
		long		tableSize(const std::string& table);
		void		setTrace(bool flag) { m_logSQL = flag; };
		static bool 	formatDate(char *formatted_date, size_t formatted_date_size, const char *date);
		unsigned int	purgeReadingsAsset(const std::string& asset);
		bool		vacuum();
		bool		loadDatabase(const std::string& filname);
		bool		saveDatabase(const std::string& filname);
		void		setPurgeBlockSize(unsigned long purgeBlockSize)
				{
					m_purgeBlockSize = purgeBlockSize;
				}
	private:
		int 		SQLexec(sqlite3 *db, const char *sql,
					int (*callback)(void*,int,char**,char**),
		  			void *cbArg, char **errmsg);
		bool		m_logSQL;
		void		raiseError(const char *operation, const char *reason,...);
		sqlite3		*inMemory; // Handle for :memory: database
		int		mapResultSet(void *res, std::string& resultSet);
		bool		jsonWhereClause(const rapidjson::Value& whereClause, SQLBuffer&, bool convertLocaltime = false);
		bool		jsonModifiers(const rapidjson::Value&, SQLBuffer&);
    		bool		jsonAggregates(const rapidjson::Value&,
		                               const rapidjson::Value&,
		                               SQLBuffer&,
		                               SQLBuffer&,
		                               bool isTableReading = false);
		bool		returnJson(const rapidjson::Value&, SQLBuffer&, SQLBuffer&);
		char		*trim(char *str);
		const std::string	escape(const std::string&);
		bool applyColumnDateTimeFormat(sqlite3_stmt *pStmt,
						int i,
						std::string& newDate);
		void		logSQL(const char *, const char *);
		unsigned long	m_purgeBlockSize;
};
#endif
