#ifndef _STORAGE_API_H
#define _STORAGE_API_H

#include <server_http.hpp>

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/*
 * The URL for each entry point
 */
#define COMMON_ACCESS		"^/storage/table/([A-Za-z][a-zA-Z0-9_]*)$"
#define COMMON_QUERY		"^/storage/table/([A-Za-z][a-zA-Z_0-9]*)/query$"

#define TABLE_NAME_COMPONENT	1

/**
 * The Storage API class - this class is responsible for the registration of all API
 * entry points in the storage API and the dispatch of those API calls to the internals
 * of the storage service and the storage plugin itself.
 */
class StorageApi {

public:
	StorageApi(const short port, const int threads);
        static StorageApi *getInstance();
  void initResources();
	void start();
	void wait();
	void commonInsert(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void commonSimpleQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void commonQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void commonUpdate(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void commonDelete(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void defaultResource(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);

private:
        static StorageApi       *m_instance;
        HttpServer              *m_server;
	short                   m_port;
	int		        m_threads;
        thread                  m_thread;
	void respond(shared_ptr<HttpServer::Response> response, string payload);
  void respond(shared_ptr<HttpServer::Response> response, SimpleWeb::StatusCode code, string payload);
};

#endif
