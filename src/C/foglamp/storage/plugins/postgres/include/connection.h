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
		bool		retrieve(const std::string& table, const std::string& condition,
					std::string& resultSet);
		bool		insert(const std::string& table, const std::string& data);
		bool		update(const std::string& table, const std::string& data);
		bool		deleteRows(const std::string& table, const std::string& condition);
	private:
		void		raiseError(const char *operation, const char *reason,...);
		PGconn		*dbConnection;
		void		mapResultSet(PGresult *res, std::string& resultSet);
		bool		jsonWhereClause(const rapidjson::Value& whereClause, SQLBuffer&);
		char		*trim(char *str);
};
#endif
