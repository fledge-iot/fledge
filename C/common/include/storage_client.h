#ifndef _STORAGE_CLIENT_H
#define _STORAGE_CLIENT_H
/*
 * FogLAMP storage client.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <client_http.hpp>
#include <reading.h>
#include <reading_set.h>
#include <resultset.h>
#include <purge_result.h>
#include <query.h>
#include <insert.h>
#include <json_properties.h>
#include <expression.h>
#include <logger.h>
#include <string>
#include <vector>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

/**
 * Client for accessing the storage service
 */
class StorageClient {
	public:
		StorageClient(HttpClient *client) : m_client(client) {};
		StorageClient(const std::string& hostname, const unsigned short port);
		~StorageClient();
		ResultSet	*queryTable(const std::string& tablename, const Query& query);
		int 		insertTable(const std::string& tableName, const InsertValues& values);
		int		updateTable(const std::string& tableName, const InsertValues& values, const Where& where);
		int		updateTable(const std::string& tableName, const JSONProperties& json, const Where& where);
		int		updateTable(const std::string& tableName, const InsertValues& values, const JSONProperties& json, const Where& where);
		int		updateTable(const std::string& tableName, const ExpressionValues& values, const Where& where);
		int		updateTable(const std::string& tableName, const InsertValues& values, const ExpressionValues& expressoins, const Where& where);
		int		deleteTable(const std::string& tableName, const Query& query);
		bool		readingAppend(Reading& reading);
		bool		readingAppend(const std::vector<Reading *> & readings);
		ResultSet	*readingQuery(const Query& query);
		ReadingSet	*readingFetch(const unsigned long readingId, const unsigned long count);
		PurgeResult	readingPurgeByAge(unsigned long age, unsigned long sent, bool purgeUnsent);
		PurgeResult	readingPurgeBySize(unsigned long size, unsigned long sent, bool purgeUnsent);
	private:
		void  		handleUnexpectedResponse(const char *operation,
						const std::string& responseCode,
						const std::string& payload);
		HttpClient		*m_client;
		Logger			*m_logger;
};
#endif

