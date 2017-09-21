#ifndef _CONNECTION_H
#define _CONNECTION_H

#include <sql_buffer.h>
#include <string>
#include <rapidjson/document.h>
#include <libpq-fe.h>

class Connection {
	public:
		Connection();
		~Connection();
		std::string     retrieve(const std::string& table, const std::string& condition);
		bool		insert(const std::string& table, const std::string& data);
		bool		update(const std::string& table, const std::string& data);
		bool		deleteRows(const std::string& table, const std::string& condition);
	private:
		PGconn		*dbConnection;
		std::string	mapResultSet(PGresult *res);
		bool		jsonWhereClause(const rapidjson::Value& whereClause, SQLBuffer&);
		char		*trim(char *str);
};
#endif
