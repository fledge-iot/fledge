#ifndef _CONNECTION_H
#define _CONNECTION_H
/*
 * FogLAMP storage service.
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

class Connection {
	public:
		Connection();
		~Connection();
		bool		retrieve(const std::string& table, const std::string& condition,
					std::string& resultSet);
		int		insert(const std::string& table, const std::string& data);
		int		update(const std::string& table, const std::string& data);
		int		deleteRows(const std::string& table, const std::string& condition);
		int		appendReadings(const char *readings);
		bool		fetchReadings(unsigned long id, unsigned int blksize,
						std::string& resultSet);
		unsigned int	purgeReadings(unsigned long age, unsigned int flags,
						unsigned long sent, std::string& results);
		long		tableSize(const std::string& table);
	private:
		void		raiseError(const char *operation, const char *reason,...);
		sqlite3		*dbHandle;
		int		mapResultSet(void *res, std::string& resultSet);
		bool		jsonWhereClause(const rapidjson::Value& whereClause, SQLBuffer&);
		bool		jsonModifiers(const rapidjson::Value&, SQLBuffer&);
		bool		jsonAggregates(const rapidjson::Value&,
						const rapidjson::Value&,
						SQLBuffer&,
						SQLBuffer&);
		bool		returnJson(const rapidjson::Value&, SQLBuffer&, SQLBuffer&);
		char		*trim(char *str);
		const char	*escape(const char *);
		const std::string	escape(const std::string&);
};
#endif
