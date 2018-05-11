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
#include <logger.h>
#include <string>
#include <vector>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

/**
 * Client for accessing the storage service
 */
class StorageClient {
	public:
		StorageClient(const std::string& hostname, const unsigned short port);
		~StorageClient();
		ResultSet *queryTable(const std::string& tablename, const Query& query);
		int insertTable(const std::string& tableName, const InsertValues& values);
		int updateTable(const std::string& tableName, const InsertValues& values, const Query& query);
		bool readingAppend(Reading& reading);
		bool readingAppend(const std::vector<Reading *> & readings);
		ResultSet *readingQuery(const Query& query);
		ReadingSet *readingFetch(const unsigned long readingId, const unsigned long count);
		PurgeResult readingPurgeByAge(unsigned long age, unsigned long sent, bool purgeUnsent);
		PurgeResult readingPurgeBySize(unsigned long size, unsigned long sent, bool purgeUnsent);
	private:
		HttpClient		*m_client;
		Logger			*m_logger;
};
#endif

