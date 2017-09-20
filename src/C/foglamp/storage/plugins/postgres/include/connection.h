#ifndef _CONNECTION_H
#define _CONNECTION_H

#include <string>
#include <rapidjson/document.h>
#include <libpq-fe.h>

class Connection {
  public:
    Connection();
    ~Connection();
    std::string      retrieve(const std::string& table, const std::string& condition);
  private:
    PGconn      *dbConnection;
    std::string      mapResultSet(PGresult *res);
    std::string      jsonWhereClause(const rapidjson::Value& whereClause);
    char *trim(char *str);
};
#endif
