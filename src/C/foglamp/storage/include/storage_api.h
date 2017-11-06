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

#define PURGE_FLAG_RETAIN	"retain"
#define PURGE_FLAG_PURGE	"purge"

#define TABLE_NAME_COMPONENT	1

/**
 * The Storage API class - this class is responsible for the registration of all API
 * entry points in the storage API and the dispatch of those API calls to the internals
 * of the storage service and the storage plugin itself.
 */
class StorageApi {

public:
	StorageApi(const unsigned short port, const int threads);
        static StorageApi *getInstance();
	void	initResources();
	void	setPlugin(StoragePlugin *);
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

private:
        static StorageApi       *m_instance;
        HttpServer              *m_server;
	unsigned short          m_port;
	int		        m_threads;
        thread                  *m_thread;
	StoragePlugin		*plugin;
	StorageStats		stats;
	void			respond(shared_ptr<HttpServer::Response>, const string&);
	void			respond(shared_ptr<HttpServer::Response>, SimpleWeb::StatusCode, const string&);
	void			internalError(shared_ptr<HttpServer::Response>, const exception&);
	void			mapError(string&, PLUGIN_ERROR *);
};

#endif
