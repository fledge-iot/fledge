#ifndef _STORAGE_API_H
#define _STORAGE_API_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <server_http.hpp>
#include <storage_plugin.h>
#include <storage_stats.h>
#include <storage_registry.h>

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/*
 * The URL for each entry point
 */
#define COMMON_ACCESS		"^/storage/table/([A-Za-z][a-zA-Z0-9_]*)$"
#define COMMON_QUERY		"^/storage/table/([A-Za-z][a-zA-Z_0-9]*)/query$"
#define READING_ACCESS  	"^/storage/reading$"
#define READING_QUERY   	"^/storage/reading/query"
#define READING_PURGE   	"^/storage/reading/purge"
#define READING_INTEREST	"^/storage/reading/interest/([A-Za-z\\*][a-zA-Z0-9_]*)$"
#define GET_TABLE_SNAPSHOTS	"^/storage/table/([A-Za-z][a-zA-Z_0-9_]*)/snapshot$"
#define CREATE_TABLE_SNAPSHOT	GET_TABLE_SNAPSHOTS
#define LOAD_TABLE_SNAPSHOT	"^/storage/table/([A-Za-z][a-zA-Z_0-9_]*)/snapshot/([a-zA-Z_0-9_]*)$"
#define DELETE_TABLE_SNAPSHOT	LOAD_TABLE_SNAPSHOT

#define PURGE_FLAG_RETAIN	"retain"
#define PURGE_FLAG_PURGE	"purge"

#define TABLE_NAME_COMPONENT	1
#define ASSET_NAME_COMPONENT	1
#define SNAPSHOT_ID_COMPONENT	2

/**
 * The Storage API class - this class is responsible for the registration of all API
 * entry points in the storage API and the dispatch of those API calls to the internals
 * of the storage service and the storage plugin itself.
 */
class StorageApi {

public:
	StorageApi(const unsigned short port, const unsigned  int threads);
        static StorageApi *getInstance();
	void	initResources();
	void	setPlugin(StoragePlugin *);
	void	setReadingPlugin(StoragePlugin *);
	void	start();
	void	startServer();
	void	wait();
	void	stopServer();
	unsigned short getListenerPort();
	void	commonInsert(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	commonSimpleQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	commonQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	commonUpdate(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	commonDelete(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	defaultResource(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingAppend(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingFetch(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingPurge(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingRegister(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingUnregister(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	createTableSnapshot(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	loadTableSnapshot(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	deleteTableSnapshot(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	getTableSnapshots(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	printList();

public:
	std::atomic<int>        m_workers_count;

private:
        static StorageApi       *m_instance;
        HttpServer              *m_server;
	unsigned short          m_port;
	unsigned int		m_threads;
        thread                  *m_thread;
	StoragePlugin		*plugin;
	StoragePlugin		*readingPlugin;
	StorageStats		stats;
	std::map<string, pair<int,std::list<std::string>::iterator>> m_seqnum_map;
	const unsigned int	max_entries_in_seqnum_map = 16;
	std::list<std::string>	seqnum_map_lru_list; // has the most recently accessed elements of m_seqnum_map at front of the dequeue
	std::mutex 		mtx_seqnum_map;
	StorageRegistry		registry;
	void			respond(shared_ptr<HttpServer::Response>, const string&);
	void			respond(shared_ptr<HttpServer::Response>, SimpleWeb::StatusCode, const string&);
	void			internalError(shared_ptr<HttpServer::Response>, const exception&);
	void			mapError(string&, PLUGIN_ERROR *);
};

#endif
