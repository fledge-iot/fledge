#ifndef _CONNECTION_H
#define _CONNECTION_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <sql_buffer.h>
#include <string>
#include <rapidjson/document.h>
#include <libpq-fe.h>

class Connection {
	public:
		Connection();
		~Connection();
		bool		retrieve(const std::string& table, const std::string& condition,
					std::string& resultSet);
    		bool 		retrieveReadings(const std::string& condition, std::string& resultSet);
		int		insert(const std::string& table, const std::string& data);
		int		update(const std::string& table, const std::string& data);
		int		deleteRows(const std::string& table, const std::string& condition);
		int		appendReadings(const char *readings);
		bool		fetchReadings(unsigned long id, unsigned int blksize, std::string& resultSet);
		unsigned int	purgeReadings(unsigned long age, unsigned int flags, unsigned long sent, std::string& results);
		long		tableSize(const std::string& table);
		void		setTrace(bool flag) { m_logSQL = flag; };
    		static bool 	formatDate(char *formatted_date, size_t formatted_date_size, const char *date);
		int		create_table_snapshot(const std::string& table, const std::string& id);
		int		load_table_snapshot(const std::string& table, const std::string& id);
		int		delete_table_snapshot(const std::string& table, const std::string& id);
		bool		get_table_snapshots(const std::string& table,
						    std::string& resultSet);

	private:
		bool		m_logSQL;
		void		raiseError(const char *operation, const char *reason,...);
		PGconn		*dbConnection;
		void		mapResultSet(PGresult *res, std::string& resultSet);
		bool		jsonWhereClause(const rapidjson::Value& whereClause, SQLBuffer&);
		bool		jsonModifiers(const rapidjson::Value&, SQLBuffer&);
		bool		jsonAggregates(const rapidjson::Value&, const rapidjson::Value&, SQLBuffer&, SQLBuffer&, bool isTableReading = false);
		bool		returnJson(const rapidjson::Value&, SQLBuffer&, SQLBuffer&);
		char		*trim(char *str);
    		const std::string	escape_double_quotes(const std::string&);
		const std::string	escape(const std::string&);
    		const std::string 	double_quote_reserved_column_name(const std::string &column_name);
		void		logSQL(const char *, const char *);
};
#endif
