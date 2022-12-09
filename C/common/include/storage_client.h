#ifndef _STORAGE_CLIENT_H
#define _STORAGE_CLIENT_H
/*
 * Fledge storage client.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
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
#include <thread>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

#define STREAM_BLK_SIZE 	50	// Readings to send per write call to a stream
#define STREAM_THRESHOLD	25	// Switch to streamed mode above this number of readings per second

// Backup values for repeated storage client exception messages
#define SC_INITIAL_BACKOFF	100
#define SC_MAX_BACKOFF		1000

#define DEFAULT_SCHEMA 	"fledge"

class ManagementClient;

/**
 * Client for accessing the storage service
 */
class StorageClient {
	public:
		StorageClient(HttpClient *client);
		StorageClient(const std::string& hostname, const unsigned short port);
		StorageClient(const std::string& hostname, const unsigned short port, std::map<std::thread::id, std::atomic<int>>*);
		~StorageClient();
		ResultSet	*queryTable(const std::string& schema, const std::string& tablename, const Query& query);
		ResultSet	*queryTable(const std::string& tablename, const Query& query);
		ReadingSet	*queryTableToReadings(const std::string& tableName, const Query& query);
		int 		insertTable(const std::string& schema, const std::string& tableName, const InsertValues& values);
		int		updateTable(const std::string& schema, const std::string& tableName, const InsertValues& values, const Where& where);
		int		updateTable(const std::string& schema, const std::string& tableName, const JSONProperties& json, const Where& where);
		int		updateTable(const std::string& schema, const std::string& tableName, const InsertValues& values, const JSONProperties& json, const Where& where);
		int		updateTable(const std::string& schema, const std::string& tableName, const ExpressionValues& values, const Where& where);
		int		updateTable(const std::string& schema, const std::string& tableName, std::vector<std::pair<ExpressionValues *, Where *>>& updates);
		int		updateTable(const std::string& schema, const std::string& tableName, const InsertValues& values, const ExpressionValues& expressoins, const Where& where);
		int		deleteTable(const std::string& schema, const std::string& tableName, const Query& query);
		int 		insertTable(const std::string& tableName, const InsertValues& values);
		int		updateTable(const std::string& tableName, const InsertValues& values, const Where& where);
		int		updateTable(const std::string& tableName, const JSONProperties& json, const Where& where);
		int		updateTable(const std::string& tableName, const InsertValues& values, const JSONProperties& json, const Where& where);
		int		updateTable(const std::string& tableName, const ExpressionValues& values, const Where& where);
		int		updateTable(const std::string& tableName, std::vector<std::pair<ExpressionValues *, Where *>>& updates);
		int		updateTable(const std::string& tableName, const InsertValues& values, const ExpressionValues& expressoins, const Where& where);
		int		deleteTable(const std::string& tableName, const Query& query);
		bool		readingAppend(Reading& reading);
		bool		readingAppend(const std::vector<Reading *> & readings);
		ResultSet	*readingQuery(const Query& query);
		ReadingSet 	*readingQueryToReadings(const Query& query);
		ReadingSet	*readingFetch(const unsigned long readingId, const unsigned long count);
		PurgeResult	readingPurgeByAge(unsigned long age, unsigned long sent, bool purgeUnsent);
		PurgeResult	readingPurgeBySize(unsigned long size, unsigned long sent, bool purgeUnsent);
		PurgeResult	readingPurgeByAsset(const std::string& asset);
		bool		registerAssetNotification(const std::string& assetName,
							  const std::string& callbackUrl);
		bool		unregisterAssetNotification(const std::string& assetName,
							    const std::string& callbackUrl);

		void		registerManagement(ManagementClient *mgmnt) { m_management = mgmnt; };
		bool 		createSchema(const std::string&);
		std::map<std::thread::id, std::atomic<int>>* getSeqNumMap() { return &m_seqnum_map; }
		std::ostringstream& getUrlBase() { return m_urlbase; }

	private:
		void		handleUnexpectedResponse(const char *operation,
							const std::string& table,
							const std::string& responseCode,
							const std::string& payload);
		void		handleUnexpectedResponse(const char *operation,
							const std::string& responseCode,
							const std::string& payload);
		void		handleException(const std::exception& ex, const char *operation, ...);
		HttpClient 	*getHttpClient(void);
		bool		openStream();
		bool		streamReadings(const std::vector<Reading *> & readings);
		void 		handle_storage_service_restart();

		std::ostringstream 			m_urlbase;
		std::string				m_host;
		std::map<std::thread::id, HttpClient *> m_client_map;
		std::map<std::thread::id, std::atomic<int>> m_seqnum_map;
		Logger					*m_logger;
		pid_t					m_pid;
		bool					m_streaming;
		int					m_stream;
		uint32_t				m_readingBlock;
		std::string				m_lastException;
		int					m_exRepeat;
		int					m_backoff;
		ManagementClient			*m_management;
};

#endif

